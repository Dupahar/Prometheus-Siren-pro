# Project Jirachi: Demo Walkthrough

**The "Main Lead" Neuro-Symbolic Defense System**

This guide explains how to start the 3 components of the system and demonstrate the attacks.

## 🏗️ 1. Start the System (3 Terminals)

### Terminal 1: The Commander (Brain)
Acts as the decision engine.
```powershell
python -m src.services.brain_server
```
*Status:* Running on http://127.0.0.1:8000

### Terminal 2: The Agent (Body)
High-performance Rust proxy.
```powershell
cd src/jirachi-proxy
cargo run
```
*Status:* Running on http://127.0.0.1:6161

### Terminal 3: The Hive Mind (Dashboard)
Real-time visualization.
```powershell
streamlit run dashboard.py
```
*Status:* Open browser to http://localhost:8501

---

## ⚔️ 2. Execute the Attacks

Open a 4th terminal to simulate the attacker.

### Test A: The Block (SQL Injection)
Gemini detects the threat and orders a BLOCK.
```powershell
curl -v http://localhost:6161/admin?query=UNION
```
*   **Result:** `403 Forbidden`
*   **Dashboard:** Shows a **RED** "BLOCK" event.

### Test B: The Siren Trap (Deception)
Gemini detects a specific campaign (`siren_test`) and orders a DECEIVE.
```powershell
curl -v -L http://localhost:6161/login?q=siren_test
```
*   **Result:** `307 Redirect` -> JSON Response `{"error": "Fatal DB Error"}`
*   **Dashboard:** Shows an **ORANGE** "DECEIVE" event.

### Test C: Safe Traffic
Normal traffic flows through.
```powershell
curl -v http://localhost:6161/hello
```
*   **Result:** `502 Bad Gateway` (Upstream app not running) or `200 OK` (if upstream is up).
*   **Dashboard:** Shows a **GREEN** "ALLOW" event (if logged).

---

## 📸 3. The Evidence
1.  **Engineering Log:** `report/Jirachi_Engineering_Log.md`
2.  **Dashboard:** Live metrics proving "Gemini Active".
3.  **Logs:** `mission_log.jsonl` contains the JSON proof of every decision.

## 🖼️ Dashboard Proof
![Jirachi Global Hive Mind](C:/Users/mahaj/.gemini/antigravity/brain/1f95e92f-db3b-496b-a8c6-6ba1c5313043/uploaded_media_1769284732112.png)

