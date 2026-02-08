# src/evolution/feedback_loop.py
"""
The Evolution Engine: Where Siren teaches Prometheus.
This is the self-improvement core that makes the system truly cyber-immune.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from loguru import logger

from src.core.config import settings
from src.core.qdrant_client import qdrant_manager
from src.core.embeddings import embedding_engine
from src.siren.recorder import attack_recorder
from src.gateway.threat_scorer import threat_scorer
from src.indexer.search import code_searcher


@dataclass
class EvolutionMetrics:
    """Metrics for the evolution process."""
    attacks_processed: int = 0
    patterns_learned: int = 0
    threat_score_improvements: int = 0
    vulnerabilities_identified: int = 0
    patches_suggested: int = 0


class FeedbackLoop:
    """
    The Evolution Engine that creates a self-improving security system.
    
    Flow:
    1. Siren captures attack patterns
    2. Attack patterns are embedded and stored
    3. New attacks are compared against memory
    4. Prometheus uses attack patterns to prioritize patching
    5. ML models retrain when attack patterns drift
    
    NEW: ML Enhancement
    - Tracks attack counts for retraining triggers
    - Detects pattern drift
    - Exports training data for ML models
    """
    
    # ML retraining thresholds
    RETRAIN_THRESHOLD = 100  # Retrain after this many new attacks
    DRIFT_THRESHOLD = 0.3     # Retrain if attack distribution shifts > 30%
    
    def __init__(self):
        """Initialize the feedback loop."""
        self.metrics = EvolutionMetrics()
        self._last_evolution = datetime.now()
        self._attacks_since_retrain = 0
        self._last_attack_distribution: dict = {}
        self._retrain_pending = False
    
    def evolve_from_attack(
        self,
        attack_type: str,
        payload: str,
        session_id: str,
        attacker_ip: str,
    ) -> dict:
        """
        Process a captured attack and evolve the system.
        
        This is the core evolution function that:
        1. Records the attack to memory
        2. Finds similar code that might be vulnerable
        3. Updates threat scoring knowledge
        
        Args:
            attack_type: Type of attack (sql_injection, xss, etc.)
            payload: The attack payload
            session_id: Honeypot session ID
            attacker_ip: Attacker's IP
            
        Returns:
            Evolution result with insights
        """
        logger.info(f"Evolving from {attack_type} attack...")
        
        # Step 1: Record to attack memory
        record = attack_recorder.record_attack(
            session_id=session_id,
            attacker_ip=attacker_ip,
            attack_type=attack_type,
            payload=payload,
            threat_level=self._assess_threat_level(payload),
        )
        self.metrics.patterns_learned += 1
        
        # Step 2: Find potentially vulnerable code
        vulnerable_code = self._find_vulnerable_code(attack_type, payload)
        
        # Step 3: Update threat patterns
        similar_attacks = attack_recorder.find_similar_attacks(payload, top_k=5)
        
        result = {
            "attack_id": record.id,
            "attack_type": attack_type,
            "threat_level": record.threat_level,
            "similar_patterns_found": len(similar_attacks),
            "potentially_vulnerable_code": [
                {
                    "file": r.file_path,
                    "function": r.function_name,
                    "relevance": r.score,
                }
                for r in vulnerable_code[:3]
            ],
            "evolution_status": "complete",
        }
        
        self.metrics.attacks_processed += 1
        if vulnerable_code:
            self.metrics.vulnerabilities_identified += len(vulnerable_code)
        
        logger.success(f"Evolution complete: {len(similar_attacks)} similar patterns, {len(vulnerable_code)} potential vulnerabilities")
        return result
    
    def _assess_threat_level(self, payload: str) -> str:
        """Assess threat level based on payload characteristics."""
        payload_lower = payload.lower()
        
        # Critical patterns
        if any(p in payload_lower for p in ["drop table", "delete from", "rm -rf", "exec("]):
            return "critical"
        
        # High patterns
        if any(p in payload_lower for p in ["union select", "/etc/shadow", "cmd.exe", "<script"]):
            return "high"
        
        # Medium patterns
        if any(p in payload_lower for p in ["or 1=1", "../", "javascript:", "eval("]):
            return "medium"
        
        return "low"
    
    def _find_vulnerable_code(self, attack_type: str, payload: str):
        """Find code that might be vulnerable to this attack type."""
        # Map attack types to search queries
        search_queries = {
            "sql_injection": "SQL query execute database cursor",
            "xss": "render template HTML user input",
            "path_traversal": "file open read path",
            "command_injection": "subprocess shell execute command",
            "deserialization": "pickle load deserialize",
        }
        
        query = search_queries.get(attack_type, f"vulnerable {attack_type}")
        
        try:
            results = code_searcher.search(query, top_k=5)
            return results
        except Exception as e:
            logger.warning(f"Could not search for vulnerable code: {e}")
            return []
    
    def get_evolution_insights(self) -> dict:
        """Get insights from the evolution process."""
        stats = attack_recorder.get_attack_statistics()
        
        return {
            "total_attacks_processed": self.metrics.attacks_processed,
            "patterns_in_memory": stats.get("total", 0),
            "attack_types_seen": stats.get("by_type", {}),
            "threat_distribution": stats.get("by_threat_level", {}),
            "vulnerabilities_identified": self.metrics.vulnerabilities_identified,
            "last_evolution": self._last_evolution.isoformat(),
        }
    
    def suggest_priority_patches(self) -> list[dict]:
        """
        Suggest which code should be patched first based on attack patterns.
        
        This is where Siren's knowledge feeds into Prometheus's priorities.
        """
        stats = attack_recorder.get_attack_statistics()
        suggestions = []
        
        # Get most common attack types
        attack_types = stats.get("by_type", {})
        
        for attack_type, count in sorted(attack_types.items(), key=lambda x: -x[1]):
            # Find vulnerable code for this attack type
            vulnerable = self._find_vulnerable_code(attack_type, "")
            
            if vulnerable:
                suggestions.append({
                    "priority": "high" if count > 5 else "medium",
                    "attack_type": attack_type,
                    "attacks_seen": count,
                    "suggested_files": [
                        {"file": r.file_path, "function": r.function_name}
                        for r in vulnerable[:2]
                    ],
                })
        
        return suggestions
    
    def process_honeypot_session(self, session_summary: dict) -> dict:
        """
        Process a complete honeypot session and extract learnings.
        
        Called when a Siren session ends.
        """
        session_id = session_summary.get("session_id", "unknown")
        attacker_ip = session_summary.get("attacker_ip", "unknown")
        
        evolutions = []
        
        # Process SQL attacks
        sql_data = session_summary.get("sql_attacks", {})
        if sql_data.get("malicious_queries", 0) > 0:
            result = self.evolve_from_attack(
                attack_type="sql_injection",
                payload=str(sql_data),
                session_id=session_id,
                attacker_ip=attacker_ip,
            )
            evolutions.append(result)
        
        # Process filesystem attacks
        fs_data = session_summary.get("fs_attacks", {})
        if fs_data.get("malicious_attempts", 0) > 0:
            result = self.evolve_from_attack(
                attack_type="path_traversal",
                payload=str(fs_data.get("files_accessed", [])),
                session_id=session_id,
                attacker_ip=attacker_ip,
            )
            evolutions.append(result)
        
        return {
            "session_id": session_id,
            "evolutions": evolutions,
            "total_learnings": len(evolutions),
        }
    
    # ==========================================
    # ML Enhancement Methods
    # ==========================================
    
    def should_retrain(self) -> bool:
        """
        Check if ML models should be retrained.
        
        Triggers:
        1. Attack count exceeds threshold
        2. Attack distribution has drifted
        """
        # Check attack count
        if self._attacks_since_retrain >= self.RETRAIN_THRESHOLD:
            logger.info(f"Retrain trigger: {self._attacks_since_retrain} attacks since last retrain")
            return True
        
        # Check for drift
        if self._detect_drift():
            logger.info("Retrain trigger: Attack distribution drift detected")
            return True
        
        return False
    
    def _detect_drift(self) -> bool:
        """Detect if attack distribution has shifted significantly."""
        current = attack_recorder.get_attack_statistics().get("by_type", {})
        
        if not self._last_attack_distribution or not current:
            return False
        
        # Calculate distribution shift
        all_types = set(current.keys()) | set(self._last_attack_distribution.keys())
        total_current = sum(current.values()) or 1
        total_last = sum(self._last_attack_distribution.values()) or 1
        
        drift = 0.0
        for attack_type in all_types:
            current_ratio = current.get(attack_type, 0) / total_current
            last_ratio = self._last_attack_distribution.get(attack_type, 0) / total_last
            drift += abs(current_ratio - last_ratio)
        
        return drift > self.DRIFT_THRESHOLD
    
    def export_training_data(self, output_dir: Optional[str] = None) -> dict:
        """
        Export attack data for ML training.
        
        Pulls real attacks from Qdrant and formats for training.
        """
        from pathlib import Path
        
        try:
            # Get attacks from Qdrant
            records, _ = qdrant_manager.client.scroll(
                collection_name=qdrant_manager.attack_collection,
                limit=1000,
                with_payload=True,
            )
            
            # Format as training examples
            examples = []
            for record in records:
                payload = record.payload
                examples.append({
                    "text": payload.get("payload", ""),
                    "label": payload.get("attack_type", "unknown"),
                    "source": "qdrant_evolution",
                    "confidence": 0.95,
                    "metadata": {
                        "session_id": payload.get("session_id"),
                        "threat_level": payload.get("threat_level"),
                    },
                })
            
            # Save if output dir specified
            if output_dir:
                import json
                out_path = Path(output_dir) / "evolution_attacks.json"
                out_path.parent.mkdir(parents=True, exist_ok=True)
                with open(out_path, "w") as f:
                    json.dump(examples, f, indent=2)
                logger.info(f"Exported {len(examples)} training examples to {out_path}")
            
            return {
                "exported_count": len(examples),
                "attack_types": list(set(e["label"] for e in examples)),
            }
            
        except Exception as e:
            logger.warning(f"Could not export training data: {e}")
            return {"exported_count": 0, "error": str(e)}
    
    def trigger_retrain(self, async_mode: bool = True) -> dict:
        """
        Trigger ML model retraining.
        
        Args:
            async_mode: If True, queue for background training
        """
        logger.info("Triggering ML model retrain...")
        
        # Export latest training data
        export_result = self.export_training_data()
        
        if async_mode:
            # Mark for background retraining
            self._retrain_pending = True
            return {
                "status": "queued",
                "exported": export_result["exported_count"],
                "message": "Retrain queued for background processing",
            }
        
        # Synchronous retrain
        try:
            from src.ml.trainer import quick_train
            result = quick_train()
            
            # Reset counters
            self._attacks_since_retrain = 0
            self._last_attack_distribution = attack_recorder.get_attack_statistics().get("by_type", {})
            self._retrain_pending = False
            
            return {
                "status": "complete",
                "metrics": result,
            }
        except Exception as e:
            logger.error(f"Retrain failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    def check_and_evolve_ml(self) -> Optional[dict]:
        """Check if ML retrain is needed and trigger if so."""
        self._attacks_since_retrain += 1
        
        if self.should_retrain():
            return self.trigger_retrain(async_mode=True)
        return None


# Singleton instance
evolution_engine = FeedbackLoop()
