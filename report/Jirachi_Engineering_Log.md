# Project Jirachi: Engineering Evolution Log

**Date:** 25 January 2026
**Status:** Implementation Phase 4 Complete (Siren Deception Live)

---

## 1. Executive Summary
This document records the architectural transformation of **Prometheus-Siren** into **Project Jirachi**. The core objective was to elevate **Google Gemini** from a passive chatbot to the **"Main Lead" API Controller** (The Commander) that drives a high-performance, deterministic **Rust Data Plane**.

## 2. Architectural Shifts

### A. The "Gemini General" (Control Plane)
*   **Previous State:** Logic scattered across Python scripts; Gemini called only for ad-hoc analysis.
*   **New State:** A centralized **Service** (`src/services/gemini_general.py`) that acts as the "Brain".
*   **Key Innovation:** The Service enforces a strict **JSON Contract** for all decisions. The General does not "chat"; it issues **Commands** (`BLOCK`, `ALLOW`, `DECEIVE`).
*   **Capabilities Implemented:**
    1.  **The Judge:** Analyzes HTTP traces and issues `THREAT_JUDGMENT` artifacts.
    2.  **The Engineer:** precise auto-patching with `PATCH_ARTIFACT` outputs.
    3.  **The Diplomat:** Summarizes threats for the `Global Hive Mind`.

### B. The "Iron Shield" (Data Plane)
*   **Previous State:** Python `FastAPI` gateway. Vulnerable to GIL locking.
*   **New State:** **Rust Reverse Proxy** (`src/jirachi-proxy`) using **Axum**.
*   **Key Innovation:** Asynchronous, memory-safe traffic interception. The proxy is "dumb" — it makes no strategic decisions. It strictly **Consults the General** for any traffic tagged as "Suspicious".

---

## 3. Implementation Details

### Step 1: Defining the Contract
We established a shared language between Python (Brain) and Rust (Body) using formal JSON Schemas (`src/common/schemas.py`).

### Step 2: The Rust Pivot (Pingora → Axum)
*   **Initial Plan:** Use Cloudflare's **Pingora**.
*   **Challenge:** Build failures on Windows (C++ dependencies).
*   **The Switch:** Pivoted to **Axum** (Pure Rust).
*   **Result:** Successful compilation and deployment.

### Step 3: Siren Deception Layer (Phase 4)
We implemented a dynamic "Trap Route" in the Axum proxy.
*   **Trigger:** When the Brain issues `DECEIVE` (tested with keyword `siren_test`).
*   **Action:** The Rust Agent intercepts the request and issues a `307 Temporary Redirect` to `/trap`.
*   **Trap:** The `/trap` endpoint serves a fake JSON error (`Fatal DB Error`) to confuse the attacker while logging their headers.

### Step 4: Verification Results ("Live Fire")
1.  **Block Test:** `curl /admin?query=UNION` -> **403 Forbidden**. (Success)
2.  **Siren Test:** `curl -L /login?q=siren_test` -> **Redirect to /trap**. (Success)
3.  **Safe Test:** `curl /hello` -> **502 Bad Gateway** (Proxy Success).

---

## 4. Current System Status

| Component | Technology | Status | Role |
| :--- | :--- | :--- | :--- |
| **Commander** | Python / Gemini 1.5 Flash | ✅ **Live** | Analyzes intent, issues JSON commands (Block/Deceive). |
| **Agent** | Rust / Axum | ✅ **Live** | Intercepts traffic, enforces Commander's will. |
| **Siren** | Rust / Axum Trap | ✅ **Live** | Honeypot endpoint for creating "fog of war". |

## 5. Next Steps
1.  **Federation:** Connect to other nodes (Flower Client).
2.  **Dashboard:** Visualize the "Trapped" logs.
