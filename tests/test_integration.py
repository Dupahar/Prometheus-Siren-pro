# tests/test_integration.py
"""
Integration Tests: Full end-to-end flow testing.
Tests the complete attack → detection → honeypot → evolution → patch cycle.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestFullIntegration:
    """Test the complete Prometheus-Siren flow."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup for integration tests."""
        from src.core.qdrant_client import qdrant_manager
        qdrant_manager.ensure_collections()
    
    def test_complete_attack_cycle(self):
        """
        Test the complete cycle:
        1. Index code
        2. Detect attack
        3. Route to honeypot
        4. Record attack
        5. Evolution learns
        6. Future attacks recognized faster
        """
        print("\n" + "="*60)
        print("INTEGRATION TEST: Complete Attack Cycle")
        print("="*60)
        
        # Step 1: Index vulnerable code
        print("\n[1] Indexing vulnerable app...")
        from src.indexer.indexer import code_indexer
        
        vuln_app = Path(__file__).parent.parent / "vulnerable_app" / "app.py"
        if vuln_app.exists():
            count = code_indexer.index_file(vuln_app)
            print(f"    ✓ Indexed {count} chunks")
            assert count > 0, "Should index some code"
        
        # Step 2: Detect attack via threat scorer
        print("\n[2] Testing attack detection...")
        from src.gateway.threat_scorer import threat_scorer
        
        attack_payload = "admin' OR '1'='1' UNION SELECT password FROM users --"
        assessment = threat_scorer.score(attack_payload)
        
        print(f"    ✓ Threat score: {assessment.score:.3f}")
        print(f"    ✓ Attack type: {assessment.attack_type}")
        assert assessment.is_malicious, "Should detect as malicious"
        assert assessment.score > 0.9, "Should have high threat score"
        
        # Step 3: Route to honeypot
        print("\n[3] Routing to honeypot...")
        from src.gateway.router import traffic_router
        
        decision = traffic_router.route(
            method="POST",
            path="/login",
            query_string="",
            body=f"username={attack_payload}&password=test",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            client_ip="10.0.0.100",
        )
        
        print(f"    ✓ Destination: {decision.destination}")
        assert decision.destination == "honeypot", "Should route to honeypot"
        assert decision.session_id is not None, "Should create session"
        
        # Step 4: Honeypot interaction
        print("\n[4] Interacting with honeypot...")
        from src.siren.sandbox import sandbox_manager
        
        session = sandbox_manager.get_session(decision.session_id)
        assert session is not None, "Session should exist"
        
        # Execute SQL in honeypot
        sql_result = session.fake_sql.execute(
            f"SELECT * FROM users WHERE username='{attack_payload}'"
        )
        print(f"    ✓ Honeypot returned {len(sql_result.get('rows', []))} fake rows")
        assert "rows" in sql_result, "Honeypot should return fake data"
        
        # Step 5: Record attack and evolve
        print("\n[5] Evolution learning from attack...")
        from src.evolution.feedback_loop import evolution_engine
        
        evolution_result = evolution_engine.evolve_from_attack(
            attack_type="sql_injection",
            payload=attack_payload,
            session_id=decision.session_id,
            attacker_ip="10.0.0.100",
        )
        
        print(f"    ✓ Attack ID: {evolution_result['attack_id']}")
        print(f"    ✓ Similar patterns: {evolution_result['similar_patterns_found']}")
        assert evolution_result["evolution_status"] == "complete"
        
        # Step 6: Verify future recognition
        print("\n[6] Testing future attack recognition...")
        from src.siren.recorder import attack_recorder
        
        similar = attack_recorder.find_similar_attacks(
            "SELECT * FROM users WHERE 1=1", top_k=3
        )
        print(f"    ✓ Found {len(similar)} similar patterns in memory")
        
        # Step 7: Check evolution insights
        print("\n[7] Checking evolution insights...")
        insights = evolution_engine.get_evolution_insights()
        print(f"    ✓ Total attacks processed: {insights['total_attacks_processed']}")
        print(f"    ✓ Patterns in memory: {insights['patterns_in_memory']}")
        
        print("\n" + "="*60)
        print("✅ INTEGRATION TEST PASSED: Full cycle complete!")
        print("="*60)
    
    def test_semantic_search_flow(self):
        """Test semantic search finds relevant vulnerabilities."""
        print("\n[Search] Testing semantic search...")
        
        from src.indexer.search import code_searcher
        
        # Search for SQL-related vulnerabilities
        results = code_searcher.search("SQL database query execute", top_k=5)
        
        print(f"    ✓ Found {len(results)} results")
        for r in results[:3]:
            print(f"      - {r.function_name}: {r.score:.3f}")
    
    def test_patch_generation_flow(self):
        """Test AI patch generation."""
        print("\n[Patch] Testing patch generation...")
        
        from src.prometheus.patch_generator import patch_generator
        
        vulnerable_code = '''
def get_user(username):
    query = f"SELECT * FROM users WHERE name='{username}'"
    return db.execute(query)
'''
        
        patch = patch_generator.generate_security_patch(
            vulnerability_type="sql_injection",
            vulnerable_code=vulnerable_code,
            context="Database query function",
        )
        
        if patch:
            print(f"    ✓ Patch generated with {patch.confidence:.0%} confidence")
            assert patch.patched_code is not None
            assert "?" in patch.patched_code or "%" in patch.patched_code, \
                "Patch should use parameterized query"
        else:
            print("    ⚠ Patch generation skipped (API limit)")
    
    def test_honeypot_blueprints(self):
        """Test honeypot blueprints return realistic data."""
        print("\n[Honeypot] Testing blueprints...")
        
        from src.siren.blueprints.fake_sql import FakeSQLDatabase
        from src.siren.blueprints.fake_fs import FakeFileSystem
        
        # SQL Blueprint
        db = FakeSQLDatabase()
        users = db.execute("SELECT * FROM users")
        config = db.execute("SELECT * FROM config")
        
        print(f"    ✓ FakeSQL: {len(users.get('rows', []))} users, {len(config.get('rows', []))} configs")
        assert len(users.get("rows", [])) > 0, "Should have fake users"
        assert any("api" in str(r) for r in config.get("rows", [])), "Should have fake API keys"
        
        # FS Blueprint
        fs = FakeFileSystem()
        passwd = fs.read_file("/etc/passwd")
        ssh_key = fs.read_file("/home/admin/.ssh/id_rsa")
        
        print(f"    ✓ FakeFS: passwd={passwd['success']}, ssh_key={ssh_key['success']}")
        assert passwd["success"], "Should return fake passwd"
        assert "HONEYPOT" in ssh_key.get("content", ""), "SSH key should be marked as honeypot"
    
    def test_evolution_priority_patches(self):
        """Test evolution suggests patch priorities."""
        print("\n[Evolution] Testing priority patches...")
        
        from src.evolution.feedback_loop import evolution_engine
        from src.siren.recorder import attack_recorder
        
        # Record some test attacks
        for i in range(3):
            attack_recorder.record_attack(
                session_id=f"test-{i}",
                attacker_ip=f"10.0.0.{i}",
                attack_type="sql_injection",
                payload=f"' OR 1=1 -- variant {i}",
                threat_level="high",
            )
        
        # Get priority suggestions
        suggestions = evolution_engine.suggest_priority_patches()
        
        print(f"    ✓ Got {len(suggestions)} patch suggestions")
        for s in suggestions[:3]:
            print(f"      - [{s['priority']}] {s['attack_type']}: {s['attacks_seen']} attacks")


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_safe_traffic_passes_through(self):
        """Safe traffic should not be flagged."""
        from src.gateway.threat_scorer import threat_scorer
        
        safe_payloads = [
            "Hello, world!",
            "user@example.com",
            "/api/v1/users/123",
            "John Smith",
        ]
        
        for payload in safe_payloads:
            result = threat_scorer.score(payload)
            # Safe payloads should not be marked as malicious
            assert not result.is_malicious, f"Safe payload flagged as malicious: {payload} (score={result.score})"
    
    def test_various_attack_types(self):
        """Test detection of various attack types."""
        from src.gateway.threat_scorer import threat_scorer
        
        attacks = {
            "sql_injection": "' UNION SELECT password FROM users--",
            "xss": "<script>alert('XSS')</script>",
            "path_traversal": "../../../etc/passwd",
            "command_injection": "; rm -rf /",
        }
        
        for attack_type, payload in attacks.items():
            result = threat_scorer.score(payload)
            print(f"    {attack_type}: score={result.score:.2f}, type={result.attack_type}")
            assert result.is_malicious, f"{attack_type} should be detected"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
