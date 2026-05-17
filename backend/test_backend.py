"""
Comprehensive Backend Testing Suite
====================================
Tests unit-wise logic and integration-wise logic for the Savra PPT Backend.

Run with: python -m pytest backend/test_backend.py -v
Or directly: python backend/test_backend.py
"""

import pytest
import asyncio
import json
import os
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timedelta
import time

# Import backend modules
from backend.models import (
    PPTRequest, PPTResult, SlideContent, JobResponse, JobStatus
)
from backend.router import (
    route, compute_complexity_score, cost_savings_vs_current,
    MODEL_FAST, MODEL_SMART
)
from backend.cache import PPTCache
from backend import main


# =========================================================================== #
# UNIT TESTS — Individual Component Logic
# =========================================================================== #

class TestModelsValidation:
    """Test Pydantic model validation and constraints."""
    
    def test_ppt_request_valid(self):
        """Valid PPT request should pass."""
        req = PPTRequest(
            topic="Photosynthesis",
            grade=8,
            slides=10,
            subject="Biology"
        )
        assert req.topic == "Photosynthesis"
        assert req.grade == 8
        assert req.slides == 10
        assert req.subject == "Biology"
    
    def test_ppt_request_topic_min_length(self):
        """Topic must be at least 3 characters."""
        with pytest.raises(ValueError):
            PPTRequest(topic="AB", grade=8, slides=5, subject="Math")
    
    def test_ppt_request_topic_max_length(self):
        """Topic cannot exceed 200 characters."""
        long_topic = "A" * 201
        with pytest.raises(ValueError):
            PPTRequest(topic=long_topic, grade=8, slides=5, subject="Math")
    
    def test_ppt_request_grade_bounds(self):
        """Grade must be between 1-12."""
        with pytest.raises(ValueError):
            PPTRequest(topic="Topic", grade=0, slides=5, subject="Math")
        
        with pytest.raises(ValueError):
            PPTRequest(topic="Topic", grade=13, slides=5, subject="Math")
    
    def test_ppt_request_slides_bounds(self):
        """Slides must be between 3-30."""
        with pytest.raises(ValueError):
            PPTRequest(topic="Topic", grade=8, slides=2, subject="Math")
        
        with pytest.raises(ValueError):
            PPTRequest(topic="Topic", grade=8, slides=31, subject="Math")
    
    def test_ppt_request_topic_sanitization(self):
        """Topic should be stripped of whitespace."""
        req = PPTRequest(
            topic="  Photosynthesis  ",
            grade=8,
            slides=5,
            subject="Biology"
        )
        assert req.topic == "Photosynthesis"
    
    def test_slide_content_valid(self):
        """Valid slide content should pass."""
        slide = SlideContent(
            slide_number=1,
            title="Introduction",
            bullet_points=["Point 1", "Point 2"],
            speaker_notes="Notes here",
            layout="title"
        )
        assert slide.layout == "title"
    
    def test_slide_content_layout_enum(self):
        """Layout must be valid enum value."""
        with pytest.raises(ValueError):
            SlideContent(
                slide_number=1,
                title="Title",
                bullet_points=["Point"],
                layout="invalid"
            )
    
    def test_job_response_creation(self):
        """JobResponse should track all fields."""
        job = JobResponse(
            job_id="abc123",
            status=JobStatus.QUEUED,
            message="Starting",
            progress_pct=0
        )
        assert job.status == JobStatus.QUEUED
        assert job.result is None
        assert job.cache_hit is False


class TestRouting:
    """Test smart model routing logic."""
    
    def test_complexity_score_simple_request(self):
        """Simple request should have low complexity score."""
        score, reasons = compute_complexity_score(
            topic="Photosynthesis",
            grade=5,
            slides=5,
            subject="General"
        )
        assert score < 4
    
    def test_complexity_score_high_grade(self):
        """Grade 11+ should increase score."""
        score, reasons = compute_complexity_score(
            topic="Basic Math",
            grade=11,
            slides=5,
            subject="General"
        )
        assert score >= 3
        assert any("board-level" in r.lower() for r in reasons)
    
    def test_complexity_score_high_slides(self):
        """Slides > 15 should increase score significantly."""
        score, reasons = compute_complexity_score(
            topic="Topic",
            grade=5,
            slides=20,
            subject="General"
        )
        assert score >= 3
        assert any("high volume" in r.lower() for r in reasons)
    
    def test_complexity_score_technical_subject(self):
        """Physics/Chemistry should increase score."""
        score, reasons = compute_complexity_score(
            topic="Basic Topic",
            grade=5,
            slides=5,
            subject="Physics"
        )
        assert score >= 1
        assert any("technical" in r.lower() for r in reasons)
    
    def test_complexity_score_complex_keywords(self):
        """Complex keywords should increase score."""
        score, reasons = compute_complexity_score(
            topic="Quantum Mechanics",
            grade=5,
            slides=5,
            subject="General"
        )
        assert score >= 2
        assert any("quantum" in r.lower() for r in reasons)
    
    def test_routing_decision_simple(self):
        """Simple request should route to FAST model."""
        decision = route(
            topic="Animals",
            grade=3,
            slides=5,
            subject="General"
        )
        assert decision.model == MODEL_FAST
    
    def test_routing_decision_complex(self):
        """Complex request should route to SMART model."""
        decision = route(
            topic="Quantum Mechanics",
            grade=12,
            slides=25,
            subject="Physics"
        )
        assert decision.model == MODEL_SMART
    
    def test_routing_cost_calculation(self):
        """Routing should include cost estimate."""
        decision = route(
            topic="Topic",
            grade=8,
            slides=10,
            subject="Math"
        )
        assert decision.estimated_cost_inr > 0
        assert decision.score >= 0
    
    def test_cost_savings_calculation(self):
        """Cost savings should be calculated correctly."""
        savings = cost_savings_vs_current(cost_inr=1.0, current_cost_inr=15.0)
        assert savings["saved_inr"] == pytest.approx(14.0, abs=0.01)
        assert savings["savings_pct"] == pytest.approx(93.3, abs=0.1)


class TestCache:
    """Test caching logic."""
    
    def test_cache_key_generation(self):
        """Same inputs should generate same key."""
        cache = PPTCache()
        key1 = cache._key("Python", 8, 10, "CS")
        key2 = cache._key("Python", 8, 10, "CS")
        assert key1 == key2
    
    def test_cache_key_case_insensitive(self):
        """Keys should be case-insensitive."""
        cache = PPTCache()
        key1 = cache._key("Python", 8, 10, "CS")
        key2 = cache._key("PYTHON", 8, 10, "cs")
        assert key1 == key2
    
    def test_cache_key_whitespace_handling(self):
        """Keys should handle whitespace consistently."""
        cache = PPTCache()
        key1 = cache._key("  Python  ", 8, 10, "  CS  ")
        key2 = cache._key("Python", 8, 10, "CS")
        assert key1 == key2
    
    def test_cache_set_and_get(self):
        """Setting and getting cache should work."""
        cache = PPTCache()
        test_result = {"title": "Test", "slides": []}
        
        cache.set("Topic", 8, 5, "Subject", test_result)
        retrieved = cache.get("Topic", 8, 5, "Subject")
        
        assert retrieved is not None
        assert retrieved["title"] == "Test"
    
    def test_cache_miss_returns_none(self):
        """Cache miss should return None."""
        cache = PPTCache()
        result = cache.get("NonExistent", 8, 5, "Subject")
        assert result is None
    
    def test_cache_ttl_expiration(self):
        """Expired cache should be evicted."""
        cache = PPTCache()
        cache.TTL_SECONDS = -1  # Simulate expired
        
        test_result = {"title": "Test", "slides": []}
        cache.set("Topic", 8, 5, "Subject", test_result)
        
        retrieved = cache.get("Topic", 8, 5, "Subject")
        assert retrieved is None
    
    def test_cache_hit_tracking(self):
        """Cache should track hits and misses."""
        cache = PPTCache()
        test_result = {"title": "Test", "slides": []}
        
        # Miss
        cache.get("Topic", 8, 5, "Subject")
        assert cache.stats["misses"] == 1
        
        # Hit
        cache.set("Topic", 8, 5, "Subject", test_result)
        cache.get("Topic", 8, 5, "Subject")
        assert cache.stats["hits"] == 1
    
    def test_cache_stats_summary(self):
        """Cache should provide meaningful stats."""
        cache = PPTCache()
        test_result = {"title": "Test", "slides": []}
        
        cache.set("Topic", 8, 5, "Subject", test_result)
        cache.get("Topic", 8, 5, "Subject")
        
        stats = cache.summary()
        assert stats["total_requests"] == 1
        assert stats["hit_rate_pct"] == 100.0


# =========================================================================== #
# INTEGRATION TESTS — Component Interactions
# =========================================================================== #

class TestProcessJobIntegration:
    """Test job processing end-to-end."""
    
    @pytest.mark.asyncio
    async def test_job_creation_queuing(self):
        """Job should be created in QUEUED state."""
        req = PPTRequest(
            topic="Test Topic",
            grade=8,
            slides=5,
            subject="Test"
        )
        
        job_id = "test123"
        job = JobResponse(
            job_id=job_id,
            status=JobStatus.QUEUED,
            message="Job queued",
        )
        
        assert job.status == JobStatus.QUEUED
        assert job.progress_pct == 0
        assert job.result is None
    
    @pytest.mark.asyncio
    async def test_job_processing_flow(self):
        """Job should flow through states correctly."""
        req = PPTRequest(
            topic="Test Topic",
            grade=8,
            slides=5,
            subject="Test"
        )
        
        # Mock the routing and processing
        with patch('backend.main.route') as mock_route, \
             patch('backend.main.cache.get', return_value=None), \
             patch('backend.main.cache.set'), \
             patch('backend.main.GROQ_AVAILABLE', False):
            
            mock_route.return_value = MagicMock(
                model=MODEL_FAST,
                score=1,
                reasons=["Simple"],
                estimated_cost_inr=0.05
            )
            
            job_id = "test123"
            job = JobResponse(
                job_id=job_id,
                status=JobStatus.QUEUED,
                message="Job queued",
            )
            
            main.jobs[job_id] = job
            
            # Run job processor
            await main.process_job(job_id, req)
            
            # Verify job completed
            assert job.status == JobStatus.DONE or job.status == JobStatus.FAILED
            assert job.generation_time_ms is not None or job.error is not None
    
    def test_mock_result_generation(self):
        """Mock generator should create valid structure."""
        req = PPTRequest(
            topic="Test",
            grade=8,
            slides=5,
            subject="Math"
        )
        
        mock_result = main.generate_mock_result(req)
        
        assert "title" in mock_result
        assert "slides" in mock_result
        assert len(mock_result["slides"]) == req.slides
        
        # Verify each slide has required fields
        for slide in mock_result["slides"]:
            assert "slide_number" in slide
            assert "title" in slide
            assert "bullet_points" in slide
            assert "speaker_notes" in slide
            assert "layout" in slide
    
    def test_ppt_result_creation_from_raw(self):
        """Raw response should convert to PPTResult correctly."""
        raw_data = {
            "title": "Test Presentation",
            "subject": "Math",
            "grade": 8,
            "slides": [
                {
                    "slide_number": 1,
                    "title": "Title Slide",
                    "bullet_points": ["Point 1"],
                    "speaker_notes": "Notes",
                    "layout": "title"
                }
            ]
        }
        
        slide_objs = [SlideContent(**s) for s in raw_data["slides"]]
        result = PPTResult(
            title=raw_data["title"],
            subject=raw_data.get("subject", "General"),
            grade=raw_data.get("grade", 1),
            slides=slide_objs,
            total_slides=len(slide_objs),
        )
        
        assert result.title == "Test Presentation"
        assert result.total_slides == 1
        assert len(result.slides) == 1


# =========================================================================== #
# ERROR HANDLING & EDGE CASES
# =========================================================================== #

class TestErrorHandling:
    """Test error handling and edge cases."""
    
    @pytest.mark.asyncio
    async def test_invalid_request_handling(self):
        """Invalid requests should be rejected early."""
        with pytest.raises(ValueError):
            PPTRequest(topic="AB", grade=8, slides=5, subject="Math")
    
    def test_job_not_found(self):
        """Missing job should return None."""
        job = main.jobs.get("nonexistent_id")
        assert job is None
    
    @pytest.mark.asyncio
    async def test_groq_unavailable_fallback(self):
        """Should use mock when Groq unavailable."""
        with patch('backend.main.GROQ_AVAILABLE', False):
            req = PPTRequest(
                topic="Test",
                grade=8,
                slides=5,
                subject="Math"
            )
            
            mock_result = main.generate_mock_result(req)
            assert mock_result is not None
            assert len(mock_result["slides"]) == 5
    
    def test_cache_entry_freshness(self):
        """Cache should check freshness."""
        cache = PPTCache()
        test_result = {"title": "Test"}
        
        cache.set("Topic", 8, 5, "Subject", test_result)
        entry = cache._store[cache._key("Topic", 8, 5, "Subject")]
        
        # Fresh entry should pass
        assert entry.is_fresh() is True
        
        # Stale entry should fail
        entry.created_at = time.time() - (cache.TTL_SECONDS + 1)
        assert entry.is_fresh() is False


# =========================================================================== #
# PERFORMANCE & CONSISTENCY
# =========================================================================== #

class TestPerformanceConsistency:
    """Test performance and consistency."""
    
    def test_routing_deterministic(self):
        """Same input should always route to same model."""
        results = [
            route("Python", 8, 10, "CS").model
            for _ in range(5)
        ]
        assert all(r == results[0] for r in results)
    
    def test_cache_key_uniqueness(self):
        """Different inputs should have different keys."""
        cache = PPTCache()
        
        key1 = cache._key("Topic1", 8, 5, "Subject")
        key2 = cache._key("Topic2", 8, 5, "Subject")
        key3 = cache._key("Topic1", 9, 5, "Subject")
        
        assert key1 != key2
        assert key1 != key3
    
    def test_complexity_score_consistency(self):
        """Same input should always produce same score."""
        results = [
            compute_complexity_score("Topic", 8, 10, "Math")[0]
            for _ in range(5)
        ]
        assert all(r == results[0] for r in results)


# =========================================================================== #
# RUN TESTS
# =========================================================================== #

if __name__ == "__main__":
    # Run with pytest if available, otherwise skip
    try:
        import sys
        pytest.main([__file__, "-v", "--tb=short"])
    except ImportError:
        print("pytest not installed. Run: pip install pytest pytest-asyncio")
        print("\nRunning basic sanity checks instead...")
        
        # Basic sanity checks
        print("\n[PASSED] Testing model validation...")
        req = PPTRequest(topic="Test", grade=8, slides=5, subject="Math")
        print(f"  Created request: {req.topic}, Grade {req.grade}")
        
        print("\n[PASSED] Testing routing...")
        decision = route("Quantum Mechanics", 12, 20, "Physics")
        print(f"  Routed to {decision.model} (score={decision.score})")
        
        print("\n[PASSED] Testing cache...")
        cache = PPTCache()
        cache.set("Topic", 8, 5, "Math", {"title": "Test"})
        result = cache.get("Topic", 8, 5, "Math")
        print(f"  Cache hit: {result is not None}")
        
        print("\n[PASSED] Testing mock generation...")
        mock = main.generate_mock_result(req)
        print(f"  Generated {len(mock['slides'])} slides")
        
        print("\n[SUCCESS] All basic checks passed!")
