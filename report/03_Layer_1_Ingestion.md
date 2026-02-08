# Layer 1: Ingestion & Telemetry

## 🔍 The Gateway
The first layer of defense is the **Ingestion Gateway**, acting as a smart reverse proxy.

### Technical Implementation
- **Protocol:** HTTP/1.1 & gRPC.
- **Placement:** Sits between the Ingress Controller and the Application Container (localhost loopback).
- **Visibility:** Decrypted traffic (Post-TLS termination).

### Step-by-Step Flow
1.  **Interception:** Captures `Method`, `Headers`, `Path`, `Query Params`, and `Body`.
2.  **Normalization:** Decodes URL encoding, base64 payloads, and standardizes charset.
3.  **Context Extraction:** Identifies the target service ID (e.g., `payment-service`) to apply service-specific policies.

### Performance
- **Overhead:** Negligible (<0.1ms).
- **Tech Stack:** Currently Python (prototype), moving to **Rust** (Pingora/Hyper) for commercial release to handle 100k+ RPS.

**Outcome:** Raw request object is normalized and passed to Layer 2 (Fast Analysis).
