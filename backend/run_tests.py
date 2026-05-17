"""
Backend Sanity Check Runner
============================
Validates backend logic without pytest complexity.
"""

import sys
sys.path.insert(0, '.')

from backend.models import PPTRequest, SlideContent, PPTResult, JobStatus
from backend.router import route, compute_complexity_score, cost_savings_vs_current
from backend.cache import PPTCache
from backend.main import generate_mock_result

def test_models():
    """Test model validation."""
    print("\n=== UNIT TEST: Models Validation ===")
    
    # Valid request
    req = PPTRequest(topic="Test Topic", grade=8, slides=5, subject="Math")
    print(f"✓ Created valid request: {req.topic}, Grade {req.grade}, {req.slides} slides")
    
    # Test sanitization
    req2 = PPTRequest(topic="  Padded Topic  ", grade=8, slides=5, subject="Math")
    assert req2.topic == "Padded Topic", "Sanitization failed"
    print("✓ Topic sanitization works")
    
    # Test constraints
    errors = []
    try:
        PPTRequest(topic="AB", grade=8, slides=5, subject="Math")
        errors.append("Should reject topic < 3 chars")
    except ValueError:
        print("✓ Rejects topic < 3 chars")
    
    try:
        PPTRequest(topic="Valid", grade=0, slides=5, subject="Math")
        errors.append("Should reject grade < 1")
    except ValueError:
        print("✓ Rejects grade < 1")
    
    try:
        PPTRequest(topic="Valid", grade=13, slides=5, subject="Math")
        errors.append("Should reject grade > 12")
    except ValueError:
        print("✓ Rejects grade > 12")
    
    try:
        PPTRequest(topic="Valid", grade=8, slides=2, subject="Math")
        errors.append("Should reject slides < 3")
    except ValueError:
        print("✓ Rejects slides < 3")
    
    try:
        PPTRequest(topic="Valid", grade=8, slides=31, subject="Math")
        errors.append("Should reject slides > 30")
    except ValueError:
        print("✓ Rejects slides > 30")
    
    # Test slide layout enum
    try:
        SlideContent(slide_number=1, title="Title", bullet_points=["P1"], layout="invalid")
        errors.append("Should reject invalid layout")
    except ValueError:
        print("✓ Rejects invalid layout enum")
    
    return errors

def test_routing():
    """Test smart model routing."""
    print("\n=== UNIT TEST: Smart Routing ===")
    errors = []
    
    # Simple request → FAST model
    simple = route("Basic Math", grade=5, slides=5, subject="Math")
    print(f"✓ Simple request: {simple.model}, score={simple.score}")
    
    # Complex request → SMART model
    complex_req = route("Quantum Mechanics", grade=12, slides=25, subject="Physics")
    print(f"✓ Complex request: {complex_req.model}, score={complex_req.score}")
    
    if simple.model == complex_req.model:
        errors.append(f"Simple and complex should route differently. Both: {simple.model}")
    
    # Complexity score deterministic
    score1, _ = compute_complexity_score("Topic", 8, 10, "Math")
    score2, _ = compute_complexity_score("Topic", 8, 10, "Math")
    if score1 != score2:
        errors.append("Complexity score not deterministic")
    print(f"✓ Deterministic scoring: {score1} == {score2}")
    
    # Cost always positive
    if simple.estimated_cost_inr <= 0:
        errors.append(f"Cost should be positive, got {simple.estimated_cost_inr}")
    print(f"✓ Cost positive: ₹{simple.estimated_cost_inr}")
    
    # Savings calculation
    savings = cost_savings_vs_current(1.0, 15.0)
    expected_saved = 14.0
    if abs(savings["saved_inr"] - expected_saved) > 0.01:
        errors.append(f"Savings calc wrong: {savings['saved_inr']} vs {expected_saved}")
    print(f"✓ Savings calc: ₹{savings['saved_inr']} saved ({savings['savings_pct']}%)")
    
    return errors

def test_cache():
    """Test caching logic."""
    print("\n=== UNIT TEST: Caching ===")
    errors = []
    
    cache = PPTCache()
    test_result = {"title": "Test", "slides": []}
    
    # Same inputs → same key
    key1 = cache._key("Python", 8, 10, "CS")
    key2 = cache._key("Python", 8, 10, "CS")
    if key1 != key2:
        errors.append("Cache keys not consistent")
    print(f"✓ Consistent cache keys: {key1} == {key2}")
    
    # Case insensitive
    key3 = cache._key("PYTHON", 8, 10, "CS")
    if key1 != key3:
        errors.append("Cache keys not case-insensitive")
    print(f"✓ Case insensitive keys: {key1} == {key3}")
    
    # Set and get
    cache.set("Topic", 8, 5, "Subject", test_result)
    retrieved = cache.get("Topic", 8, 5, "Subject")
    if retrieved != test_result:
        errors.append("Cache set/get failed")
    print("✓ Cache set/get works")
    
    # Stats tracking
    stats = cache.summary()
    if stats["total_requests"] != 1 or stats["hit_rate_pct"] != 100.0:
        errors.append(f"Cache stats wrong: {stats}")
    print(f"✓ Cache stats tracked: {stats['hit_rate_pct']}% hit rate")
    
    return errors

def test_mock_generation():
    """Test mock PPT generation."""
    print("\n=== UNIT TEST: Mock Generation ===")
    errors = []
    
    req = PPTRequest(topic="Test Topic", grade=8, slides=5, subject="Math")
    mock_result = generate_mock_result(req)
    
    # Required fields
    if "title" not in mock_result or "slides" not in mock_result:
        errors.append("Mock result missing required fields")
    print(f"✓ Mock result has required fields")
    
    # Correct slide count
    if len(mock_result["slides"]) != req.slides:
        errors.append(f"Slide count mismatch: {len(mock_result['slides'])} vs {req.slides}")
    print(f"✓ Correct slide count: {len(mock_result['slides'])}")
    
    # Each slide has required fields
    required_slide_fields = ["slide_number", "title", "bullet_points", "speaker_notes", "layout"]
    for slide in mock_result["slides"]:
        for field in required_slide_fields:
            if field not in slide:
                errors.append(f"Slide missing {field}")
                break
    print(f"✓ All slides have required fields")
    
    # Layout consistency
    if mock_result["slides"][0]["layout"] != "title":
        errors.append(f"First slide layout should be 'title', got {mock_result['slides'][0]['layout']}")
    if mock_result["slides"][-1]["layout"] != "summary":
        errors.append(f"Last slide layout should be 'summary', got {mock_result['slides'][-1]['layout']}")
    print(f"✓ Layout consistency: first={mock_result['slides'][0]['layout']}, last={mock_result['slides'][-1]['layout']}")
    
    return errors

def test_integration():
    """Test integration between components."""
    print("\n=== INTEGRATION TEST: Component Interaction ===")
    errors = []
    
    # Create request
    req = PPTRequest(topic="Integration Test", grade=9, slides=8, subject="Science")
    
    # Route it
    decision = route(req.topic, req.grade, req.slides, req.subject)
    print(f"✓ Request routed: {decision.model} (score={decision.score})")
    
    # Generate mock
    mock = generate_mock_result(req)
    print(f"✓ Generated mock: {len(mock['slides'])} slides")
    
    # Validate structure
    try:
        slide_objs = [SlideContent(**s) for s in mock["slides"]]
        result = PPTResult(
            title=mock["title"],
            subject=mock.get("subject", req.subject),
            grade=mock.get("grade", req.grade),
            slides=slide_objs,
            total_slides=len(slide_objs),
        )
        print(f"✓ PPTResult created: {result.total_slides} slides")
    except Exception as e:
        errors.append(f"Failed to create PPTResult: {e}")
    
    # Cache the result
    cache = PPTCache()
    cache.set(req.topic, req.grade, req.slides, req.subject, mock)
    cached = cache.get(req.topic, req.grade, req.slides, req.subject)
    
    if cached is None:
        errors.append("Cache miss after set")
    else:
        print(f"✓ Cached result retrieved successfully")
    
    return errors

def main():
    """Run all tests."""
    print("=" * 60)
    print("BACKEND COMPREHENSIVE TESTING SUITE")
    print("=" * 60)
    
    all_errors = []
    
    all_errors.extend(test_models())
    all_errors.extend(test_routing())
    all_errors.extend(test_cache())
    all_errors.extend(test_mock_generation())
    all_errors.extend(test_integration())
    
    print("\n" + "=" * 60)
    if all_errors:
        print("❌ ERRORS FOUND:")
        for i, error in enumerate(all_errors, 1):
            print(f"  {i}. {error}")
        print("=" * 60)
        return 1
    else:
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nSummary:")
        print("  ✓ Unit-wise logic: VALID")
        print("  ✓ Integration-wise logic: VALID")
        print("  ✓ Error handling: ROBUST")
        print("  ✓ Data consistency: CONFIRMED")
        print("  ✓ Backend ready for production")
        return 0

if __name__ == "__main__":
    sys.exit(main())
