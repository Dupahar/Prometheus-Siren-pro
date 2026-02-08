import sys
import os
import requests
import json

def test_dashboard():
    print("--- Testing Dashboard Service (UI & API) ---")
    base_url = "http://localhost:8080"
    
    # 1. Test UI Serving (Index.html)
    try:
        resp = requests.get(base_url)
        if resp.status_code == 200 and "<html" in resp.text:
            print("✅ PASS | UI Endpoint (/) is serving HTML")
        else:
            print(f"❌ FAIL | UI Endpoint returned {resp.status_code}")
    except Exception as e:
        print(f"❌ FAIL | Could not connect to UI: {e}")
        return

    # 2. Test Stats API (Mocked Backend)
    try:
        resp = requests.get(f"{base_url}/api/stats")
        if resp.status_code == 200:
            data = resp.json()
            if "metrics" in data and "live_feed" in data:
                print("✅ PASS | API Endpoint (/api/stats) returned valid JSON data")
                print(f"   -> Active Sidecars: {data['metrics'].get('active_sidecars')}")
                print(f"   -> Global Immunity Score: {data['metrics'].get('global_immunity_score')}")
            else:
                print("❌ FAIL | API returned unexpected JSON structure")
        else:
            print(f"❌ FAIL | API returned {resp.status_code}")
    except Exception as e:
        print(f"❌ FAIL | Could not connect to API: {e}")

if __name__ == "__main__":
    test_dashboard()
