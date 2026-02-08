# src/siren/recorder.py
"""
Attack Recorder: Stores attack patterns in Qdrant for learning.
This is where Siren's memory becomes Prometheus's intelligence.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from loguru import logger

from src.core.config import settings
from src.core.qdrant_client import qdrant_manager
from src.core.embeddings import embedding_engine


@dataclass
class AttackRecord:
    """A recorded attack event."""
    id: str
    timestamp: datetime
    session_id: str
    attacker_ip: str
    attack_type: str  # sql_injection, path_traversal, xss, etc.
    payload: str
    threat_level: str  # low, medium, high, critical
    metadata: dict
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "session_id": self.session_id,
            "attacker_ip": self.attacker_ip,
            "attack_type": self.attack_type,
            "payload": self.payload[:200],  # Preview
            "threat_level": self.threat_level,
        }


class AttackRecorder:
    """
    Records and stores attack patterns in Qdrant.
    
    This creates the "attack_memory" that enables:
    - Instant threat recognition (no retraining needed)
    - Pattern correlation across sessions
    - Attack intelligence for future defense
    """
    
    def __init__(self, collection_name: Optional[str] = None):
        """Initialize the recorder."""
        self.collection_name = collection_name or settings.qdrant_attack_collection
        self.records: list[AttackRecord] = []
    
    def record_attack(
        self,
        session_id: str,
        attacker_ip: str,
        attack_type: str,
        payload: str,
        threat_level: str = "medium",
        metadata: Optional[dict] = None,
    ) -> AttackRecord:
        """
        Record an attack and store in Qdrant.
        
        Args:
            session_id: Honeypot session ID
            attacker_ip: Attacker's IP address
            attack_type: Type of attack (sql_injection, path_traversal, etc.)
            payload: The attack payload or command
            threat_level: Severity level
            metadata: Additional context
            
        Returns:
            The created AttackRecord
        """
        record_id = str(uuid.uuid4())
        
        record = AttackRecord(
            id=record_id,
            timestamp=datetime.now(),
            session_id=session_id,
            attacker_ip=attacker_ip,
            attack_type=attack_type,
            payload=payload,
            threat_level=threat_level,
            metadata=metadata or {},
        )
        
        self.records.append(record)
        
        # Store in Qdrant
        self._store_in_qdrant(record)
        
        logger.info(f"Recorded {attack_type} attack from {attacker_ip} [{threat_level}]")
        return record
    
    def _store_in_qdrant(self, record: AttackRecord) -> None:
        """Store attack record in Qdrant with embedding."""
        try:
            # Generate embedding for the attack pattern
            vector = embedding_engine.embed_attack(
                payload=record.payload,
                attack_type=record.attack_type,
            )
            
            # Build payload
            payload = {
                "session_id": record.session_id,
                "attacker_ip": record.attacker_ip,
                "attack_type": record.attack_type,
                "threat_level": record.threat_level,
                "payload_preview": record.payload[:500],
                "timestamp": record.timestamp.isoformat(),
                **record.metadata,
            }
            
            # Upsert to Qdrant
            qdrant_manager.upsert_vectors(
                collection_name=self.collection_name,
                ids=[record.id],
                vectors=[vector],
                payloads=[payload],
            )
            
        except Exception as e:
            logger.error(f"Failed to store attack in Qdrant: {e}")
    
    def find_similar_attacks(
        self,
        payload: str,
        top_k: int = 5,
        min_score: float = 0.8,
    ) -> list[dict]:
        """
        Find similar attack patterns in memory.
        
        This is the "instant recognition" capability.
        
        Args:
            payload: Incoming payload to check
            top_k: Number of similar attacks to return
            min_score: Minimum similarity threshold
            
        Returns:
            List of similar attack records
        """
        try:
            # Generate embedding for the query
            query_vector = embedding_engine.embed_attack(payload=payload)
            
            # Search Qdrant
            results = qdrant_manager.search_similar(
                collection_name=self.collection_name,
                query_vector=query_vector,
                top_k=top_k,
                score_threshold=min_score,
            )
            
            return [
                {
                    "score": r["score"],
                    "attack_type": r["payload"].get("attack_type"),
                    "threat_level": r["payload"].get("threat_level"),
                    "payload_preview": r["payload"].get("payload_preview"),
                }
                for r in results
            ]
        
        except Exception as e:
            logger.error(f"Failed to search attack memory: {e}")
            return []
    
    def classify_threat(self, payload: str) -> dict:
        """
        Classify an incoming payload based on attack memory.
        
        Returns threat classification with confidence.
        """
        similar = self.find_similar_attacks(payload, top_k=3, min_score=0.90)
        
        if not similar:
            return {
                "is_threat": False,
                "confidence": 0.0,
                "attack_type": None,
                "threat_level": None,
            }
        
        # Use the most similar match
        top_match = similar[0]
        
        return {
            "is_threat": True,
            "confidence": top_match["score"],
            "attack_type": top_match["attack_type"],
            "threat_level": top_match["threat_level"],
            "similar_attacks": len(similar),
        }
    
    def get_attack_statistics(self) -> dict:
        """Get statistics on recorded attacks."""
        if not self.records:
            return {"total": 0}
        
        attack_types = {}
        threat_levels = {}
        
        for record in self.records:
            attack_types[record.attack_type] = attack_types.get(record.attack_type, 0) + 1
            threat_levels[record.threat_level] = threat_levels.get(record.threat_level, 0) + 1
        
        return {
            "total": len(self.records),
            "by_type": attack_types,
            "by_threat_level": threat_levels,
            "unique_attackers": len(set(r.attacker_ip for r in self.records)),
        }
    
    def record_from_sandbox(self, session_summary: dict) -> None:
        """
        Record attacks from a closed sandbox session.
        
        Called when a honeypot session ends.
        """
        session_id = session_summary.get("session_id", "unknown")
        attacker_ip = session_summary.get("attacker_ip", "unknown")
        
        # Record SQL attacks
        sql_data = session_summary.get("sql_attacks", {})
        if sql_data.get("malicious_queries", 0) > 0:
            self.record_attack(
                session_id=session_id,
                attacker_ip=attacker_ip,
                attack_type="sql_injection",
                payload=str(sql_data),
                threat_level="high" if sql_data.get("malicious_queries", 0) > 5 else "medium",
                metadata={"query_count": sql_data.get("total_queries", 0)},
            )
        
        # Record filesystem attacks
        fs_data = session_summary.get("fs_attacks", {})
        if fs_data.get("malicious_attempts", 0) > 0:
            self.record_attack(
                session_id=session_id,
                attacker_ip=attacker_ip,
                attack_type="path_traversal",
                payload=str(fs_data.get("files_accessed", [])),
                threat_level="high" if "/etc/shadow" in str(fs_data) else "medium",
                metadata={"access_count": fs_data.get("total_accesses", 0)},
            )


# Singleton instance
attack_recorder = AttackRecorder()
