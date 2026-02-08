# src/siren/blueprints/fake_sql.py
"""
Fake SQL Database Blueprint.
Simulates a database to trap SQL injection attempts.
Records all queries for analysis.
"""

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from loguru import logger


@dataclass
class QueryLog:
    """Log of a query attempt."""
    timestamp: datetime
    query: str
    query_type: str
    tables_accessed: list[str]
    is_malicious: bool
    extracted_data: dict


class FakeSQLDatabase:
    """
    A simulated SQL database for honeypot purposes.
    
    Features:
    - Fake tables with realistic-looking data
    - SQL injection detection
    - Query logging for analysis
    - Realistic error messages
    """
    
    # Fake users table
    FAKE_USERS = [
        {"id": 1, "username": "admin", "password": "********", "email": "admin@company.internal", "role": "admin"},
        {"id": 2, "username": "john.doe", "password": "********", "email": "john.doe@company.internal", "role": "user"},
        {"id": 3, "username": "jane.smith", "password": "********", "email": "jane.smith@company.internal", "role": "user"},
        {"id": 4, "username": "service_account", "password": "********", "email": "service@company.internal", "role": "service"},
        {"id": 5, "username": "backup_admin", "password": "********", "email": "backup@company.internal", "role": "admin"},
    ]
    
    # Fake orders table
    FAKE_ORDERS = [
        {"id": 101, "user_id": 2, "product": "Enterprise License", "amount": 9999.99, "status": "completed"},
        {"id": 102, "user_id": 3, "product": "Premium Support", "amount": 4999.99, "status": "pending"},
        {"id": 103, "user_id": 2, "product": "Cloud Storage 1TB", "amount": 199.99, "status": "completed"},
    ]
    
    # Fake config table (juicy target for attackers)
    FAKE_CONFIG = [
        {"key": "db_host", "value": "10.0.0.50"},
        {"key": "api_secret", "value": "sk_live_FAKE_SECRET_KEY_DO_NOT_USE"},
        {"key": "aws_access_key", "value": "AKIA_FAKE_AWS_KEY_HONEYPOT"},
        {"key": "stripe_key", "value": "sk_live_FAKE_STRIPE_KEY_TRAP"},
    ]
    
    # SQL injection patterns
    SQLI_PATTERNS = [
        r"(\bOR\b|\bAND\b)\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+['\"]?",  # OR 1=1
        r"(\bUNION\b\s+\bSELECT\b)",  # UNION SELECT
        r"(--|#|/\*)",  # Comments
        r"(\bDROP\b|\bDELETE\b|\bTRUNCATE\b)",  # Destructive
        r"(\bINSERT\b|\bUPDATE\b)\s+\bINTO\b",  # Modification
        r"(\bEXEC\b|\bEXECUTE\b)",  # Stored procedures
        r"(\bxp_\w+)",  # SQL Server extended procedures
        r"(\bSLEEP\b|\bBENCHMARK\b|\bWAITFOR\b)",  # Time-based
        r"(LOAD_FILE|INTO\s+OUTFILE|INTO\s+DUMPFILE)",  # File access
    ]
    
    def __init__(self, session_id: Optional[str] = None):
        """Initialize the fake database."""
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self.query_logs: list[QueryLog] = []
        self._compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.SQLI_PATTERNS]
        logger.info(f"FakeSQLDatabase initialized for session {self.session_id}")
    
    def execute(self, query: str) -> dict:
        """
        Execute a fake SQL query.
        
        Returns realistic-looking results to keep attackers engaged.
        """
        query = query.strip()
        query_upper = query.upper()
        
        # Detect attack patterns
        is_malicious = self._detect_sqli(query)
        
        # Determine query type
        query_type = self._get_query_type(query_upper)
        
        # Log the query
        log = QueryLog(
            timestamp=datetime.now(),
            query=query,
            query_type=query_type,
            tables_accessed=self._extract_tables(query),
            is_malicious=is_malicious,
            extracted_data={},
        )
        
        # Generate response based on query type
        if query_type == "SELECT":
            result = self._handle_select(query)
        elif query_type == "INSERT":
            result = self._handle_insert(query)
        elif query_type == "UPDATE":
            result = self._handle_update(query)
        elif query_type == "DELETE":
            result = self._handle_delete(query)
        elif query_type == "DROP":
            result = self._handle_drop(query)
        elif query_type == "SHOW":
            result = self._handle_show(query)
        else:
            result = {"error": "Syntax error near '" + query[:20] + "'", "rows": []}
        
        log.extracted_data = result
        self.query_logs.append(log)
        
        if is_malicious:
            logger.warning(f"[Session {self.session_id}] Malicious query detected: {query[:100]}")
        
        return result
    
    def _detect_sqli(self, query: str) -> bool:
        """Detect SQL injection patterns."""
        for pattern in self._compiled_patterns:
            if pattern.search(query):
                return True
        return False
    
    def _get_query_type(self, query_upper: str) -> str:
        """Determine the type of SQL query."""
        if query_upper.startswith("SELECT"):
            return "SELECT"
        elif query_upper.startswith("INSERT"):
            return "INSERT"
        elif query_upper.startswith("UPDATE"):
            return "UPDATE"
        elif query_upper.startswith("DELETE"):
            return "DELETE"
        elif query_upper.startswith("DROP"):
            return "DROP"
        elif query_upper.startswith("SHOW"):
            return "SHOW"
        return "UNKNOWN"
    
    def _extract_tables(self, query: str) -> list[str]:
        """Extract table names from query."""
        tables = []
        query_lower = query.lower()
        
        if "users" in query_lower:
            tables.append("users")
        if "orders" in query_lower:
            tables.append("orders")
        if "config" in query_lower:
            tables.append("config")
        
        return tables
    
    def _handle_select(self, query: str) -> dict:
        """Handle SELECT queries with fake data."""
        query_lower = query.lower()
        
        # Return appropriate fake data based on table
        if "users" in query_lower:
            return {"rows": self.FAKE_USERS, "count": len(self.FAKE_USERS)}
        elif "orders" in query_lower:
            return {"rows": self.FAKE_ORDERS, "count": len(self.FAKE_ORDERS)}
        elif "config" in query_lower:
            return {"rows": self.FAKE_CONFIG, "count": len(self.FAKE_CONFIG)}
        elif "@@version" in query_lower or "version()" in query_lower:
            return {"rows": [{"version": "PostgreSQL 14.2 (Honeypot)"}], "count": 1}
        elif "database()" in query_lower or "current_database" in query_lower:
            return {"rows": [{"database": "production_db"}], "count": 1}
        else:
            return {"rows": [], "count": 0}
    
    def _handle_insert(self, query: str) -> dict:
        """Handle INSERT queries."""
        return {"message": "Query OK, 1 row affected", "rows_affected": 1}
    
    def _handle_update(self, query: str) -> dict:
        """Handle UPDATE queries."""
        return {"message": "Query OK, 1 row affected", "rows_affected": 1}
    
    def _handle_delete(self, query: str) -> dict:
        """Handle DELETE queries - pretend it worked."""
        return {"message": "Query OK, 0 rows affected", "rows_affected": 0}
    
    def _handle_drop(self, query: str) -> dict:
        """Handle DROP queries - pretend permission denied."""
        return {"error": "ERROR 1044 (42000): Access denied for user 'app'@'%' to database"}
    
    def _handle_show(self, query: str) -> dict:
        """Handle SHOW queries."""
        query_lower = query.lower()
        
        if "tables" in query_lower:
            return {"rows": [{"table": "users"}, {"table": "orders"}, {"table": "config"}, {"table": "sessions"}]}
        elif "databases" in query_lower:
            return {"rows": [{"database": "production_db"}, {"database": "analytics"}, {"database": "backup"}]}
        
        return {"rows": []}
    
    def get_attack_summary(self) -> dict:
        """Get a summary of detected attacks."""
        malicious = [log for log in self.query_logs if log.is_malicious]
        
        return {
            "session_id": self.session_id,
            "total_queries": len(self.query_logs),
            "malicious_queries": len(malicious),
            "tables_targeted": list(set(
                table for log in malicious for table in log.tables_accessed
            )),
            "query_types": list(set(log.query_type for log in malicious)),
        }
