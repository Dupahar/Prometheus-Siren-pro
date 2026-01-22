# Global Hive Mind: Shared Immunity

## 🌐 The Network Effect
Security has traditionally been an isolated burden. Prometheus-Siren transforms it into a collective defense network.

### How it Works
1.  **Patient Zero:** Customer A gets hit by a novel Zero-Day attack.
2.  **Local Learning:** Customer A's Sidecar detects anomaly -> Brain confirms attack.
3.  **Vectorization:** The attack payload is converted into a mathematical vector (e.g., `[0.12, -0.98, ...]` by Gemini embeddings).
4.  **Global Sync:**
    - The vector is pushed to the **Global Blocklist** collection in Qdrant Cloud.
    - **Privacy:** Only the *vector* is shared, not the raw data (PII safe).
5.  **Herd Immunity:** 
    - Customer B's Sidecar (in a different country) queries Qdrant.
    - It sees the new vector matches an incoming request.
    - **Block:** The attack is neutralized before it even touches Customer B's app.

### Benefit
- **Zero-Latency Updates:** No need to wait for vendor signature updates.
- **Collective Intelligence:** The system gets smarter with every single failed attack attempt globally.
