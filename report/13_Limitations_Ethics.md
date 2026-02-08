# Limitations & Ethics

## 🔒 Privacy

While the Global Hive Mind enables collective threat intelligence sharing across deployments, we implement strict data isolation principles:

- **Embedding-Only Sharing:** Only mathematical vector representations are transmitted between deployments—never raw payloads or user data.
- **PII Protection:** Personally Identifiable Information is never extracted, stored, or shared. Attack payloads are processed transiently and only their semantic fingerprints are retained.
- **Data Sovereignty:** Each deployment maintains local control over its `attack_memory` collection. The global blocklist contains only anonymized threat vectors.

## ⚠️ Safety

The autonomous capabilities of Prometheus-Siren are designed with safety guardrails:

- **Human-in-the-Loop Mode:** The Auto-Patcher is configured to operate in "Co-pilot" mode by default for all production systems. Generated patches are submitted as Pull Requests for developer review rather than deployed automatically.
- **Staged Rollout:** WAF rule updates are applied incrementally with automatic rollback triggers if error rates increase.
- **Critical Path Protection:** System-critical endpoints (authentication, payment, admin) require explicit approval before any autonomous changes are applied.

## ⚖️ Bias Mitigation

We acknowledge potential sources of bias and implement active countermeasures:

- **Geographic Bias Risk:** The Brain could theoretically learn to disproportionately flag traffic from specific regions if training data is skewed toward attacks originating from particular geographies.
- **Mitigation Strategy:** We weight semantic intent analysis (0.4) higher than metadata-based signals. Decisions are grounded in payload meaning rather than source IP, user-agent strings, or geographic origin.
- **Continuous Monitoring:** The dashboard tracks detection rates by region to identify and correct emerging bias patterns.

## 🚧 Known Failure Modes

We transparently acknowledge current system limitations:

| Limitation | Impact | Mitigation |
|------------|--------|------------|
| Cold Start Latency | ~400ms for first-time semantic analysis of novel safe payloads | Local caching and pattern pre-warming |
| API Dependency | Reliance on Gemini API and Qdrant Cloud availability | Graceful degradation to local pattern matching |
| Adversarial Prompts | Potential for crafted payloads to confuse LLM reasoning | Multi-layer validation and human review for edge cases |
| Encrypted Payload Blindness | Cannot analyze end-to-end encrypted traffic | Designed for post-TLS-termination deployment |

## 🌐 Societal Responsibility

Prometheus-Siren is designed with societal benefit as a core objective:

- **Democratizing Security:** The zero-touch deployment model enables organizations without dedicated security teams to achieve enterprise-grade protection.
- **Open Source Commitment:** Core Agent and pattern-matching components are planned for open-source release to enable adoption by NGOs, educational institutions, and public sector organizations.
- **Transparency:** All blocking decisions are logged with full reasoning chains, enabling audit and accountability.
