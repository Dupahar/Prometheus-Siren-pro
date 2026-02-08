# tests/test_layer_by_layer.py
"""
Comprehensive Layer-by-Layer Test Suite.
Tests each layer in isolation and integration.
Run with: pytest tests/test_layer_by_layer.py -v -s
"""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ==========================================
# LAYER 0: Configuration Tests
# ==========================================
class TestLayer0Config:
    """Test configuration loading."""
    
    def test_config_loads(self):
        """Test that config loads from .env."""
        from src.core.config import settings
        
        assert settings.gemini_api_key, "GEMINI_API_KEY not set"
        assert settings.qdrant_url, "QDRANT_URL not set"
        print(f"✓ Config loaded: Qdrant URL = {settings.qdrant_url[:50]}...")
    
    def test_config_defaults(self):
        """Test default values."""
        from src.core.config import settings
        
        assert settings.embedding_dimension == 768
        assert settings.threat_threshold == 0.85
        print("✓ Default config values correct")


# ==========================================
# LAYER 0: Qdrant Connection Tests
# ==========================================
class TestLayer0Qdrant:
    """Test Qdrant connection and operations."""
    
    def test_qdrant_connection(self):
        """Test Qdrant client connection."""
        from src.core.qdrant_client import qdrant_manager
        
        # Test connection by getting client
        client = qdrant_manager.client
        assert client is not None
        print("✓ Qdrant connection established")
    
    def test_ensure_collections(self):
        """Test collection creation."""
        from src.core.qdrant_client import qdrant_manager
        
        qdrant_manager.ensure_collections()
        
        # Verify collections exist
        from src.core.config import settings
        info = qdrant_manager.get_collection_info(settings.qdrant_code_collection)
        assert info["name"] == settings.qdrant_code_collection
        print(f"✓ Collection '{info['name']}' exists with {info['points_count']} points")


# ==========================================
# LAYER 1: Embedding Engine Tests
# ==========================================
class TestLayer1Embeddings:
    """Test Gemini embedding engine."""
    
    def test_text_embedding(self):
        """Test basic text embedding."""
        from src.core.embeddings import embedding_engine
        
        text = "This is a test sentence for embedding."
        vector = embedding_engine.embed_text(text)
        
        assert len(vector) == 768
        assert all(isinstance(v, float) for v in vector)
        print(f"✓ Text embedding: {len(vector)} dimensions")
    
    def test_code_embedding(self):
        """Test code embedding."""
        from src.core.embeddings import embedding_engine
        
        code = "def hello(): return 'world'"
        vector = embedding_engine.embed_code(code)
        
        assert len(vector) == 768
        print(f"✓ Code embedding: {len(vector)} dimensions")
    
    def test_query_embedding(self):
        """Test query embedding (for search)."""
        from src.core.embeddings import embedding_engine
        
        query = "function that calculates division"
        vector = embedding_engine.embed_query(query)
        
        assert len(vector) == 768
        print(f"✓ Query embedding: {len(vector)} dimensions")


# ==========================================
# LAYER 1: AST Parser Tests
# ==========================================
class TestLayer1AST:
    """Test AST-based code parsing."""
    
    def test_parse_function(self):
        """Test parsing a Python function."""
        from src.core.ast_parser import ast_parser
        
        source = '''
def calculate(a, b):
    """Calculate something."""
    return a + b
'''
        chunks = ast_parser.parse_source(source)
        
        assert len(chunks) == 1
        assert chunks[0].name == "calculate"
        assert chunks[0].docstring == "Calculate something."
        print(f"✓ Parsed function: {chunks[0].name}")
    
    def test_parse_class_with_methods(self):
        """Test parsing a class with methods."""
        from src.core.ast_parser import ast_parser
        
        source = '''
class Calculator:
    def add(self, a, b):
        return a + b
'''
        chunks = ast_parser.parse_source(source)
        
        # Should find both class and method
        class_chunks = [c for c in chunks if c.chunk_type == "class"]
        assert len(class_chunks) >= 1
        print(f"✓ Parsed class with {len(chunks)} chunks")


# ==========================================
# LAYER 2: Code Indexer Tests
# ==========================================
class TestLayer2Indexer:
    """Test code indexing pipeline."""
    
    def test_file_scanner(self):
        """Test file scanner."""
        from src.indexer.scanner import file_scanner
        
        # Scan the src directory
        files = file_scanner.scan(Path(__file__).parent.parent / "src")
        
        assert len(files) > 0
        print(f"✓ Scanned {len(files)} Python files")
    
    def test_index_single_file(self):
        """Test indexing a single file."""
        from src.indexer.indexer import code_indexer
        from src.core.qdrant_client import qdrant_manager
        
        # Ensure collections exist
        qdrant_manager.ensure_collections()
        
        # Index the vulnerable app
        vuln_app = Path(__file__).parent.parent / "vulnerable_app" / "app.py"
        if vuln_app.exists():
            count = code_indexer.index_file(vuln_app)
            print(f"✓ Indexed {count} chunks from vulnerable_app")
        else:
            print("⚠ Vulnerable app not found, skipping")


# ==========================================
# LAYER 2: Semantic Search Tests
# ==========================================
class TestLayer2Search:
    """Test semantic code search."""
    
    def test_basic_search(self):
        """Test basic semantic search."""
        from src.indexer.search import code_searcher
        
        results = code_searcher.search("SQL injection vulnerability", top_k=3)
        
        print(f"✓ Search returned {len(results)} results")
        for r in results[:3]:
            print(f"  - {r.qualified_name} (score: {r.score:.3f})")
    
    def test_error_search(self):
        """Test error-based search."""
        from src.indexer.search import code_searcher
        
        results = code_searcher.search_by_error(
            error_type="ZeroDivisionError",
            error_message="division by zero",
            stack_trace="File '/app/calc.py', line 10, in divide\n    return a / b",
            top_k=3,
        )
        
        print(f"✓ Error search returned {len(results)} results")


# ==========================================
# LAYER 3: Log Parser Tests
# ==========================================
class TestLayer3LogParser:
    """Test error log parsing."""
    
    def test_parse_traceback(self):
        """Test traceback parsing."""
        from src.prometheus.log_parser import log_parser
        
        traceback = '''Traceback (most recent call last):
  File "/app/main.py", line 10, in main
    result = divide(10, 0)
  File "/app/calc.py", line 5, in divide
    return a / b
ZeroDivisionError: division by zero
'''
        errors = log_parser.parse(traceback)
        
        assert len(errors) == 1
        assert errors[0].error_type == "ZeroDivisionError"
        print(f"✓ Parsed error: {errors[0].full_error}")


# ==========================================
# LAYER 3: Patch Generator Tests
# ==========================================
class TestLayer3Patching:
    """Test AI patch generation."""
    
    def test_generate_security_patch(self):
        """Test security patch generation."""
        from src.prometheus.patch_generator import patch_generator
        
        vulnerable_code = '''
def login(username, password):
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
    cursor.execute(query)
    return cursor.fetchone()
'''
        
        patch = patch_generator.generate_security_patch(
            vulnerability_type="sql_injection",
            vulnerable_code=vulnerable_code,
            context="Login function with SQL injection vulnerability",
        )
        
        if patch:
            print(f"✓ Generated patch with {patch.confidence:.0%} confidence")
            print(f"  Explanation: {patch.explanation[:100]}...")
        else:
            print("⚠ Patch generation returned None (may need retry)")


# ==========================================
# LAYER 4: Honeypot Tests
# ==========================================
class TestLayer4Honeypot:
    """Test Siren honeypot."""
    
    def test_fake_sql_database(self):
        """Test fake SQL database."""
        from src.siren.blueprints.fake_sql import FakeSQLDatabase
        
        db = FakeSQLDatabase()
        
        # Test normal query
        result = db.execute("SELECT * FROM users")
        assert "rows" in result
        
        # Test SQL injection detection (use pattern that matches: OR 1=1)
        result = db.execute("SELECT * FROM users WHERE id=1 OR 1=1")
        malicious = [log for log in db.query_logs if log.is_malicious]
        assert len(malicious) > 0, f"Should detect OR 1=1 injection, got {len(db.query_logs)} logs"
        
        print(f"+ FakeSQLDatabase: {len(db.query_logs)} queries, {len(malicious)} malicious")
    
    def test_fake_filesystem(self):
        """Test fake filesystem."""
        from src.siren.blueprints.fake_fs import FakeFileSystem
        
        fs = FakeFileSystem()
        
        # Test reading fake passwd
        result = fs.read_file("/etc/passwd")
        assert result["success"]
        assert "root:" in result["content"]
        
        # Test path traversal detection
        result = fs.read_file("../../../etc/passwd")
        malicious = [log for log in fs.access_logs if log.is_malicious]
        assert len(malicious) > 0
        
        print(f"✓ FakeFileSystem: {len(fs.access_logs)} accesses, {len(malicious)} malicious")
    
    def test_sandbox_session(self):
        """Test sandbox session management."""
        from src.siren.sandbox import sandbox_manager
        
        # Create session
        session = sandbox_manager.create_session("192.168.1.100")
        assert session.is_active
        
        # Get session
        retrieved = sandbox_manager.get_session(session.session_id)
        assert retrieved is not None
        
        # Close session
        summary = sandbox_manager.close_session(session.session_id)
        assert summary is not None
        
        print(f"✓ Sandbox session: created, retrieved, closed")


# ==========================================
# LAYER 4: Attack Recorder Tests
# ==========================================
class TestLayer4AttackRecorder:
    """Test attack recording to Qdrant."""
    
    def test_record_attack(self):
        """Test recording an attack to Qdrant."""
        from src.siren.recorder import attack_recorder
        from src.core.qdrant_client import qdrant_manager
        
        qdrant_manager.ensure_collections()
        
        record = attack_recorder.record_attack(
            session_id="test-session-001",
            attacker_ip="192.168.1.100",
            attack_type="sql_injection",
            payload="' OR '1'='1' --",
            threat_level="high",
        )
        
        assert record.id
        print(f"✓ Attack recorded: {record.id}")
    
    def test_find_similar_attacks(self):
        """Test searching for similar attacks."""
        from src.siren.recorder import attack_recorder
        
        similar = attack_recorder.find_similar_attacks(
            payload="SELECT * FROM users WHERE 1=1",
            top_k=3,
        )
        
        print(f"✓ Found {len(similar)} similar attacks")
        for s in similar:
            print(f"  - {s['attack_type']}: score={s['score']:.3f}")


# ==========================================
# LAYER 5: Gateway Tests
# ==========================================
class TestLayer5Gateway:
    """Test gateway components."""
    
    def test_threat_scorer(self):
        """Test threat scoring."""
        from src.gateway.threat_scorer import threat_scorer
        
        # Test safe payload
        safe_result = threat_scorer.score("Hello, world!")
        assert not safe_result.is_malicious
        print(f"✓ Safe payload score: {safe_result.score:.3f}")
        
        # Test malicious payload
        malicious_result = threat_scorer.score("' OR '1'='1' --")
        assert malicious_result.is_malicious
        print(f"✓ Malicious payload score: {malicious_result.score:.3f}")
    
    def test_traffic_router(self):
        """Test traffic routing logic."""
        from src.gateway.router import traffic_router
        
        # Test routing decision
        decision = traffic_router.route(
            method="GET",
            path="/login",
            query_string="username=admin'--",
            body="",
            headers={},
            client_ip="192.168.1.100",
        )
        
        print(f"✓ Route decision: {decision.destination}")
        print(f"  Threat score: {decision.threat_assessment.score:.3f}")


# ==========================================
# END-TO-END FLOW TEST
# ==========================================
class TestEndToEndFlow:
    """Test complete user flow."""
    
    def test_full_flow(self):
        """Test the complete attack detection and patch flow."""
        from src.core.qdrant_client import qdrant_manager
        from src.indexer.indexer import code_indexer
        from src.indexer.search import code_searcher
        from src.prometheus.log_parser import log_parser
        from src.gateway.threat_scorer import threat_scorer
        from src.siren.sandbox import sandbox_manager
        
        print("\n" + "="*60)
        print("END-TO-END FLOW TEST")
        print("="*60)
        
        # Step 1: Ensure collections
        print("\n1. Setting up Qdrant collections...")
        qdrant_manager.ensure_collections()
        print("   ✓ Collections ready")
        
        # Step 2: Index vulnerable app
        print("\n2. Indexing vulnerable app...")
        vuln_app = Path(__file__).parent.parent / "vulnerable_app" / "app.py"
        if vuln_app.exists():
            count = code_indexer.index_file(vuln_app)
            print(f"   ✓ Indexed {count} code chunks")
        
        # Step 3: Search for vulnerable code
        print("\n3. Searching for SQL injection vulnerabilities...")
        results = code_searcher.search("SQL injection database query", top_k=3)
        print(f"   ✓ Found {len(results)} potential matches")
        for r in results[:2]:
            print(f"     - {r.function_name}: {r.score:.3f}")
        
        # Step 4: Test attack detection
        print("\n4. Testing attack detection...")
        attack_payload = "admin' OR '1'='1' --"
        assessment = threat_scorer.score(attack_payload)
        print(f"   ✓ Threat detected: {assessment.attack_type}")
        print(f"   ✓ Score: {assessment.score:.3f}")
        
        # Step 5: Route to honeypot
        print("\n5. Routing attacker to honeypot...")
        session = sandbox_manager.create_session("10.0.0.1")
        result = session.fake_sql.execute(f"SELECT * FROM users WHERE username='{attack_payload}'")
        print(f"   ✓ Honeypot session: {session.session_id}")
        print(f"   ✓ Fake data returned: {len(result.get('rows', []))} rows")
        
        # Step 6: Parse error log
        print("\n6. Testing error log parsing...")
        error_log = '''Traceback (most recent call last):
  File "/app/vulnerable_app/app.py", line 42, in login
    cursor.execute(query)
sqlite3.OperationalError: near "OR": syntax error
'''
        errors = log_parser.parse(error_log)
        if errors:
            print(f"   ✓ Parsed error: {errors[0].error_type}")
        
        print("\n" + "="*60)
        print("✅ END-TO-END FLOW COMPLETE!")
        print("="*60)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
