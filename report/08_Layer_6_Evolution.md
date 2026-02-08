# Layer 6: Evolution (Auto-Patching)

## 🧬 Self-Healing Mechanism
The ultimate goal of Prometheus is not just to block, but to **fix** the underlying vulnerability so it can never be exploited again.

### The Patching Workflow
1.  **Attack Correlation:**
    - The Brain identifies which code endpoint was targeted (e.g., `/login`).
    - It maps the HTTP request to the specific function in the source code (AST Mapping).

2.  **Root Cause Analysis:**
    - Extracts the vulnerable code snippet (e.g., raw SQL string concatenation).
    - Pairs it with the successful attack payload.

3.  **GenAI Remediation:**
    - **Prompt:** "Fix this SQL injection vulnerability in Python using parameterized queries."
    - **Model:** Gemini Pro 1.5.
    - **Output:** Secure code patch.

4.  **Deployment:**
    - **Mode A (Autopilot):** Hot-patches the running WAF rule to strictly enforce the new schema.
    - **Mode B (Co-pilot):** Opens a Pull Request (GitHub/GitLab) for developer review.

**Result:** The system structurally eliminates the vulnerability class.
