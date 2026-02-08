# src/gateway/threat_scorer.py
"""
Threat Scorer: Real-time threat assessment using attack memory.
This determines if traffic should go to the real app or the honeypot.
"""

from dataclasses import dataclass
from typing import Optional
from loguru import logger

from src.core.config import settings
from src.siren.recorder import attack_recorder


@dataclass
class ThreatAssessment:
    """Result of threat scoring."""
    payload: str
    score: float  # 0-1, higher = more threatening
    is_malicious: bool
    attack_type: Optional[str]
    confidence: float
    similar_attacks: int
    action: str  # "allow", "block", "honeypot"
    
    @property
    def threat_level(self) -> str:
        """Human-readable threat level."""
        if self.score < 0.3:
            return "low"
        elif self.score < 0.6:
            return "medium"
        elif self.score < 0.85:
            return "high"
        else:
            return "critical"


class ThreatScorer:
    """
    Scores incoming requests for threat level.
    
    Uses attack_memory vectors for instant pattern matching.
    No regex rules needed - purely semantic similarity.
    """
    
    # Known malicious patterns for quick detection
    QUICK_PATTERNS = {
        "sql_injection": [
            "' OR '1'='1",
            "1; DROP TABLE",
            "UNION SELECT",
            "' OR 1=1--",
            "admin'--",
        ],
        "xss": [
            "<script>",
            "javascript:",
            "onerror=",
            "onload=",
            "onclick=",
        ],
        "path_traversal": [
            "../",
            "..\\",
            "/etc/passwd",
            "/etc/shadow",
            "..%2f",
        ],
        "command_injection": [
            "; ls",
            "| cat",
            "$(whoami)",
            "`id`",
            "&& rm",
            "; rm",
            "| rm",
            "; bash",
            "| bash",
            "; sh",
        ],
    }
    
    def __init__(self):
        """Initialize the threat scorer."""
        self.threshold = settings.threat_threshold
    
    def score(self, payload: str) -> ThreatAssessment:
        """
        Score a payload for threat level.
        
        Combines:
        1. Quick pattern matching (fast)
        2. Semantic search in attack_memory (accurate)
        
        Args:
            payload: Request body, query string, or headers
            
        Returns:
            ThreatAssessment with score and recommended action
        """
        # Step 1: Quick pattern check
        quick_result = self._quick_pattern_check(payload)
        if quick_result["is_malicious"]:
            return ThreatAssessment(
                payload=payload,
                score=0.95,
                is_malicious=True,
                attack_type=quick_result["attack_type"],
                confidence=0.9,
                similar_attacks=0,
                action="honeypot",
            )
        
        # Step 2: Semantic search in attack memory
        classification = attack_recorder.classify_threat(payload)
        
        if classification["is_threat"]:
            score = classification["confidence"]
            is_malicious = score >= self.threshold
            
            return ThreatAssessment(
                payload=payload,
                score=score,
                is_malicious=is_malicious,
                attack_type=classification["attack_type"],
                confidence=classification["confidence"],
                similar_attacks=classification.get("similar_attacks", 0),
                action="honeypot" if is_malicious else "allow",
            )
        
        # No threat detected
        return ThreatAssessment(
            payload=payload,
            score=0.0,
            is_malicious=False,
            attack_type=None,
            confidence=0.0,
            similar_attacks=0,
            action="allow",
        )
    
    def _quick_pattern_check(self, payload: str) -> dict:
        """Quick pattern-based check for obvious attacks."""
        payload_lower = payload.lower()
        
        for attack_type, patterns in self.QUICK_PATTERNS.items():
            for pattern in patterns:
                if pattern.lower() in payload_lower:
                    logger.debug(f"Quick match: {attack_type} pattern '{pattern}'")
                    return {
                        "is_malicious": True,
                        "attack_type": attack_type,
                        "pattern": pattern,
                    }
        
        return {"is_malicious": False, "attack_type": None}
    
    def score_request(
        self,
        method: str,
        path: str,
        query_string: str,
        body: str,
        headers: dict,
    ) -> ThreatAssessment:
        """
        Score a full HTTP request.
        
        Combines multiple parts of the request for comprehensive scoring.
        """
        # Combine all parts into one payload for scoring
        combined = f"""
Method: {method}
Path: {path}
Query: {query_string}
Body: {body}
"""
        
        # Check suspicious headers
        suspicious_headers = []
        for key, value in headers.items():
            key_lower = key.lower()
            if key_lower in ["user-agent", "x-forwarded-for", "referer"]:
                suspicious_headers.append(f"{key}: {value}")
        
        if suspicious_headers:
            combined += "Headers:\n" + "\n".join(suspicious_headers)
        
        return self.score(combined)


# Singleton instance
threat_scorer = ThreatScorer()
