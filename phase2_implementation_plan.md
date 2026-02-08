# Implementation Plan - Phase 2: The Injector

## 🥅 Goal
Implement a **Mutating Admission Webhook** in Kubernetes that automatically injects the `Prometheus-Agent` sidecar into any Pod annotated with `prometheus-siren/enabled: "true"`.

## 🏗️ Technical Architecture
### 1. The Controller Logic
- **Language:** Python (FastAPI).
- **Endpoint:** POST `/mutate`.
- **Input:** `AdmissionReview` JSON (from K8s API Server).
- **Logic:**
    1.  Check if `metadata.annotations` contains `prometheus-siren/enabled: "true"`.
    2.  If yes, generate a `JSONPatch`.
- **Output:** `AdmissionResponse` with `patch` (base64 encoded).

### 2. The Patch Operation
The controller will inject:
1.  **Container:** `prometheus-siren-agent:latest`.
2.  **Env Vars:** Links to `BRAIN_URL` and `SIREN_URL`.
3.  **Ports:** Expose `8000` (Proxy Port).

## 📋 Implementation Steps

### 1. Python Controller (`injector_controller.py`)
- Define the `AdmissionReview` Pydantic models.
- Implement the JSONPatch generation logic.
- Handle SSL/TLS (Required by K8s Webhooks) - *For local dev, we will assume a reverse proxy or self-signed cert setup.*

### 2. Kubernetes Manifests (`k8s/`)
- `injector-deployment.yaml`: Runs the controller itself.
- `injector-service.yaml`: Exposes the controller in cluster.
- `mutating-webhook-config.yaml`: Tells K8s API server to send pod creation requests to us.

### 3. Verification
- Create `test-pod.yaml` with the annotation.
- Mock the K8s API call to the controller to verify it returns the correct JSONPatch.

---
> [!NOTE]
> This completes the "Zero-Touch" promise. Developers just add one line of YAML, and security is auto-injected.
