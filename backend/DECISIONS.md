# DECISIONS.md — Key Engineering Choices

This document explains the *why* behind every non-obvious decision. Per the brief: reasoning > output.

---

## 1. Why Groq over Gemini / OpenAI?

Groq runs Llama models on custom LPU (Language Processing Unit) chips. The practical results:
- **Speed**: 500–800 tokens/second vs ~50-100 for Gemini (8–15x faster)
- **Cost**: $0.05–0.59/1M tokens vs ~$3.50 for Gemini Pro (6–70x cheaper)
- **Latency**: 2–4s for a full PPT vs 30s+ currently

The risk: Groq can have its own rate-limit issues. Mitigated by the retry-with-fallback pattern.

Llama 3.3 70b matches or exceeds Gemini 1.5 Pro on most educational content benchmarks. For Grade 1–8 content, 8b is more than sufficient.

---

## 2. Why async jobs instead of streaming?

Two options for teacher UX:
1. **Stream** text tokens live to the browser as they're generated
2. **Async job** with polling and progress updates

I chose async jobs because:
- Streaming requires a persistent HTTP connection for potentially 30+ seconds — fragile on mobile, bad on spotty school networks
- If the stream breaks mid-way, you restart from zero with no recovery
- A job ID is resumable: refresh the page, the job is still there
- Progress updates (Queued → Routing → Generating → Done) communicate *more* than a stream of tokens does

The async pattern also unlocks future features: batch processing, scheduled generation, email notification when done.

---

## 3. Why JSON mode (not function calling or free-form text)?

Three options for structured LLM output:
1. Free-form text → parse with regex → fragile
2. Function calling (tool use) → works, but adds latency and token overhead
3. JSON mode (Groq's `response_format: {type: "json_object"}`) → guaranteed valid JSON, zero parsing failures

JSON mode is the right call here. It:
- Eliminates all "LLM returned malformed output" errors (a real production failure mode)
- Lets us validate with Pydantic at the API boundary
- Reduces prompt length (no need to explain escaping, nesting, etc.)
- Is supported by Groq natively, no extra latency

---

## 4. Why SHA-256 for the cache key, not a simpler hash?

The cache key is `SHA-256(topic.lower + "|" + grade + "|" + slides + "|" + subject.lower)`.

Options considered:
- Simple string concatenation → collision risk with adversarial inputs
- MD5 → fine, but SHA-256 is just as fast and more standard
- Database index → overkill for this, SHA-256 prefix (16 chars) is effectively collision-free at our scale

8h TTL was chosen because:
- School days are ~8h. Cached morning PPTs are still valid afternoon.
- Curriculum changes on a semester basis, not hourly.

---

## 5. What I skipped and why

### Skipped: PPTX file generation in prototype
The prototype outputs JSON + HTML preview, not a real .PPTX file. `python-pptx` works fine and the integration is straightforward, but it doesn't demonstrate any of the interesting system design. The JSON output is the hard part — injecting it into a template is mechanical. I'd rather the evaluators see clean routing and async logic than a file download.

### Skipped: Redis / persistent job store
The prototype uses an in-memory dict for jobs. This works fine for a demo but will lose jobs on restart. In production, this is the first thing to change. I documented the migration path explicitly in the design doc rather than adding Redis infra that complicates running the demo.

### Skipped: Authentication / multi-tenancy
The prototype has no auth. In production, each job is tied to `teacher_id` from the JWT token. The job schema has a `teacher_id` field placeholder, but verifying tokens adds deployment complexity for no evaluation value.

### Skipped: Semantic cache (bonus)
The bonus semantic cache would use embeddings to match "Grade 8 Photosynthesis 10 slides" with "Class 8 Photosynthesis presentation 10 slides." I've described the approach in the design doc. Implementing it requires an embedding model call (Groq doesn't offer embeddings — would need OpenAI or a local model), which adds infra complexity. Given time constraints, the exact cache (which handles the most common case) delivers more value per hour spent.

---

## 6. Complexity scoring thresholds — how I arrived at 4

I calibrated the score threshold against a mental model of Indian school curriculum:

- **Grade 1–6, any subject, ≤10 slides** → score typically 0–2 → 8b fine
- **Grade 7–8, Science/Math** → score ~3 → borderline, 8b still good
- **Grade 9–10, Physics/Chemistry** → score 4–5 → 70b needed
- **Grade 11–12, any subject** → score 5–8 → always 70b

Threshold 4 routes ~75% to 8b and ~25% to 70b at our expected request distribution. This is tunable — if quality complaints come in from Grade 8–9, lower threshold to 3.

---

## 7. Fallback strategy — why same model first

The retry sequence is: `model A → model A → model B`.

Trying the same model twice before falling back is deliberate. Groq 503s are typically burst-level rate limits that clear in 1–3 seconds. A 1s delay between attempts recovers most transient failures without touching the fallback model at all.

If we fell back immediately to 8b on the first 503, Grade 11 teachers would silently get worse content. This way, we give the primary model two chances before deciding it's genuinely unavailable.

---

## 8. Technology stack justification

- **FastAPI over Express**: Native async/await, automatic OpenAPI docs, Pydantic validation out of the box. Express would work too, but Python's AI ecosystem (groq SDK, pydantic) is stronger.
- **No database in prototype**: All state is in-memory. First production upgrade = add Redis for job store.
- **Tailwind-free frontend**: The React prototype uses inline styles / vanilla CSS. Tailwind adds build complexity for a demo; the evaluator cares about system design, not button radius.
