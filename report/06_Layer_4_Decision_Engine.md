# Layer 4: The Decision Engine

## 🛡️ Policy Enforcement
Based on the `ThreatScore` calculated in Layer 3, the Decision Engine applies dynamic security policies.

### Thresholds logic

| Score Range | Classification | Action | Explanation |
| :--- | :--- | :--- | :--- |
| **0.00 - 0.49** | **Safe** | `ALLOW` | Normal traffic. Passes to backend application. |
| **0.50 - 0.79** | **Suspicious** | `CHALLENGE` | (Future) Rate limit, CAPTCHA, or 2FA challenge. |
| **0.80 - 1.00** | **Attack** | `HONEYPOT` | Divert to Siren Deception Environment. |

### Routing Mechanism
- **Allow:** The reverse proxy forwards the packet to `localhost:APP_PORT`.
- **Block/Honeypot:** The proxy **hijacks** the connection and internally routes it to the `Siren` module (Layer 5) without the attacker knowing.

**Outcome:** Legit users see the app; Attackers see a fake reality.
