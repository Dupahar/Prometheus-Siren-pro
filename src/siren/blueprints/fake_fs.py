# src/siren/blueprints/fake_fs.py
"""
Fake File System Blueprint.
Simulates a file system to trap path traversal and file access attempts.
"""

import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from loguru import logger


@dataclass
class FileAccessLog:
    """Log of a file access attempt."""
    timestamp: datetime
    operation: str  # read, write, list, delete
    path: str
    is_malicious: bool
    result: str


class FakeFileSystem:
    """
    A simulated file system for honeypot purposes.
    
    Features:
    - Fake sensitive files (/etc/passwd, config files)
    - Path traversal detection
    - Access logging
    - Realistic error messages
    """
    
    # Fake file contents
    FAKE_FILES = {
        "/etc/passwd": """root:x:0:0:root:/root:/bin/bash
daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin
www-data:x:33:33:www-data:/var/www:/usr/sbin/nologin
admin:x:1000:1000:Admin User:/home/admin:/bin/bash
backup:x:1001:1001:Backup User:/home/backup:/bin/bash
mysql:x:27:27:MySQL Server:/var/lib/mysql:/bin/false
""",
        "/etc/shadow": "Permission denied: /etc/shadow",
        
        "/home/admin/.ssh/id_rsa": """-----BEGIN OPENSSH PRIVATE KEY-----
HONEYPOT_FAKE_KEY_DO_NOT_USE_THIS_IS_A_TRAP
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABA
THIS_KEY_IS_MONITORED_ALL_USAGE_WILL_BE_LOGGED
-----END OPENSSH PRIVATE KEY-----
""",
        
        "/home/admin/.bash_history": """ls -la
cd /var/www/html
cat config.php
mysql -u root -p
ssh backup@10.0.0.50
scp backup@10.0.0.50:/data/backup.tar.gz .
""",
        
        "/var/www/html/config.php": """<?php
// Database configuration - HONEYPOT
$db_host = '10.0.0.50';
$db_user = 'app_user';
$db_pass = 'FAKE_PASSWORD_HONEYPOT_TRAP';
$db_name = 'production_db';

// API Keys - ALL FAKE
$stripe_key = 'sk_live_FAKE_STRIPE_KEY_MONITORED';
$aws_key = 'AKIAIOSFODNN7EXAMPLE_FAKE';
$aws_secret = 'wJalrXUtnFEMI/K7MDENG/FAKE_HONEYPOT';
?>
""",
        
        "/var/log/auth.log": """Jan 15 10:23:45 server sshd[1234]: Failed password for admin from 192.168.1.100
Jan 15 10:23:48 server sshd[1234]: Failed password for admin from 192.168.1.100
Jan 15 10:24:01 server sshd[1234]: Accepted password for admin from 192.168.1.100
Jan 15 11:15:22 server sudo: admin : TTY=pts/0 ; PWD=/home/admin ; USER=root ; COMMAND=/bin/cat /etc/shadow
""",
        
        "/app/.env": """# Environment Configuration - HONEYPOT
DATABASE_URL=postgresql://user:FAKE_PASS@10.0.0.50:5432/prod
SECRET_KEY=FAKE_SECRET_KEY_FOR_HONEYPOT_MONITORING
JWT_SECRET=FAKE_JWT_SECRET_ALL_TOKENS_INVALID
REDIS_URL=redis://:FAKE_REDIS_PASS@10.0.0.51:6379
""",
    }
    
    # Fake directory listings
    FAKE_DIRS = {
        "/": ["bin", "etc", "home", "var", "app", "root", "tmp", "usr"],
        "/etc": ["passwd", "shadow", "hosts", "nginx", "ssh"],
        "/home": ["admin", "backup", "deploy"],
        "/home/admin": [".ssh", ".bash_history", "data", "scripts"],
        "/home/admin/.ssh": ["id_rsa", "id_rsa.pub", "authorized_keys", "known_hosts"],
        "/var": ["log", "www", "lib", "run"],
        "/var/www": ["html"],
        "/var/www/html": ["index.php", "config.php", "api", "uploads"],
        "/var/log": ["auth.log", "syslog", "nginx", "mysql"],
        "/app": [".env", "main.py", "requirements.txt", "data"],
    }
    
    # Path traversal patterns
    TRAVERSAL_PATTERNS = [
        "..",
        "../",
        "..\\",
        "%2e%2e",
        "%2e%2e%2f",
        "....//",
        "..;/",
    ]
    
    def __init__(self, session_id: Optional[str] = None):
        """Initialize the fake file system."""
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self.access_logs: list[FileAccessLog] = []
        self.cwd = "/var/www/html"
        logger.info(f"FakeFileSystem initialized for session {self.session_id}")
    
    def read_file(self, path: str) -> dict:
        """Read a file (fake)."""
        normalized_path = self._normalize_path(path)
        is_malicious = self._detect_traversal(path)
        
        # Log access
        log = FileAccessLog(
            timestamp=datetime.now(),
            operation="read",
            path=path,
            is_malicious=is_malicious,
            result="",
        )
        
        if normalized_path in self.FAKE_FILES:
            content = self.FAKE_FILES[normalized_path]
            log.result = "success"
            self.access_logs.append(log)
            
            if is_malicious:
                logger.warning(f"[Session {self.session_id}] Path traversal detected: {path}")
            
            return {"success": True, "content": content, "path": normalized_path}
        else:
            log.result = "not_found"
            self.access_logs.append(log)
            return {"success": False, "error": f"No such file or directory: {path}"}
    
    def list_directory(self, path: str) -> dict:
        """List directory contents (fake)."""
        normalized_path = self._normalize_path(path)
        is_malicious = self._detect_traversal(path)
        
        log = FileAccessLog(
            timestamp=datetime.now(),
            operation="list",
            path=path,
            is_malicious=is_malicious,
            result="",
        )
        
        if normalized_path in self.FAKE_DIRS:
            contents = self.FAKE_DIRS[normalized_path]
            log.result = "success"
            self.access_logs.append(log)
            return {"success": True, "contents": contents, "path": normalized_path}
        else:
            log.result = "not_found"
            self.access_logs.append(log)
            return {"success": False, "error": f"No such directory: {path}"}
    
    def write_file(self, path: str, content: str) -> dict:
        """Write to a file (fake - always fails with permission error)."""
        is_malicious = self._detect_traversal(path)
        
        log = FileAccessLog(
            timestamp=datetime.now(),
            operation="write",
            path=path,
            is_malicious=is_malicious,
            result="permission_denied",
        )
        self.access_logs.append(log)
        
        if is_malicious:
            logger.warning(f"[Session {self.session_id}] Write attempt with traversal: {path}")
        
        return {"success": False, "error": "Permission denied: read-only file system"}
    
    def _normalize_path(self, path: str) -> str:
        """Normalize a path, resolving .. and ."""
        # Handle relative paths
        if not path.startswith("/"):
            path = os.path.join(self.cwd, path)
        
        # Normalize
        path = os.path.normpath(path)
        path = path.replace("\\", "/")
        
        return path
    
    def _detect_traversal(self, path: str) -> bool:
        """Detect path traversal attempts."""
        for pattern in self.TRAVERSAL_PATTERNS:
            if pattern in path:
                return True
        return False
    
    def get_attack_summary(self) -> dict:
        """Get a summary of detected attacks."""
        malicious = [log for log in self.access_logs if log.is_malicious]
        
        return {
            "session_id": self.session_id,
            "total_accesses": len(self.access_logs),
            "malicious_attempts": len(malicious),
            "files_accessed": list(set(log.path for log in malicious)),
            "operations": list(set(log.operation for log in malicious)),
        }
    
    def cd(self, path: str) -> dict:
        """Change directory."""
        normalized = self._normalize_path(path)
        
        if normalized in self.FAKE_DIRS:
            self.cwd = normalized
            return {"success": True, "cwd": self.cwd}
        else:
            return {"success": False, "error": f"No such directory: {path}"}
