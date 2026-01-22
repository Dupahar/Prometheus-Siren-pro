# Layer 2: Fast Analysis (Pattern Matching)

## ⚡ Speed First
Before invoking heavy AI models, the system runs a **Fast Path** analysis to instantly catch obvious attacks.

### The ThreatScorer Component
- **Mechanism:** High-performance Regex Engine.
- **Pattern Library:** Contains signatures for common injection patterns (e.g., `' OR 1=1`, `<script>`, `../`).
- **Latency:** **< 1ms** (Microsecond scale).

### Logic Flow
1.  **Check:** Payload matches known static signature?
2.  **Yes:**
    - Assign `ThreatScore = 1.0` (Critical).
    - **Action:** Short-circuit to Layer 4 (Decision) -> Honeypot.
3.  **No:**
    - Pass to Layer 3 (Deep Analysis).

**Status:** This layer handles ~80% of automated bot traffic, preserving resources for complex threats.
