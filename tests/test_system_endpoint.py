import sys
import os

# Append workspace root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from backend.main import app
from backend.config import settings

def get_headers():
    headers = {}
    if settings.jarvis_api_key:
        headers["X-Jarvis-API-Key"] = settings.jarvis_api_key
    return headers

def safe_print(*args, **kwargs):
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        new_args = []
        for arg in args:
            if isinstance(arg, str):
                new_args.append(arg.encode('ascii', errors='replace').decode('ascii'))
            else:
                new_args.append(arg)
        print(*new_args, **kwargs)

def test_system_status_endpoint():
    safe_print("\n--- 1. Testing GET /api/system/status Telemetry Endpoint ---")
    client = TestClient(app)
    
    response = client.get("/api/system/status", headers=get_headers())
    safe_print(f"Status Code: {response.status_code}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    data = response.json()
    safe_print(f"Response Data Keys: {list(data.keys())}")
    
    assert data["status"] == "online"
    assert "timestamp" in data
    assert "cpu" in data
    assert "ram" in data
    assert "disk" in data
    assert "battery" in data
    assert "os" in data
    
    safe_print(f"  - CPU: {data['cpu']['percent']}% ({data['cpu']['cores']} cores)")
    safe_print(f"  - RAM: {data['ram']['percent']}% ({data['ram']['used_gb']} GB / {data['ram']['total_gb']} GB)")
    safe_print(f"  - Disk: {data['disk']['percent']}% ({data['disk']['used_gb']} GB / {data['disk']['total_gb']} GB)")
    safe_print(f"  - Battery: {data['battery']['percent']}% ({data['battery']['status']})")
    safe_print(f"  - OS: {data['os']['system']} {data['os']['release']} ({data['os']['arch']})")
    
    safe_print("[PASS] /api/system/status telemetry verified successfully for mobile client.")

def test_memory_endpoints_via_http():
    safe_print("\n--- 2. Testing Memory HTTP Endpoints ---")
    client = TestClient(app)
    
    # 1. Remember fact
    res_rem = client.post("/api/memory/remember", json={
        "content": "Mobile app created with Flutter 3.0",
        "key": "mobile_framework",
        "category": "project"
    }, headers=get_headers())
    assert res_rem.status_code == 200
    safe_print("[PASS] POST /api/memory/remember succeeded.")
    
    # 2. Recall memory
    res_rec = client.get("/api/memory/recall?query=Flutter", headers=get_headers())
    assert res_rec.status_code == 200
    rec_data = res_rec.json()
    assert len(rec_data["results"]) > 0
    safe_print(f"[PASS] GET /api/memory/recall retrieved {len(rec_data['results'])} results.")


if __name__ == "__main__":
    safe_print("=== Starting JARVIS Version 6 Mobile Telemetry Tests ===")
    try:
        test_system_status_endpoint()
        test_memory_endpoints_via_http()
        safe_print("\n[ALL PASS] JARVIS Version 6 Mobile API Endpoints validated successfully!")
        sys.exit(0)
    except AssertionError as ae:
        safe_print(f"\n[FAIL] Assertion failed: {ae}")
        sys.exit(1)
    except Exception as e:
        safe_print(f"\n[FAIL] Unexpected error: {e}")
        sys.exit(1)
