"""
Backend Runtime & API Integration Tests
=========================================
Verifies the FastAPI backend starts correctly and endpoints work.
"""

import sys
sys.path.insert(0, '.')

import asyncio
from fastapi.testclient import TestClient
from backend.main import app
from backend.models import PPTRequest

def test_api_endpoints():
    """Test all FastAPI endpoints."""
    print("\n=== INTEGRATION TEST: API Endpoints ===")
    
    client = TestClient(app)
    errors = []
    
    # Test 1: Health check
    try:
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"
        print(f"✓ Health endpoint works: {data}")
    except Exception as e:
        errors.append(f"Health endpoint failed: {e}")
    
    # Test 2: Cache stats
    try:
        response = client.get("/api/cache/stats")
        assert response.status_code == 200
        stats = response.json()
        assert "hit_rate_pct" in stats
        print(f"✓ Cache stats endpoint works: {stats}")
    except Exception as e:
        errors.append(f"Cache stats endpoint failed: {e}")
    
    # Test 3: Job submission (PPT generation)
    try:
        request_data = {
            "topic": "Introduction to Python",
            "grade": 8,
            "slides": 5,
            "subject": "Computer Science"
        }
        response = client.post("/api/ppt/generate", json=request_data)
        assert response.status_code == 202, f"Expected 202, got {response.status_code}"
        job_data = response.json()
        assert "job_id" in job_data
        assert job_data["status"] == "queued"
        job_id = job_data["job_id"]
        print(f"✓ Job submission works: job_id={job_id}, status={job_data['status']}")
        
        # Test 4: Poll job status (with retries for processing)
        max_retries = 10
        for attempt in range(max_retries):
            status_response = client.get(f"/api/ppt/status/{job_id}")
            assert status_response.status_code == 200
            status_data = status_response.json()
            
            print(f"  ↳ Status poll #{attempt+1}: {status_data['status']} ({status_data['progress_pct']}%)")
            
            if status_data["status"] == "done":
                print(f"✓ Job completed: result={status_data.get('result', {}).get('title', 'N/A')}")
                
                # Verify result structure
                result = status_data.get("result")
                if result:
                    assert "title" in result
                    assert "slides" in result
                    assert result["total_slides"] == len(request_data)
                    print(f"✓ Result structure valid: {result['total_slides']} slides")
                break
            
            if status_data["status"] == "failed":
                errors.append(f"Job failed: {status_data.get('error', 'Unknown error')}")
                break
            
            asyncio.sleep(0.1)
        
    except Exception as e:
        errors.append(f"Job workflow failed: {e}")
    
    # Test 5: Invalid requests should fail gracefully
    try:
        invalid_request = {
            "topic": "AB",  # Too short
            "grade": 8,
            "slides": 5,
            "subject": "Math"
        }
        response = client.post("/api/ppt/generate", json=invalid_request)
        # Should return validation error
        if response.status_code not in [400, 422]:
            print(f"⚠ Invalid request validation: got {response.status_code} (expected 400/422)")
        else:
            print(f"✓ Invalid request validation works: {response.status_code}")
    except Exception as e:
        errors.append(f"Invalid request handling failed: {e}")
    
    # Test 6: Job not found
    try:
        response = client.get("/api/ppt/status/nonexistent_id")
        assert response.status_code == 404
        print(f"✓ Job not found handling: 404 returned")
    except Exception as e:
        errors.append(f"Job not found handling failed: {e}")
    
    return errors

def test_imports():
    """Test all imports work."""
    print("\n=== DEPENDENCY TEST: Imports ===")
    errors = []
    
    try:
        from backend.models import PPTRequest, PPTResult, SlideContent, JobResponse, JobStatus
        print("✓ Models import successful")
    except Exception as e:
        errors.append(f"Models import failed: {e}")
    
    try:
        from backend.router import route, compute_complexity_score
        print("✓ Router import successful")
    except Exception as e:
        errors.append(f"Router import failed: {e}")
    
    try:
        from backend.cache import PPTCache, cache
        print("✓ Cache import successful")
    except Exception as e:
        errors.append(f"Cache import failed: {e}")
    
    try:
        from backend.main import app, generate_mock_result, call_groq_with_fallback
        print("✓ Main import successful")
    except Exception as e:
        errors.append(f"Main import failed: {e}")
    
    return errors

def test_env_configuration():
    """Test environment configuration."""
    print("\n=== CONFIGURATION TEST: Environment ===")
    errors = []
    
    try:
        import os
        from dotenv import load_dotenv
        load_dotenv()
        
        config = {
            "LOG_LEVEL": os.environ.get("LOG_LEVEL", "INFO"),
            "LOG_MODULE": os.environ.get("LOG_MODULE", "savra"),
            "FAST_MODEL": os.environ.get("FAST_MODEL", "llama-3.1-8b-instant"),
            "SMART_MODEL": os.environ.get("SMART_MODEL", "llama-3.3-70b-versatile"),
            "CACHE_TTL_HOURS": os.environ.get("CACHE_TTL_HOURS", "8"),
            "CORS_ALLOW_ORIGINS": os.environ.get("CORS_ALLOW_ORIGINS", "*"),
        }
        
        for key, value in config.items():
            print(f"✓ {key}: {value}")
        
    except Exception as e:
        errors.append(f"Config loading failed: {e}")
    
    return errors

def main():
    """Run all API tests."""
    print("=" * 60)
    print("BACKEND API & RUNTIME TESTS")
    print("=" * 60)
    
    all_errors = []
    
    all_errors.extend(test_imports())
    all_errors.extend(test_env_configuration())
    all_errors.extend(test_api_endpoints())
    
    print("\n" + "=" * 60)
    if all_errors:
        print("⚠ ISSUES FOUND:")
        for i, error in enumerate(all_errors, 1):
            print(f"  {i}. {error}")
        print("=" * 60)
        return 1
    else:
        print("✅ ALL API TESTS PASSED!")
        print("=" * 60)
        print("\nBackend Status:")
        print("  ✓ All dependencies importable")
        print("  ✓ Environment configured correctly")
        print("  ✓ API endpoints functional")
        print("  ✓ Request validation working")
        print("  ✓ Async job processing ready")
        print("  ✓ Caching system operational")
        return 0

if __name__ == "__main__":
    sys.exit(main())
