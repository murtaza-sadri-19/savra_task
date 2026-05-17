from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal
from enum import Enum


class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


class PPTRequest(BaseModel):
    topic: str = Field(..., min_length=3, max_length=200, description="Presentation topic")
    grade: int = Field(..., ge=1, le=12, description="Grade/class level")
    slides: int = Field(..., ge=3, le=30, description="Number of slides")
    subject: str = Field(default="General", description="Subject area")

    @field_validator("topic")
    @classmethod
    def sanitize_topic(cls, v: str) -> str:
        return v.strip()


class SlideContent(BaseModel):
    slide_number: int
    title: str
    bullet_points: list[str]
    speaker_notes: Optional[str] = None
    layout: Literal["title", "content", "two-column", "summary"] = "content"


class PPTResult(BaseModel):
    title: str
    subject: str
    grade: int
    slides: list[SlideContent]
    total_slides: int


class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    message: str
    progress_pct: int = 0
    # Populated when done
    result: Optional[PPTResult] = None
    routing: Optional[dict] = None
    cache_hit: bool = False
    cost_inr: Optional[float] = None
    generation_time_ms: Optional[int] = None
    error: Optional[str] = None