# Savra PPT Generation — Architecture Design Document

> **Author**: Full-Stack Engineering Candidate  
> **Date**: May 2026  
> **Status**: Implemented (prototype) + Designed (production path)

---

## TL;DR

Replace the synchronous Gemini-backed PPT generator with an async job system on Groq's API, with smart model routing as the primary cost lever. Projected cost reduction: **~99%** per PPT. Generation time: **30s → 2–4s** (fast path), **<15s** (complex path).

---

## A. System Design

### Current Architecture (The Problem)

```
Teacher → HTTP POST → Backend → Gemini 3.1 Pro → template injection → .PPTX
                  ↑ teacher blocked here, waiting up to 2+ minutes
```

**Why this breaks at scale:**
- Synchronous: one teacher's slow request blocks their entire session
- No retry intelligence — 503 → fallback → quality degrades, teacher still waits
- No caching — identical topic requests hit the LLM every single time
- Single LLM, single cost tier — Grade 3 "Animals" costs the same as Grade 12 "Organic Chemistry"

---

### Proposed Architecture

```
                     ┌─────────────────────────────────────────────────┐
                     │                   FRONTEND                       │
                     │  Submit form → get job_id → poll every 2s       │
                     │  Progress bar: Queued → Routing → Generating     │
                     └───────────────────┬─────────────────────────────┘
                                         │ POST /api/ppt/generate
                                         ▼
                     ┌─────────────────────────────────────────────────┐
                     │              FastAPI Backend                     │
                     │                                                  │
                     │  1. Validate request (Pydantic)                  │
                     │  2. Return job_id immediately (202 Accepted)     │
                     │  3. Enqueue background task                      │
                     └─────────┬──────────────────────────────────────┘
                               │ Background Task
                               ▼
              ┌────────────────────────────────────────┐
              │           Job Processor                │
              │                                        │
              │  ┌──────────────────────────────────┐  │
              │  │   1. Smart Router                │  │
              │  │   complexity_score(topic,grade,  │  │
              │  │   slides,subject) → model choice │  │
              │  └──────────┬───────────────────────┘  │
              │             │                           │
              │  ┌──────────▼───────────────────────┐  │
              │  │   2. Cache Check (SHA-256 key)   │  │
              │  │   HIT → return instantly (₹0)   │  │
              │  │   MISS → proceed to LLM         │  │
              │  └──────────┬───────────────────────┘  │
              │             │ MISS only                 │
              │  ┌──────────▼───────────────────────┐  │
              │  │   3. Groq API Call               │  │
              │  │   JSON mode → guaranteed parse   │  │
              │  │   Retry: model A → A → B         │  │
              │  └──────────┬───────────────────────┘  │
              │             │                           │
              │  ┌──────────▼───────────────────────┐  │
              │  │   4. Validate + Store Result     │  │
              │  │   Update job status → DONE       │  │
              │  └──────────────────────────────────┘  │
              └────────────────────────────────────────┘
                               │
                               ▼
              Teacher polls GET /api/ppt/status/{job_id}
              → Progress updates in real-time
              → Full result on completion
```

### Request Flow (Happy Path)

1. Teacher submits form → `POST /api/ppt/generate` returns `{job_id: "a1b2c3d4"}` in **< 50ms**
2. Frontend starts polling `GET /api/ppt/status/a1b2c3d4` every 2 seconds
3. Progress bar updates: Queued (0%) → Routing (20%) → Generating (40%) → Done (100%)
4. On `status: "done"` — render HTML slide preview, offer PPTX download

**Teacher experience**: No spinning wheel. They submit and see a live progress tracker. Even if generation takes 10s, they're informed, not stuck.

---

### Why Async Matters (The Most Important Decision)

The current sync model creates a compound problem:
- Under load, slow requests block the event loop
- Teachers rage-refresh, creating duplicate requests
- 503s hit during the wait, giving teachers a broken experience with no context

Async flips the contract: **we own the wait, not the teacher**. The teacher is free to navigate while we process. This is also why the progress bar matters — it's not decoration, it's trust-building.

In production, the background task queue should be BullMQ (Redis-backed) or Celery, not FastAPI's `background_tasks`, which is in-process and will drop jobs on restart. For the prototype, in-process is fine.

---

## B. Cost Reduction Strategy

### Where the Money Goes (Current)

| Component | Cost Driver | Share of ₹15 |
|-----------|------------|--------------|
| Gemini 3.1 Pro tokens | Input + output per PPT | ~₹12 |
| API overhead / calls | Per-request | ~₹2 |
| Infra (compute) | Synchronous holding | ~₹1 |

The LLM call is **80%+ of the cost**. That's the lever.

### The Switch to Groq

Groq runs Llama models on custom LPU hardware with dramatic speed and cost advantages:

| Model | Cost / 1M tokens | Avg PPT cost (5K tokens) | vs Gemini |
|-------|-----------------|--------------------------|-----------|
| `llama-3.1-8b-instant` | $0.05 | ~₹0.02 | **750x cheaper** |
| `llama-3.3-70b-versatile` | $0.59 | ~₹0.25 | **60x cheaper** |
| Gemini 3.1 Pro (current) | ~$3.50 est | ~₹14.60 | baseline |

### Smart Model Routing (Primary Optimization)

Not all PPTs need the same model. A Grade 5 "Water Cycle" presentation does not need 70B parameters.

**Complexity Score:**

```python
score = 0
if slides > 10:     score += 2   # volume → structure matters
if grade >= 11:     score += 3   # board-level complexity  
elif grade >= 9:    score += 2
if subject in HARD_SUBJECTS:  score += 1
if topic has complex keywords: score += 2

model = "70b" if score >= 4 else "8b"
```

**Expected distribution at 100 PPTs/day:**

| Model | Share | PPTs/day | Daily Cost |
|-------|-------|----------|-----------|
| 8b instant | 75% | 75 | ₹1.50 |
| 70b versatile | 25% | 25 | ₹6.25 |
| **Total** | | **100** | **₹7.75** |

vs. Current: ₹1,500/day

**Cost at current scale: ₹7.75/day (vs ₹1,500). Reduction: 99.5%.**

### Caching Layer

Exact-match cache (SHA-256 of topic + grade + slides + subject, 8h TTL):
- Schools teach the same topics every year. "Photosynthesis, Grade 7" will be requested by many teachers across schools.
- Estimated hit rate: 15–20% at scale (based on EdTech request pattern studies)
- Cache hits cost ₹0. At 20% hit rate on 100 PPTs/day: saves ~₹1.55/day additional

### Prompt Optimization

The current prompt is almost certainly verbose and unstructured. Our prompt:
- Uses JSON mode (Groq forces valid JSON output → no parsing failures, no retry waste)
- Enforces token budget via concise instructions
- Structured output reduces hallucination and re-generation cost

---

## C. Reliability Plan

### Current Failure Mode
Gemini 503 → immediate fallback to 2.5 Flash → quality drops → teacher notices → teacher loses trust

This is the worst kind of failure: **silent degradation**.

### Proposed Failure Hierarchy

```
Attempt 1:  Target model (8b or 70b based on routing)
Attempt 2:  Same model, 1s backoff (transient 503 recovery)
Attempt 3:  Alternate model, 3s backoff (actual fallback, same quality tier if possible)
Failure:    Job marked FAILED with clear message + retry option for teacher
```

**Key principle**: Never silently degrade. If we fall back to a different model, we log it and optionally show the teacher "Generated with fallback model — quality may vary." Honest > quiet failure.

### Fallback Model Choice

70b fails → fall back to 8b? Only for simple requests. For Grade 11+ Physics, 8b genuinely can't match quality. In that case:
- Retry 70b twice more (503s are usually transient, < 30s recovery)
- If still failing, queue the job with a "will retry" status and notify teacher when done
- Offer to generate a simplified version with 8b as opt-in

### Idempotency

Each job has a UUID. Retrying the same request (teacher refreshes) checks for existing job with same params — no duplicate generation.

### Circuit Breaker (Production)

Track Groq error rate over a 60s sliding window. If error rate > 40%, open the circuit:
- Route all new requests to 8b (more resilient, less loaded)
- Close circuit after 30s quiet period
- This prevents thundering herd on a recovering provider

---

## D. Scaling Plan

### Current Bottleneck Map

| Component | Bottleneck at 100/day | Bottleneck at 500/day | Bottleneck at 2000/day |
|-----------|----------------------|----------------------|------------------------|
| Sync HTTP hold | Threads exhausted | App crashes | N/A (already broken) |
| Gemini rate limits | Occasional 503 | Constant 503 | Impossible |
| No cache | Full cost every request | Full cost every request | Full cost every request |
| Single server | OK | Strained | Impossible |

### With Proposed Architecture

| Scale | System Behavior | Action Needed |
|-------|----------------|---------------|
| 500 PPTs/day | Async queue handles without strain. Groq rate limits won't be hit. | None — current design handles this |
| 2,000 PPTs/day | In-memory job store will fill RAM. Background tasks risk loss on restart. | Migrate job store to Redis. Add persistent job queue (BullMQ/Celery) |
| 5,000+ PPTs/day | Single FastAPI instance becomes a bottleneck | Horizontal scaling: 3-5 API servers behind a load balancer, shared Redis |
| 10,000 PPTs/day | Need rate limiting per teacher (prevent abuse), job prioritization | Add per-teacher rate limiting (10 PPTs/hour), priority queue for Pro users |

### Infrastructure Decisions: Now vs. Later

**Build now (cheap, high leverage):**
- Async job pattern (done — prevents cascading failures)
- Groq integration (done — 99% cost reduction)
- Smart routing (done — further savings + quality preservation)
- Exact cache (done — handles repeat requests for free)

**Build at 500 PPTs/day:**
- Migrate in-memory job store → Redis
- Add BullMQ job queue for persistence and retry guarantees
- Structured logging + Sentry for error tracking

**Build at 2,000 PPTs/day:**
- Horizontal scaling: 3 FastAPI replicas + Redis shared state
- CDN for delivered PPTX files (avoid re-serving the same file)
- PostgreSQL for job history and analytics (teacher usage dashboards)

**Build at 5,000+ PPTs/day:**
- Dedicated worker pool separate from API servers (decoupled scaling)
- Semantic cache layer (bonus feature) — significantly higher hit rates
- LLM provider redundancy: Groq primary, OpenAI fallback

---

## Bonus: Projected Cost at 10,000 Users

**Assumptions:**
- 10,000 total users
- 50% teachers = 5,000 teachers
- 2 PPTs/week per teacher = 10,000 PPTs/week = ~43,000 PPTs/month
- Model distribution: 75% 8b ($0.05/1M tokens), 25% 70b ($0.59/1M tokens)
- Avg tokens per PPT: 5,000 (2K input + 3K output)
- Cache hit rate at scale: 25% (schools share topics heavily)
- INR/USD: 83.5

**Calculation:**

```
Effective PPTs after cache: 43,000 × 0.75 = 32,250 LLM calls/month

8b calls:  32,250 × 0.75 = 24,188 calls × 5,000 tokens = 120,938,000 tokens
           120,938,000 / 1,000,000 × $0.05 = $6.05 = ₹505

70b calls: 32,250 × 0.25 = 8,063 calls × 5,000 tokens = 40,313,000 tokens
           40,313,000 / 1,000,000 × $0.59 = $23.78 = ₹1,986

Total LLM cost: ₹505 + ₹1,986 = ₹2,491/month
```

**Current system at same scale:**
43,000 PPTs/month × ₹15 = ₹6,45,000/month

| | Current | Proposed |
|--|---------|---------|
| Monthly LLM cost | ₹6,45,000 | ₹2,491 |
| Per-PPT cost | ₹15.00 | ₹0.058 |
| **Savings** | | **₹6,42,509 (99.6%)** |

The math isn't aggressive — it's conservative. A 25% cache hit rate is achievable even without semantic caching. With semantic caching (bonus feature), hit rates could reach 40–50%, halving the already-low LLM cost further.
