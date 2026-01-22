import sys
import os
import asyncio
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

# Ensure we can import from commercial/
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from services.brain_service import app as brain_app
from services.siren_service import app as siren_app
from services.agent_service import app as agent_app

def print_result(name, passed, details=""):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} | {name} {details}")

def test_siren():
    print("\n--- Testing Siren (Honeypot) ---")
    client = TestClient(siren_app)
    
    # Test 1: Fake SQL
    resp = client.post("/login", content="SELECT * FROM users")
    if resp.status_code == 200 and "admin" in resp.json().get("data", [{}])[0].get("user", ""):
        print_result("Fake SQL Response", True)
    else:
        print_result("Fake SQL Response", False, f"Got {resp.text}")

    # Test 2: Generic
    resp = client.get("/dashboard")
    if resp.json().get("message") == "Login failed":
        print_result("Generic Deception", True)
    else:
        print_result("Generic Deception", False)

def test_brain():
    print("\n--- Testing Brain (Control Plane) ---")
    client = TestClient(brain_app)
    
    # Test Telemetry
    payload = {"payload": "SELECT *", "source_ip": "1.2.3.4", "score": 0.9}
    
    # Mock Qdrant to avoid needing actual DB connection
    with patch("services.brain_service.qdrant") as mock_qdrant:
        resp = client.post("/telemetry", json=payload)
        if resp.status_code == 200 and resp.json().get("status") == "recorded":
            print_result("Telemetry Ingestion", True)
        else:
            print_result("Telemetry Ingestion", False, f"Got {resp.text}")

def test_agent():
    print("\n--- Testing Agent (Sidecar) ---")
    client = TestClient(agent_app)

    # Test 1: Clean Traffic (Should proxy)
    # Mock httpx to simulate successful upstream response
    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value.status_code = 200
        mock_req.return_value.content = b"Welcome to App"
        mock_req.return_value.headers = {}
        
        resp = client.get("/home")
        # Agent logic: threat score 0.0 -> Proxy
        if resp.status_code == 200 and resp.content == b"Welcome to App":
            print_result("Clean Traffic Proxy", True)
        else:
            print_result("Clean Traffic Proxy", False, f"Got {resp.status_code}")

    # Test 2: Malicious Traffic (Should block/tunnel)
    # Mock threat scorer to return High score object
    from unittest.mock import Mock
    mock_assessment = Mock(score=1.0)
    with patch("services.agent_service.threat_scorer.score", return_value=mock_assessment):
        with patch("services.agent_service.tunnel_to_siren", new_callable=AsyncMock) as mock_tunnel:
            # We construct a fake response for the tunnel
            from fastapi.responses import Response
            mock_tunnel.return_value = Response(content="Fake Data", status_code=200)

            resp = client.post("/login", content="' OR 1=1")
            
            if mock_tunnel.called:
                print_result("Attack Interception", True, "Redirected to Siren")
            else:
                print_result("Attack Interception", False, "Did not redirect")

if __name__ == "__main__":
    test_siren()
    test_brain()
    test_agent()
