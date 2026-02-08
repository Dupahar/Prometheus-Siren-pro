# src/siren/sandbox.py
"""
Sandbox Manager: Orchestrates isolated deception environments.
Uses Docker for ephemeral, isolated attacker sessions.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from loguru import logger

from src.core.config import settings
from .blueprints.fake_sql import FakeSQLDatabase
from .blueprints.fake_fs import FakeFileSystem


@dataclass
class SandboxSession:
    """Represents an active honeypot session."""
    session_id: str
    created_at: datetime
    attacker_ip: str
    fake_sql: FakeSQLDatabase
    fake_fs: FakeFileSystem
    is_active: bool = True
    last_activity: datetime = field(default_factory=datetime.now)
    
    def touch(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.now()
    
    @property
    def age_seconds(self) -> float:
        """Session age in seconds."""
        return (datetime.now() - self.created_at).total_seconds()
    
    @property
    def idle_seconds(self) -> float:
        """Time since last activity in seconds."""
        return (datetime.now() - self.last_activity).total_seconds()


class SandboxManager:
    """
    Manages honeypot sandbox sessions.
    
    Features:
    - Create isolated sessions for each attacker
    - Automatic timeout and cleanup
    - Track all sessions for analysis
    - Resource limits
    """
    
    def __init__(self):
        """Initialize the sandbox manager."""
        self.sessions: dict[str, SandboxSession] = {}
        self.max_sessions = settings.siren_max_sessions
        self.session_timeout = settings.siren_sandbox_timeout
    
    def create_session(self, attacker_ip: str) -> SandboxSession:
        """
        Create a new sandbox session for an attacker.
        
        Args:
            attacker_ip: IP address of the attacker
            
        Returns:
            SandboxSession with fake DB and FS
        """
        # Check capacity
        self._cleanup_expired()
        
        if len(self.sessions) >= self.max_sessions:
            logger.warning(f"Max sessions ({self.max_sessions}) reached, rejecting new session")
            # Close oldest session
            self._close_oldest_session()
        
        # Create new session
        session_id = str(uuid.uuid4())[:8]
        
        session = SandboxSession(
            session_id=session_id,
            created_at=datetime.now(),
            attacker_ip=attacker_ip,
            fake_sql=FakeSQLDatabase(session_id),
            fake_fs=FakeFileSystem(session_id),
        )
        
        self.sessions[session_id] = session
        logger.info(f"Created sandbox session {session_id} for {attacker_ip}")
        
        return session
    
    def get_session(self, session_id: str) -> Optional[SandboxSession]:
        """Get an existing session."""
        session = self.sessions.get(session_id)
        
        if session and session.is_active:
            # Check timeout
            if session.age_seconds > self.session_timeout:
                self.close_session(session_id)
                return None
            session.touch()
            return session
        
        return None
    
    def close_session(self, session_id: str) -> Optional[dict]:
        """
        Close a session and return attack summary.
        
        Returns combined attack data from all blueprints.
        """
        session = self.sessions.get(session_id)
        if not session:
            return None
        
        session.is_active = False
        
        # Collect attack summaries
        summary = {
            "session_id": session_id,
            "attacker_ip": session.attacker_ip,
            "duration_seconds": session.age_seconds,
            "sql_attacks": session.fake_sql.get_attack_summary(),
            "fs_attacks": session.fake_fs.get_attack_summary(),
        }
        
        logger.info(f"Closed session {session_id}, duration: {session.age_seconds:.0f}s")
        return summary
    
    def _cleanup_expired(self) -> int:
        """Clean up expired sessions."""
        expired = [
            sid for sid, session in self.sessions.items()
            if session.age_seconds > self.session_timeout or not session.is_active
        ]
        
        for sid in expired:
            self.close_session(sid)
            del self.sessions[sid]
        
        if expired:
            logger.debug(f"Cleaned up {len(expired)} expired sessions")
        
        return len(expired)
    
    def _close_oldest_session(self) -> None:
        """Close the oldest active session."""
        if not self.sessions:
            return
        
        oldest = min(self.sessions.values(), key=lambda s: s.created_at)
        self.close_session(oldest.session_id)
        del self.sessions[oldest.session_id]
    
    def get_active_sessions(self) -> list[dict]:
        """Get info about all active sessions."""
        self._cleanup_expired()
        
        return [
            {
                "session_id": s.session_id,
                "attacker_ip": s.attacker_ip,
                "age_seconds": s.age_seconds,
                "idle_seconds": s.idle_seconds,
            }
            for s in self.sessions.values()
            if s.is_active
        ]
    
    def get_all_attack_data(self) -> list[dict]:
        """Get attack summaries from all sessions (active and closed)."""
        summaries = []
        
        for session in self.sessions.values():
            summaries.append({
                "session_id": session.session_id,
                "attacker_ip": session.attacker_ip,
                "is_active": session.is_active,
                "sql_attacks": session.fake_sql.get_attack_summary(),
                "fs_attacks": session.fake_fs.get_attack_summary(),
            })
        
        return summaries


# Singleton instance
sandbox_manager = SandboxManager()
