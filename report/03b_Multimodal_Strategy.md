# Multimodal Retrieval Strategy: Text & Code

## 🔄 Cross-Modal Intelligence

Prometheus-Siren implements true multimodal retrieval by operating across two distinct but interconnected embedding spaces. This enables the system to not only detect attacks but correlate them with vulnerable code—a capability that sets it apart from traditional single-modal security tools.

## 📝 Modality 1: Text Embeddings (Attack Payloads)

The primary modality processes unstructured text from HTTP traffic:

- **Data Sources:** Request bodies, query parameters, headers, URL paths
- **Embedding Model:** Gemini `text-embedding-004` (768 dimensions)
- **Collection:** `attack_memory` in Qdrant
- **Use Case:** Semantic similarity search to identify attack intent regardless of syntactic obfuscation

### Example
```
Input: "1' OR '1'='1' --"
Vector: [0.12, -0.45, 0.78, ...]
Matches: SQL injection variants with similar semantic meaning
```

## 💻 Modality 2: Code Embeddings (Vulnerability Context)

The secondary modality processes structured source code:

- **Data Sources:** Python, JavaScript, Java source files from the protected application
- **Processing:** AST (Abstract Syntax Tree) parsing to extract function-level code chunks
- **Embedding Model:** Gemini `text-embedding-004` with code-optimized prompting
- **Collection:** `code_chunks` in Qdrant
- **Use Case:** Identifying vulnerable code patterns and enabling targeted patch generation

### Example
```python
# Vulnerable Code Chunk
def login(user, password):
    query = f"SELECT * FROM users WHERE user='{user}'"
    return db.execute(query)
```
```
Vector: [0.33, -0.21, 0.56, ...]
```

## 🔗 Cross-Modal Correlation

The true power of multimodal retrieval emerges when attacks are correlated with vulnerable code:

```
┌─────────────────────────────────────────────────────────────────┐
│                    MULTIMODAL PIPELINE                          │
├─────────────────────────────────────────────────────────────────┤
│  1. Attack Detected                                             │
│     └─> Payload vectorized in Text Embedding Space              │
│                                                                 │
│  2. Endpoint Mapping                                            │
│     └─> HTTP path mapped to application route                   │
│                                                                 │
│  3. Code Retrieval                                              │
│     └─> Semantic search in Code Embedding Space                 │
│     └─> Retrieve TOP-K similar code chunks                      │
│                                                                 │
│  4. Cross-Modal Join                                            │
│     └─> Attack payload + Vulnerable code = Context for GenAI    │
│                                                                 │
│  5. Patch Generation                                            │
│     └─> Gemini Pro generates targeted remediation               │
└─────────────────────────────────────────────────────────────────┘
```

## 📊 Why This Matters

| Capability | Single-Modal (Text Only) | Multimodal (Text + Code) |
|------------|--------------------------|--------------------------|
| Attack Detection | ✅ Yes | ✅ Yes |
| Semantic Matching | ✅ Yes | ✅ Yes |
| Root Cause Identification | ❌ No | ✅ Yes |
| Targeted Patch Generation | ❌ No | ✅ Yes |
| Vulnerability Elimination | ❌ No | ✅ Yes |

By cross-referencing unstructured attack text with structured vulnerability code, Prometheus-Siren achieves what traditional WAFs cannot: **permanent remediation** rather than temporary blocking.
