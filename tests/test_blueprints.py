# tests/test_blueprints.py
"""Tests for Siren Deception Blueprints - No external dependencies"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.siren.blueprints.fake_sql import FakeSQLDatabase
from src.siren.blueprints.fake_fs import FakeFileSystem


class TestFakeSQLDatabase:
    """Test the fake SQL database honeypot."""
    
    def setup_method(self):
        self.db = FakeSQLDatabase(session_id="test-session")
    
    def test_basic_select(self):
        """Test basic SELECT query."""
        result = self.db.execute("SELECT * FROM users")
        
        assert "rows" in result
        assert len(result["rows"]) > 0
    
    def test_sql_injection_detection(self):
        """Test SQL injection pattern detection."""
        # OR 1=1 injection
        result = self.db.execute("SELECT * FROM users WHERE id='1' OR '1'='1'")
        
        # Check that the attack was logged as malicious
        malicious_logs = [log for log in self.db.query_logs if log.is_malicious]
        assert len(malicious_logs) > 0
    
    def test_union_injection_detection(self):
        """Test UNION SELECT injection detection."""
        result = self.db.execute("SELECT id FROM users UNION SELECT password FROM users")
        
        malicious_logs = [log for log in self.db.query_logs if log.is_malicious]
        assert len(malicious_logs) > 0
    
    def test_safe_query_not_flagged(self):
        """Test that safe queries aren't flagged."""
        self.db.query_logs.clear()
        result = self.db.execute("SELECT id, username FROM users WHERE id = 1")
        
        malicious_logs = [log for log in self.db.query_logs if log.is_malicious]
        assert len(malicious_logs) == 0
    
    def test_fake_config_data(self):
        """Test that fake config data is returned."""
        result = self.db.execute("SELECT * FROM config")
        
        assert "rows" in result
        config_keys = [r["key"] for r in result["rows"]]
        assert "api_secret" in config_keys
    
    def test_drop_returns_error(self):
        """Test that DROP queries return permission denied."""
        result = self.db.execute("DROP TABLE users")
        
        assert "error" in result
        assert "Access denied" in result["error"]
    
    def test_show_tables(self):
        """Test SHOW TABLES query."""
        result = self.db.execute("SHOW TABLES")
        
        assert "rows" in result
        tables = [r["table"] for r in result["rows"]]
        assert "users" in tables
    
    def test_attack_summary(self):
        """Test attack summary generation."""
        # Execute some attacks (patterns that match the regex)
        self.db.execute("SELECT * FROM users WHERE id=1 OR 1=1")  # Matches OR 1=1 pattern
        self.db.execute("SELECT id FROM users UNION SELECT password FROM config")  # Matches UNION SELECT
        
        summary = self.db.get_attack_summary()
        
        assert summary["session_id"] == "test-session"
        assert summary["malicious_queries"] >= 2, f"Expected >= 2 malicious, got {summary['malicious_queries']}"


class TestFakeFileSystem:
    """Test the fake filesystem honeypot."""
    
    def setup_method(self):
        self.fs = FakeFileSystem(session_id="test-session")
    
    def test_read_passwd(self):
        """Test reading /etc/passwd."""
        result = self.fs.read_file("/etc/passwd")
        
        assert result["success"]
        assert "root:" in result["content"]
    
    def test_path_traversal_detection(self):
        """Test path traversal detection."""
        result = self.fs.read_file("../../../etc/passwd")
        
        # Check that it was logged as malicious
        malicious_logs = [log for log in self.fs.access_logs if log.is_malicious]
        assert len(malicious_logs) > 0
    
    def test_read_ssh_key(self):
        """Test reading fake SSH key."""
        result = self.fs.read_file("/home/admin/.ssh/id_rsa")
        
        assert result["success"]
        assert "HONEYPOT" in result["content"]
    
    def test_list_directory(self):
        """Test directory listing."""
        result = self.fs.list_directory("/etc")
        
        assert result["success"]
        assert "passwd" in result["contents"]
    
    def test_write_denied(self):
        """Test that writes are denied."""
        result = self.fs.write_file("/etc/passwd", "hacked!")
        
        assert not result["success"]
        assert "Permission denied" in result["error"]
    
    def test_nonexistent_file(self):
        """Test reading nonexistent file."""
        result = self.fs.read_file("/nonexistent/file.txt")
        
        assert not result["success"]
        assert "No such file" in result["error"]
    
    def test_change_directory(self):
        """Test directory change."""
        result = self.fs.cd("/home/admin")
        
        assert result["success"]
        assert self.fs.cwd == "/home/admin"
    
    def test_fake_config(self):
        """Test reading fake config file."""
        result = self.fs.read_file("/var/www/html/config.php")
        
        assert result["success"]
        assert "HONEYPOT" in result["content"]
    
    def test_attack_summary(self):
        """Test attack summary generation."""
        # Perform some attacks
        self.fs.read_file("../../../etc/passwd")
        self.fs.read_file("/etc/../etc/shadow")
        
        summary = self.fs.get_attack_summary()
        
        assert summary["session_id"] == "test-session"
        assert summary["malicious_attempts"] >= 2
