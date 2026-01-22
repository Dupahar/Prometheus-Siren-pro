# Layer 5: Deception (Siren Honeypot)

## 🎭 The Virtual Matrix
Instead of simply dropping malicious packets (which tells the attacker "I found you"), Siren invites them into a high-fidelity simulation.

### 1. Fake Database (SQL)
- **Component:** `FakeSQLDatabase`.
- **Behavior:** Parses raw SQL queries and returns coherent, fake datasets.
- **Example:** 
    - *Attacker:* `SELECT * FROM users`
    - *Siren:* Returns a table of 5 dummy users (John Doe, Jane Smith) with realistic emails.

### 2. Fake File System (Path Traversal)
- **Component:** `FakeFileSystem`.
- **Behavior:** Intercepts path access like `../../etc/passwd`.
- **Response:** Returns a believable Linux `/etc/passwd` file, but with fake hashes.

### Goal
1.  **Stall:** Waste the attacker's time.
2.  **Learn:** Record every keystroke and payload to understand new attack vectors.
3.  **Trace:** Attribution and fingerprinting (IP, User-Agent, Timing).
