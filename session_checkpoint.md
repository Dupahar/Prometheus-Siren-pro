# Project Jirachi: Session Checkpoint

**Date:** 25 January 2026
**State:** DEMO READY / STABLE

## 🏁 System Status
The "Neuro-Symbolic Defense System" is fully operational.

| Component | Port | Status | PID (Last Known) | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Brain** (Python) | 8000 | ✅ Online | ~17132 | `src/services/gemini_general.py` |
| **Shield** (Rust) | 6161 | ✅ Online | ~49928 | `src/jirachi-proxy` (Axum) |
| **Dashboard** | 8501 | ✅ Online | Streamlit | `dashboard.py` |

## 📂 Key Artifacts
*   **Demo Guide:** [walkthrough.md](file:///c:/Users/mahaj/Downloads/Jirachi/walkthrough.md) - **START HERE**
*   **Task Tracker:** [task.md](file:///c:/Users/mahaj/.gemini/antigravity/brain/1f95e92f-db3b-496b-a8c6-6ba1c5313043/task.md) - All phases complete.
*   **Engineering Log:** [Jirachi_Engineering_Log.md](file:///c:/Users/mahaj/Downloads/Jirachi/report/Jirachi_Engineering_Log.md) - Architecture decisions.
*   **Mythical Upgrade Report:** [mythical_upgrade_report.md](file:///c:/Users/mahaj/Downloads/Jirachi/report/mythical_upgrade_report.md) - **NEW** (Federated, eBPF, Verification)
*   **Roadmap:** [future_roadmap.md](file:///c:/Users/mahaj/Downloads/Jirachi/report/future_roadmap.md)
*   **Evaluation:** [project_evaluation.md](file:///c:/Users/mahaj/Downloads/Jirachi/report/project_evaluation.md)

## 🛠️ Quick Commands

**Restart Brain:**
```powershell
python -m src.services.brain_server
```

**Restart Body:**
```powershell
cd src/jirachi-proxy
cargo run
```

**Restart Dashboard:**
```powershell
streamlit run dashboard.py
```

## ⚠️ Known Quirks
1.  **Gemini Model:** Hardcoded to `gemini-1.5-flash` for API compatibility.
2.  **Logging:** Uses absolute paths to ensure `mission_log.jsonl` is written correctly.
3.  **Dashboard:** Requires auto-refresh (sidebar) to see live updates.
