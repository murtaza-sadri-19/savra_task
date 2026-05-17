"""
Savra PPT Generation Backend
-----------------------------
FastAPI app with async job processing, smart model routing, and caching.

Key design decisions:
  - Async over sync: teacher gets job_id immediately, polls for status
  - Groq for inference: 10-20x faster than Gemini, fraction of the cost
  - Smart routing: complexity score decides 8b vs 70b model
  - Exact cache: SHA-256 hash of request params, 8h TTL
  - Structured JSON output: Groq JSON mode guarantees parseable responses
  - Graceful degradation: 503/rate-limit → retry with backoff → fallback model

Run:
  pip install fastapi uvicorn groq pydantic
  GROQ_API_KEY=your_key uvicorn main:app --reload
"""

import asyncio
import json
import os
import time
import uuid
import logging
from contextlib import asynccontextmanager
from typing import Optional
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from .models import PPTRequest, JobResponse, JobStatus, PPTResult, SlideContent
from .router import route, cost_savings_vs_current
from .cache import cache

# Load environment variables from .env file
load_dotenv()

# Configure logging
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
LOG_MODULE = os.environ.get("LOG_MODULE", "savra")
logging.basicConfig(level=getattr(logging, LOG_LEVEL))
log = logging.getLogger(LOG_MODULE)

# In-memory job store — use Redis in production
jobs: dict[str, JobResponse] = {}

# --------------------------------------------------------------------------- #
# Groq client setup
# --------------------------------------------------------------------------- #
try:
    from groq import AsyncGroq
    groq_client = AsyncGroq(api_key=os.environ.get("GROQ_API_KEY", ""))
    GROQ_AVAILABLE = bool(os.environ.get("GROQ_API_KEY"))
except ImportError:
    groq_client = None
    GROQ_AVAILABLE = False
    log.warning("groq package not installed — running in mock mode")

# --------------------------------------------------------------------------- #
# Model and LLM configuration
# --------------------------------------------------------------------------- #
FAST_MODEL = os.environ.get("FAST_MODEL", "llama-3.1-8b-instant")
SMART_MODEL = os.environ.get("SMART_MODEL", "llama-3.3-70b-versatile")

# Retry configuration
MAX_RETRIES = int(os.environ.get("MAX_RETRIES", "3"))
RETRY_DELAYS = [int(x) for x in os.environ.get("RETRY_DELAYS", "1,3,7").split(",")]

# LLM parameters
TEMPERATURE = float(os.environ.get("TEMPERATURE", "0.4"))
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "4096"))

# --------------------------------------------------------------------------- #
# Prompts
# --------------------------------------------------------------------------- #

SYSTEM_PROMPT = """You are an expert educational content creator for Indian schools.
Generate presentation slide content that is:
- Age-appropriate for the specified grade
- Aligned with NCERT/CBSE curriculum
- Comprehensive: 4-6 bullet points per slide, each 15-25 words with detailed explanations
- Pedagogically structured: concept → definition → examples → real-world applications → key takeaway
- Include practical examples, diagram descriptions, and learning objectives

CRITICAL: Respond ONLY with valid JSON. No markdown, no explanation, no preamble.
"""

def build_user_prompt(req: PPTRequest) -> str:
    return f"""Generate a comprehensive {req.slides}-slide presentation on "{req.topic}" for Grade {req.grade} {req.subject}.

Each slide should include:
- 4-6 detailed bullet points with practical examples
- Comprehensive speaker notes (2-3 sentences minimum) with learning outcomes
- Relevant real-world applications and context

Return this exact JSON structure:
{{
  "title": "Comprehensive presentation title with learning objectives",
  "subject": "{req.subject}",
  "grade": {req.grade},
  "slides": [
    {{
      "slide_number": 1,
      "title": "Detailed slide title with subtopic",
      "bullet_points": ["Comprehensive point 1 with context", "Detailed point 2 with example", "Key concept 3 with application", "Important point 4 with explanation"],
      "speaker_notes": "Detailed speaker notes explaining the concept, providing examples, and connecting to real-world applications. Include learning outcomes and why this matters.",
      "layout": "title"
    }}
  ]
}}

Slide layout options: "title" (first slide with objectives), "content" (main slides), "two-column" (comparisons), "summary" (final recap with key takeaways).
Generate exactly {req.slides} slides. First slide layout = "title", last slide layout = "summary". Each bullet point should be 15-25 words."""


async def call_groq_with_fallback(prompt: str, model: str) -> tuple[str, str]:
    """
    Call Groq, retry on 503/rate-limit, fall back to alternate model.
    Returns (raw_json_text, model_actually_used).

    Failure handling:
      Attempt 1: target model
      Attempt 2: target model (backoff 1s)
      Attempt 3: alternate model (backoff 3s)  ← smart fallback, not just cheaper
      Raises if all attempts fail
    """
    models_to_try = [model, model, (FAST_MODEL if model == SMART_MODEL else SMART_MODEL)]

    last_error = None
    for attempt, m in enumerate(models_to_try):
        try:
            if attempt > 0:
                await asyncio.sleep(RETRY_DELAYS[attempt - 1])

            log.info(f"Groq call attempt {attempt+1} with model={m}")
            resp = await groq_client.chat.completions.create(
                model=m,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
            )
            return resp.choices[0].message.content, m

        except Exception as e:
            last_error = e
            err_str = str(e).lower()
            if "503" in err_str or "rate" in err_str or "overload" in err_str:
                log.warning(f"Groq {m} overloaded on attempt {attempt+1}: {e}")
                continue
            raise  # non-recoverable error

    raise RuntimeError(f"All Groq attempts failed. Last error: {last_error}")


# --------------------------------------------------------------------------- #
# Mock generator (no API key available)
# --------------------------------------------------------------------------- #

def generate_mock_result(req: PPTRequest) -> dict:
    """Generate detailed mock slides with 25% more content than baseline."""
    slides = []
    for i in range(1, req.slides + 1):
        layout = "title" if i == 1 else ("summary" if i == req.slides else "content")
        
        if i == 1:
            # Title slide with objectives
            title = f"Introduction to {req.topic} — Grade {req.grade}"
            bullet_points = [
                f"Understanding the fundamentals of {req.topic} in {req.subject}",
                f"Key concepts and definitions relevant to Grade {req.grade} NCERT curriculum standards",
                f"Learning objectives and real-world applications of {req.topic} in daily life",
                f"Connection to previous knowledge and advanced topics to explore later",
                f"Practical examples and hands-on activities throughout this presentation",
            ]
            speaker_notes = f"Welcome to this comprehensive lesson on {req.topic}. Today we will explore fundamental concepts aligned with NCERT curriculum for Grade {req.grade} {req.subject}. We will examine definitions, practical applications, and connect this knowledge to real-world scenarios that students encounter daily. Make sure students understand these concepts as they form the foundation for advanced topics."
        elif i == req.slides:
            # Summary slide with key takeaways
            title = f"Summary: Key Takeaways and Learning Outcomes on {req.topic}"
            bullet_points = [
                f"Core principles of {req.topic} essential for Grade {req.grade} mastery and beyond",
                f"Interconnected concepts and their practical implications in {req.subject} applications",
                f"Real-world applications and career relevance in various {req.subject} fields",
                f"Further learning resources, advanced topics, and extensions for gifted students",
                f"Practice exercises, assessment strategies, and evaluation methods for retention",
            ]
            speaker_notes = f"In summary, the fundamental concepts of {req.topic} are critical for understanding advanced {req.subject}. Remember the key principles we discussed, how they connect to real-world applications, and how this knowledge forms the foundation for advanced topics in your academic journey. Practice these concepts regularly, explore additional resources for deeper understanding, and apply them to solve real-world problems."
        else:
            # Content slides with detailed information
            title = f"Section {i}: Detailed Exploration of {req.topic} Concepts"
            bullet_points = [
                f"Core concept {i-1}.1: Definition and fundamental principles defining {req.topic}",
                f"Key principle {i-1}.2: Important characteristics, classifications, and categories in {req.subject}",
                f"Practical example {i-1}.3: Real-world application relevant to Grade {req.grade} students' experiences",
                f"Critical analysis {i-1}.4: How this concept connects to broader {req.subject} topics and themes",
                f"Learning outcome {i-1}.5: What students should understand, retain, and apply from this section",
            ]
            speaker_notes = f"This section explores the deeper aspects of {req.topic} for Grade {req.grade} learners. Pay careful attention to how these concepts build upon previous knowledge covered earlier. The practical examples illustrate why understanding this is important in real-world contexts and professional settings. Encourage students to ask questions, make connections to their own experiences, and think critically about applications. This foundational understanding is absolutely essential for mastering advanced concepts and succeeding in higher-level courses."
        
        slides.append({
            "slide_number": i,
            "title": title,
            "bullet_points": bullet_points,
            "speaker_notes": speaker_notes,
            "layout": layout,
        })
    
    return {
        "title": f"{req.topic} — Comprehensive Guide for Grade {req.grade} {req.subject}",
        "subject": req.subject,
        "grade": req.grade,
        "slides": slides
    }


# --------------------------------------------------------------------------- #
# Job processor (runs in background)
# --------------------------------------------------------------------------- #

async def process_job(job_id: str, req: PPTRequest):
    job = jobs[job_id]
    start_ms = time.time() * 1000

    try:
        job.status = JobStatus.PROCESSING
        job.progress_pct = 10
        job.message = "Routing request..."

        # --- Step 1: Smart routing ---
        decision = route(req.topic, req.grade, req.slides, req.subject)
        job.routing = {
            "model": decision.model,
            "complexity_score": decision.score,
            "reasons": decision.reasons,
            "estimated_cost_inr": decision.estimated_cost_inr,
        }
        job.progress_pct = 20
        job.message = f"Routed to {decision.model.split('-')[1]}-param model"

        # --- Step 2: Cache check ---
        cached = cache.get(req.topic, req.grade, req.slides, req.subject)
        if cached:
            cache_savings = float(os.environ.get("CACHE_SAVINGS_INR", "15.0"))
            cache.record_savings(cache_savings)  # saved vs current cost
            job.cache_hit = True
            job.cost_inr = 0.0
            job.progress_pct = 90
            job.message = "Cache hit — serving instantly"
            await asyncio.sleep(0.2)  # brief delay to simulate real async
            raw_data = cached
        else:
            # --- Step 3: LLM call ---
            job.progress_pct = 40
            job.message = "Generating slide content..."

            if GROQ_AVAILABLE:
                prompt = build_user_prompt(req)
                raw_json, model_used = await call_groq_with_fallback(prompt, decision.model)
                raw_data = json.loads(raw_json)
                if model_used != decision.model:
                    job.routing["fallback_used"] = True
                    job.routing["model_used"] = model_used
            else:
                await asyncio.sleep(1.5)  # simulate latency
                raw_data = generate_mock_result(req)
                job.routing["mock_mode"] = True

            cache.set(req.topic, req.grade, req.slides, req.subject, raw_data)
            job.cost_inr = decision.estimated_cost_inr

        # --- Step 4: Parse & validate result ---
        job.progress_pct = 85
        job.message = "Finalizing slides..."

        slide_objs = [SlideContent(**s) for s in raw_data["slides"]]
        result = PPTResult(
            title=raw_data["title"],
            subject=raw_data.get("subject", req.subject),
            grade=raw_data.get("grade", req.grade),
            slides=slide_objs,
            total_slides=len(slide_objs),
        )

        elapsed = int(time.time() * 1000 - start_ms)
        job.result = result
        job.status = JobStatus.DONE
        job.progress_pct = 100
        job.generation_time_ms = elapsed
        job.message = f"Done in {elapsed}ms"

        savings = cost_savings_vs_current(job.cost_inr or 0)
        log.info(
            f"[{job_id}] Complete | model={decision.model} | "
            f"cache_hit={job.cache_hit} | time={elapsed}ms | "
            f"cost=₹{job.cost_inr} | saved={savings['savings_pct']}%"
        )

    except Exception as e:
        log.error(f"[{job_id}] Failed: {e}")
        job.status = JobStatus.FAILED
        job.error = str(e)
        job.message = "Generation failed — please retry"


# --------------------------------------------------------------------------- #
# FastAPI app
# --------------------------------------------------------------------------- #

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info(f"Savra PPT backend starting | groq_available={GROQ_AVAILABLE}")
    yield
    log.info("Savra PPT backend shutting down")


# Application configuration from environment
APP_TITLE = os.environ.get("APP_TITLE", "Savra PPT Generator")
APP_VERSION = os.environ.get("APP_VERSION", "0.1.0")

app = FastAPI(title=APP_TITLE, version=APP_VERSION, lifespan=lifespan)

# CORS configuration from environment
cors_origins = os.environ.get("CORS_ALLOW_ORIGINS", "*")
if cors_origins == "*":
    cors_origins = ["*"]
else:
    cors_origins = [origin.strip() for origin in cors_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/ppt/generate", response_model=JobResponse, status_code=202)
async def generate_ppt(req: PPTRequest, background_tasks: BackgroundTasks):
    """
    Submit a PPT generation request.
    Returns a job_id immediately (202 Accepted).
    Poll /api/ppt/status/{job_id} for progress and result.
    """
    job_id = str(uuid.uuid4())[:8]
    job = JobResponse(
        job_id=job_id,
        status=JobStatus.QUEUED,
        message="Job queued",
    )
    jobs[job_id] = job
    background_tasks.add_task(process_job, job_id, req)
    return job


@app.get("/api/ppt/status/{job_id}", response_model=JobResponse)
async def get_status(job_id: str):
    """Poll job status. Returns full result when status == 'done'."""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/api/cache/stats")
async def cache_stats():
    """Cache telemetry — useful for monitoring cost savings."""
    return cache.summary()


@app.get("/api/health")
async def health():
    return {"status": "ok", "groq_available": GROQ_AVAILABLE, "jobs_in_memory": len(jobs)}