# Architecture Overview: Agent vs. Brain

To achieve millisecond-latency enforcement with deep-learning intelligence, we decoupled the system into two distinct planes.

## 1. The Agent (The Body)
* **Design Philosophy:** "Dumb but Fast."
* **Location:** Runs as a **Sidecar container** inside every application Pod.
* **Function:** 
    - Reverse Proxy (Intercepts traffic).
    - Local Pattern Matching (Regex).
    - Lightweight ML Scoring (probabilistic).
    - **Action:** Block, Allow, or Redirect to Honeypot.
* **Latency Target:** < 2ms overhead.

## 2. The Brain (The Mind)
* **Design Philosophy:** "Slow but Smart."
* **Location:** Centralized Control Plane (Shared Cluster Service or SaaS).
* **Function:**
    - **Vectors:** Hosts Qdrant DB for semantic memory.
    - **Intelligence:** Runs DistilBERT models and connects to Gemini API.
    - **Evolution:** Generates patches and updates the global threat vector database.
* **Responsibility:** Pushes updates to all Agents.

## 🔄 The Feedback Loop
1.  **Agent** sees suspicious traffic -> Asks Brain (Async).
2.  **Brain** confirms attack -> Updates Memory.
3.  **Brain** pushes immunity (Vector/Rule) -> **All Agents**.
4.  **Result:** Herd Immunity achieved in seconds.
