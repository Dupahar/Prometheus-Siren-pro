import sys
import os
import json
import base64
from fastapi.testclient import TestClient

# Ensure we can import from commercial/
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from services.injector_controller import app

client = TestClient(app)

def test_injection():
    print("--- Testing K8s Sidecar Injection ---")
    
    # 1. Simulate K8s AdmissionReview Request
    payload = {
        "apiVersion": "admission.k8s.io/v1",
        "kind": "AdmissionReview",
        "request": {
            "uid": "12345-abcde",
            "object": {
                "metadata": {
                    "name": "my-secure-app",
                    "annotations": {
                        "prometheus-siren/enabled": "true"
                    }
                },
                "spec": {
                    "containers": [
                        {
                            "name": "my-app",
                            "image": "nginx"
                        }
                    ]
                }
            }
        }
    }
    
    resp = client.post("/mutate", json=payload)
    
    if resp.status_code != 200:
        print(f"❌ FAIL | Status Code: {resp.status_code}")
        print(resp.text)
        return

    data = resp.json()
    response_body = data.get("response", {})
    
    # 2. Verify Patch Existence
    if not response_body.get("allowed") or not response_body.get("patch"):
        print("❌ FAIL | No patch returned", data)
        return
        
    # 3. Decode Patch
    patch_b64 = response_body["patch"]
    patch_bytes = base64.b64decode(patch_b64)
    patch_json = json.loads(patch_bytes)
    
    print(f"✅ PASS | Generated Patch: {json.dumps(patch_json, indent=2)}")
    
    # 4. Verify Content
    op = patch_operations = patch_json[0]
    if op["value"]["name"] == "prometheus-agent":
         print("✅ PASS | Sidecar 'prometheus-agent' present in patch")
    else:
         print("❌ FAIL | Incorrect sidecar name")

def test_skip_injection():
    print("\n--- Testing Skip Logic (No Annotation) ---")
    payload = {
        "apiVersion": "admission.k8s.io/v1",
        "kind": "AdmissionReview",
        "request": {
            "uid": "skip-123",
            "object": {
                "metadata": {
                    "name": "plain-app",
                    "annotations": {} # No annotation
                },
                "spec": {"containers": []}
            }
        }
    }
    resp = client.post("/mutate", json=payload)
    data = resp.json()
    
    if data["response"]["allowed"] and "patch" not in data["response"]:
        print("✅ PASS | Skipped injection for unannotated pod")
    else:
        print("❌ FAIL | Attempted to inject unannotated pod", data)

if __name__ == "__main__":
    test_injection()
    test_skip_injection()
