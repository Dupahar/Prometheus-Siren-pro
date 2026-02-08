# Project Jirachi: Implementation Plan

## 🥅 Goal
Transition **Prometheus-Siren** from a Python-based prototype into **Project Jirachi**: a deterministic, verified, and distributed cyber-immune system where **Google Gemini** acts as the central "Main Lead" API Controller.

## 🏗️ Architectural Pillars
1.  **The General (Control Plane):** Google Gemini API acting as the "Brain" and "Commander".
2.  **The Iron Shield (Data Plane):** Rust + Axum Agents (High-Performance Async Proxy).
3.  **The Siren (Deception Layer):** Axum Honeypot Route (`/trap`).
4.  **The Watchtower (Visibility):** Streamlit "Hive Mind" Dashboard.

## 📋 Execution Phases

### Phase 1: The "Gemini General" Interface
- [x] **Service Definition:** `src/services/gemini_general.py` (Completed).
- [x] **Capabilities:** Judge, Engineer, Diplomat flows implemented.

### Phase 2: The Rust Data Plane (The Iron Shield)
- [x] **Axum Proxy:** `src/jirachi-proxy` compiled and verified.
- [x] **Escalation Protocol:** Successfully consulting Gemini.

### Phase 3: Integration Verification
- [x] **Live Fire Test:** `curl /admin` -> 403 Forbidden.

### Phase 4: The Siren Deception Layer
- [x] **Honeypot Route:** `/trap` implemented.
- [x] **Deception Logic:** `DECEIVE` command redirects attackers.
- [x] **Verification:** `curl /login?q=siren_test` -> Captured.

### Phase 5: The "Global Hive Mind" Dashboard
**Goal:** Visualize the Commander's decisions in real-time.
- [ ] **Logging:** Update `gemini_general.py` to write `mission_log.jsonl`.
- [ ] **Visualize:** Create `dashboard.py` using Streamlit.
- [ ] **Demo:** Run the full stack (Brain + Body + UI) and attack it.
