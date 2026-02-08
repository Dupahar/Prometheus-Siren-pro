# Search, Memory & Recommendation Logic

## 🔍 How Qdrant Powers Prometheus-Siren

Qdrant serves as the core vector search engine enabling three critical capabilities: **Semantic Search**, **Long-Term Memory**, and **Contextual Recommendations**.

---

## 1. Semantic Search (Attack Pattern Matching)

### The Problem
Traditional WAFs use exact string matching—easily bypassed by encoding, obfuscation, or novel payloads.

### The Solution
Prometheus-Siren converts attack payloads into semantic vectors and performs similarity search:

```python
# Incoming payload converted to vector
payload_vector = gemini.embed("1' UNION SELECT * FROM passwords --")

# Qdrant semantic search
results = qdrant.search(
    collection_name="attack_memory",
    query_vector=payload_vector,
    limit=5,
    score_threshold=0.75
)
```

### Why This Matters
- `DROP TABLE` matches semantically with `DELETE FROM`, `TRUNCATE`, `REMOVE ALL`
- Obfuscated payloads like `%27%20OR%201=1` match their decoded intent
- Novel zero-day variants match known attack families

---

## 2. Long-Term Memory (Evolving Knowledge)

### Memory Architecture
| Collection | Purpose | Update Frequency |
|------------|---------|------------------|
| `attack_memory` | Confirmed malicious payload vectors | On every confirmed attack |
| `code_chunks` | Protected application source code | On codebase change |
| `global_blocklist` | Shared threat intelligence | Real-time (Hive Mind) |

### Memory Beyond a Single Prompt
Unlike stateless systems, Prometheus-Siren maintains **persistent, evolving memory**:

```
┌──────────────────────────────────────────────────────────────┐
│                    MEMORY LIFECYCLE                          │
├──────────────────────────────────────────────────────────────┤
│  1. Ingestion                                                │
│     └─> New attack detected → Vectorized → Stored            │
│                                                              │
│  2. Reinforcement                                            │
│     └─> Same attack seen again → Metadata updated            │
│     └─> "seen_count" incremented, "last_seen" refreshed      │
│                                                              │
│  3. Decay (Planned)                                          │
│     └─> Stale patterns with low hit rates → Lower priority   │
│                                                              │
│  4. Global Sync                                              │
│     └─> High-confidence vectors → Shared to Hive Mind        │
└──────────────────────────────────────────────────────────────┘
```

### Payload Metadata Design
```json
{
  "attack_type": "sql_injection",
  "severity": 0.95,
  "first_seen": "2026-01-15T08:30:00Z",
  "last_seen": "2026-01-22T16:00:00Z",
  "seen_count": 47,
  "source_deployment": "customer_a",
  "target_endpoint": "/api/login"
}
```

---

## 3. Contextual Recommendations (Patch Generation)

### Decision Support Flow
Based on attack context, the system recommends specific remediation:

```
Attack Payload: "1' OR '1'='1' --"
     │
     ▼
┌─────────────────────────────┐
│ Qdrant Code Search          │
│ Query: Attack vector        │
│ Result: Top-3 similar code  │
└─────────────────────────────┘
     │
     ▼
┌─────────────────────────────┐
│ Vulnerable Code Retrieved:  │
│ query = f"SELECT * FROM     │
│   users WHERE id='{input}'" │
└─────────────────────────────┘
     │
     ▼
┌─────────────────────────────┐
│ GenAI Recommendation:       │
│ "Use parameterized queries" │
│ + Generated secure patch    │
└─────────────────────────────┘
```

### Recommendation Types
| Context | Recommendation |
|---------|----------------|
| SQL Injection detected | "Migrate to parameterized queries using `cursor.execute(query, params)`" |
| XSS payload detected | "Implement output encoding using `html.escape()` or template auto-escaping" |
| Path Traversal detected | "Validate paths using `os.path.realpath()` and whitelist checking" |

---

## 📊 Qdrant Integration Summary

| Capability | Qdrant Feature Used | Outcome |
|------------|---------------------|---------|
| **Search** | Dense vector similarity | Semantic attack detection |
| **Memory** | Persistent collections + metadata | Evolving threat knowledge |
| **Recommendation** | Cross-collection retrieval | Targeted patch suggestions |
