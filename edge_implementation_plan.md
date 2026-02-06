# 🧠 Implementation Plan: Edge-Native Intelligence (Local SLMs)

**Goal:** Reduce system latency from ~500ms to <10ms and remove API cost dependency by running a specialized Small Language Model (SLM) directly inside the Rust proxy.

## User Review Required
> [!IMPORTANT]
> **Performance vs Resource Tradeoff**
> Running a local model (even a small one like Phi-3-mini) requires ~2GB RAM. Ensure the deployment environment supports this.
> We will stick to `cpu` inference first to avoid complex CUDA/Metal constraints on the user's Windows machine, though `candle` supports generic hardware acceleration.

## Proposed Changes

### 1. Prototype Phase (Proof of Concept)
Create a standalone Rust binary to verify `candle` can load a quantized model and run inference on Windows.

#### [NEW] [candle_poc.rs](file:///c:/Users/mahaj/Downloads/Jirachi/src/jirachi-proxy/examples/candle_poc.rs)
- **Dependencies:** Add `candle-core`, `candle-nn`, `candle-transformers`, `tokenizers`.
- **Model:** Download `Phi-3-mini-4k-instruct-q4.gguf` (approx 2.4GB) from Hugging Face.
- **Logic:**
    1.  Load the GGUF model.
    2.  Take a sample HTTP payload string.
    3.  Generate a confidence score (Safe vs Malicious).

### 2. Integration Phase (The Iron Shield Upgrade)
Embed the inference engine into the `jirachi-proxy` Axum service.

#### [MODIFY] [Cargo.toml](file:///c:/Users/mahaj/Downloads/Jirachi/src/jirachi-proxy/Cargo.toml)
- Add `candle` dependencies.
- Add `hf-hub` for model downloading.

#### [NEW] [inference.rs](file:///c:/Users/mahaj/Downloads/Jirachi/src/jirachi-proxy/src/inference.rs)
- **Struct:** `LocalBrain` (Stateful, holds the model in memory).
- **Method:** `analyze(payload: &str) -> RiskScore`.
- **Prompt Engineering:**
    ```text
    Examine this HTTP payload for security threats (SQLi, XSS, RCE).
    Payload: "{payload}"
    Reply only with JSON: {"risk_score": 0.0 to 1.0, "reason": "brief explanation"}
    ```

#### [MODIFY] [main.rs](file:///c:/Users/mahaj/Downloads/Jirachi/src/jirachi-proxy/src/main.rs)
- Initialize `LocalBrain` at startup (lazy load model).
- In the `middleware` / handler:
    1.  Run `LocalBrain::analyze`.
    2.  If `score > 0.8` -> Block/Trap.
    3.  If `score < 0.2` -> Allow.
    4.  If `0.2 < score < 0.8` (Ambiguous) -> **Escalate to Gemini API** (The General).

## Verification Plan

### Automated Tests
- **Unit Test:** Verify `LocalBrain` loads the model and returns a valid JSON structure.
- **Latency Test:** Measure time taken for 100 requests. Target: `< 50ms` on CPU.

### Manual Verification
1.  **Start System:** `cargo run` (Wait for model download).
2.  **Attack:** Send `curl -d "SELECT * FROM users" localhost:6161/login`.
3.  **Result:**
    - Proxy should block it.
    - Console should show "Blocked by Edge Logic" (Not "Escalating to Gemini").
4.  **Edge Case:** Send a complex, ambiguous payload and verify it *does* fall back to Gemini.
