# Layer 3: Deep Analysis (Hybrid Intelligence)

## 🧠 The Hybrid Engine
When a request passes the fast regex filters, it enters the **Deep Analysis** layer. This layer combines Machine Learning with Semantic Memory.

### Component 1: ML Model (Structure Analysis)
- **Model:** XGBoost Classifier.
- **Input:** Token distribution, payload entropy, character frequency.
- **Speed:** ~5ms.
- **Role:** Detects *obfuscated* attacks that regex misses (e.g., encoded shells).

### Component 2: Semantic Memory (Meaning Analysis)
- **Engine:** Qdrant Vector Database + Gemini Embeddings (`text-embedding-004`).
- **Logic:**
    1.  Convert payload to a Vector.
    2.  Search `attack_memory` collection for semantic similarity.
    3.  *Example:* `DROP TABLE` is semantically similar to `DELETE FROM`.
- **Speed:** ~400ms.

### Fusion Scoring
The system calculates a weighted average:
`FinalScore = (PatternScore * 0.3) + (MLScore * 0.3) + (SemanticScore * 0.4)`

**Outcome:** A precise probability score (0.00 to 1.00) representing malicious intent.
