import base64
import json
import os
import uvicorn
from fastapi import FastAPI, Body, HTTPException
from pydantic import BaseModel
import jsonpatch

app = FastAPI(title="Prometheus Sidecar Injector")

class AdmissionReview(BaseModel):
    apiVersion: str
    kind: str
    request: dict

@app.post("/mutate")
async def mutate_pod(review: AdmissionReview = Body(...)):
    """
    Mutating Admission Webhook endpoint.
    Receives an AdmissionReview, checks for annotation, returns AdmissionResponse.
    """
    req = review.request
    uid = req.get("uid")
    object_meta = req.get("object", {}).get("metadata", {})
    annotations = object_meta.get("annotations", {})
    
    # Check for annotation
    if annotations.get("prometheus-siren/enabled") != "true":
        return _allow_response(uid)
    
    # Check if already injected (avoid infinite loop)
    # Check init containers or containers for our agent
    spec = req.get("object", {}).get("spec", {})
    containers = spec.get("containers", [])
    if any(c.get("name") == "prometheus-agent" for c in containers):
         return _allow_response(uid)

    # Generate Patch
    logger_msg = f"Injecting sidecar into pod {object_meta.get('name', 'unknown')}"
    print(logger_msg) # Simple logging for now

    patch_operations = [
        {
            "op": "add",
            "path": "/spec/containers/-",
            "value": {
                "name": "prometheus-agent",
                "image": "prometheus-siren-agent:latest", # In prod, use real registry URL
                "imagePullPolicy": "IfNotPresent",
                "ports": [{"containerPort": 8000}],
                "env": [
                    {"name": "BRAIN_URL", "value": "http://prometheus-brain.default.svc.cluster.local:8001"},
                    {"name": "SIREN_URL", "value": "http://prometheus-siren.default.svc.cluster.local:8002"},
                    {"name": "APP_URL", "value": "http://127.0.0.1:5000"} # Localhost loopback
                ],
                "resources": {
                    "limits": {"memory": "128Mi", "cpu": "200m"},
                    "requests": {"memory": "64Mi", "cpu": "100m"}
                }
            }
        }
    ]
    
    patch_bytes = json.dumps(patch_operations).encode("utf-8")
    patch_b64 = base64.b64encode(patch_bytes).decode("utf-8")
    
    return {
        "apiVersion": "admission.k8s.io/v1",
        "kind": "AdmissionReview",
        "response": {
            "uid": uid,
            "allowed": True,
            "patchType": "JSONPatch",
            "patch": patch_b64
        }
    }

def _allow_response(uid):
    return {
        "apiVersion": "admission.k8s.io/v1",
        "kind": "AdmissionReview",
        "response": {
            "uid": uid,
            "allowed": True
        }
    }

if __name__ == "__main__":
    # In K8s, this must run with SSL. 
    # For dev, we might run behind a proxy or use --ssl-keyfile if generated.
    uvicorn.run(app, host="0.0.0.0", port=8443)
