# src/ml/hybrid_scorer.py
"""
Hybrid Threat Scorer: Integrates Local ML with Gemini Deep Scan.

This is the bridge between the fast local ML and the semantic Gemini analysis.
Uses a tiered approach for optimal speed-accuracy tradeoff.

Architecture:
    Request → Local ML (5ms) → [High Confidence?]
                                    │
                   ┌────────────────┼────────────────┐
                   ▼                ▼                ▼
              [SAFE 95%+]     [UNCERTAIN]      [ATTACK 95%+]
                   │                │                │
                ALLOW         GEMINI SCAN        HONEYPOT
"""

from dataclasses import dataclass
from typing import Optional, Literal
from loguru import logger

from src.ml.classifier import ThreatClassifier, ClassificationResult
from src.gateway.threat_scorer import ThreatAssessment, ThreatScorer


@dataclass
class HybridAssessment:
    """Extended threat assessment with hybrid intelligence."""
    
    # Core assessment
    payload: str
    score: float
    is_malicious: bool
    attack_type: Optional[str]
    action: Literal["allow", "block", "honeypot"]
    
    # ML tier info
    tier_used: Literal["local_ml", "gemini_deep", "combined"]
    ml_result: Optional[ClassificationResult]
    semantic_result: Optional[ThreatAssessment]
    
    # Performance
    total_time_ms: float
    ml_time_ms: float
    semantic_time_ms: float
    
    @property
    def confidence(self) -> float:
        """Overall confidence in the assessment."""
        if self.ml_result and self.semantic_result:
            # Weighted average when both are used
            return 0.4 * self.ml_result.confidence + 0.6 * self.score
        elif self.ml_result:
            return self.ml_result.confidence
        else:
            return self.score
    
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
    
    def to_threat_assessment(self) -> ThreatAssessment:
        """Convert to legacy ThreatAssessment for backward compatibility."""
        return ThreatAssessment(
            payload=self.payload,
            score=self.score,
            is_malicious=self.is_malicious,
            attack_type=self.attack_type,
            confidence=self.confidence,
            similar_attacks=0,
            action=self.action,
        )


class HybridThreatScorer:
    """
    Two-tier threat scoring with Local ML + Gemini Deep Scan.
    
    Tier 1 (Fast): Local ML classifier (~5ms)
        - XGBoost + DistilBERT Mixture of Experts
        - Handles 95%+ of requests
        
    Tier 2 (Accurate): Gemini + Qdrant (~500ms)
        - Semantic understanding
        - Attack memory similarity search
        - Only used for uncertain cases
        
    Modes:
        - "ml_only": Only use local ML (fastest, offline-capable)
        - "gemini_only": Only use Gemini (most accurate)
        - "hybrid": ML first, Gemini for uncertain (default)
        - "parallel": Run both and combine results
    """
    
    def __init__(
        self,
        mode: Literal["ml_only", "gemini_only", "hybrid", "parallel"] = "hybrid",
        ml_confidence_threshold: float = 0.90,
    ):
        """
        Initialize hybrid scorer.
        
        Args:
            mode: Scoring mode
            ml_confidence_threshold: Min ML confidence to skip Gemini
        """
        self.mode = mode
        self.ml_threshold = ml_confidence_threshold
        
        # Initialize components
        self.ml_classifier = ThreatClassifier(mode="adaptive")
        self.semantic_scorer = ThreatScorer()
        
        # Stats
        self.stats = {
            "total_requests": 0,
            "ml_only_decisions": 0,
            "gemini_escalations": 0,
            "avg_ml_time_ms": 0.0,
            "avg_gemini_time_ms": 0.0,
        }
        
        logger.info(
            f"HybridThreatScorer initialized: mode={mode}, "
            f"threshold={ml_confidence_threshold}"
        )
    
    def score(self, payload: str) -> HybridAssessment:
        """
        Score a payload using hybrid intelligence.
        
        Args:
            payload: Request body, query string, or raw request
            
        Returns:
            HybridAssessment with scoring result and metadata
        """
        import time
        start = time.perf_counter()
        
        self.stats["total_requests"] += 1
        
        if self.mode == "ml_only":
            return self._score_ml_only(payload, start)
        elif self.mode == "gemini_only":
            return self._score_gemini_only(payload, start)
        elif self.mode == "parallel":
            return self._score_parallel(payload, start)
        else:  # hybrid (default)
            return self._score_hybrid(payload, start)
    
    def _score_ml_only(self, payload: str, start: float) -> HybridAssessment:
        """ML-only scoring (fastest, offline-capable)."""
        import time
        
        ml_result = self.ml_classifier.classify(payload)
        ml_time = ml_result.inference_time_ms
        
        self.stats["ml_only_decisions"] += 1
        self._update_avg_time("ml", ml_time)
        
        total_time = (time.perf_counter() - start) * 1000
        
        return HybridAssessment(
            payload=payload,
            score=ml_result.confidence if ml_result.prediction == "attack" else (1 - ml_result.confidence),
            is_malicious=ml_result.prediction == "attack",
            attack_type=ml_result.attack_type,
            action=self._decide_action(ml_result.prediction, ml_result.confidence),
            tier_used="local_ml",
            ml_result=ml_result,
            semantic_result=None,
            total_time_ms=total_time,
            ml_time_ms=ml_time,
            semantic_time_ms=0,
        )
    
    def _score_gemini_only(self, payload: str, start: float) -> HybridAssessment:
        """Gemini-only scoring (most accurate)."""
        import time
        
        semantic_start = time.perf_counter()
        semantic_result = self.semantic_scorer.score(payload)
        semantic_time = (time.perf_counter() - semantic_start) * 1000
        
        self.stats["gemini_escalations"] += 1
        self._update_avg_time("gemini", semantic_time)
        
        total_time = (time.perf_counter() - start) * 1000
        
        return HybridAssessment(
            payload=payload,
            score=semantic_result.score,
            is_malicious=semantic_result.is_malicious,
            attack_type=semantic_result.attack_type,
            action=semantic_result.action,
            tier_used="gemini_deep",
            ml_result=None,
            semantic_result=semantic_result,
            total_time_ms=total_time,
            ml_time_ms=0,
            semantic_time_ms=semantic_time,
        )
    
    def _score_hybrid(self, payload: str, start: float) -> HybridAssessment:
        """Hybrid scoring: ML first, Gemini for uncertain cases."""
        import time
        
        # Tier 1: Local ML
        ml_result = self.ml_classifier.classify(payload)
        ml_time = ml_result.inference_time_ms
        
        # Check if ML is confident enough
        if ml_result.high_confidence:
            # High confidence - use ML result directly
            self.stats["ml_only_decisions"] += 1
            self._update_avg_time("ml", ml_time)
            
            total_time = (time.perf_counter() - start) * 1000
            
            return HybridAssessment(
                payload=payload,
                score=ml_result.confidence if ml_result.prediction == "attack" else 0.0,
                is_malicious=ml_result.prediction == "attack",
                attack_type=ml_result.attack_type,
                action=self._decide_action(ml_result.prediction, ml_result.confidence),
                tier_used="local_ml",
                ml_result=ml_result,
                semantic_result=None,
                total_time_ms=total_time,
                ml_time_ms=ml_time,
                semantic_time_ms=0,
            )
        
        # Tier 2: Escalate to Gemini for uncertain cases
        semantic_start = time.perf_counter()
        semantic_result = self.semantic_scorer.score(payload)
        semantic_time = (time.perf_counter() - semantic_start) * 1000
        
        self.stats["gemini_escalations"] += 1
        self._update_avg_time("ml", ml_time)
        self._update_avg_time("gemini", semantic_time)
        
        # Combine results (trust Gemini more for uncertain cases)
        combined_score = 0.3 * (ml_result.confidence if ml_result.prediction == "attack" else 0) + \
                        0.7 * semantic_result.score
        
        is_malicious = combined_score > 0.5 or semantic_result.is_malicious
        
        total_time = (time.perf_counter() - start) * 1000
        
        return HybridAssessment(
            payload=payload,
            score=combined_score,
            is_malicious=is_malicious,
            attack_type=semantic_result.attack_type or ml_result.attack_type,
            action="honeypot" if is_malicious else "allow",
            tier_used="combined",
            ml_result=ml_result,
            semantic_result=semantic_result,
            total_time_ms=total_time,
            ml_time_ms=ml_time,
            semantic_time_ms=semantic_time,
        )
    
    def _score_parallel(self, payload: str, start: float) -> HybridAssessment:
        """Parallel scoring: Run both and combine."""
        import time
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        with ThreadPoolExecutor(max_workers=2) as executor:
            ml_future = executor.submit(self.ml_classifier.classify, payload)
            semantic_future = executor.submit(self.semantic_scorer.score, payload)
            
            ml_result = ml_future.result()
            semantic_result = semantic_future.result()
        
        ml_time = ml_result.inference_time_ms
        # Estimate semantic time
        semantic_time = 0  # Can't measure accurately in parallel
        
        # Weighted ensemble
        ml_attack_score = ml_result.confidence if ml_result.prediction == "attack" else (1 - ml_result.confidence)
        combined_score = 0.4 * ml_attack_score + 0.6 * semantic_result.score
        
        is_malicious = combined_score > 0.5
        
        self._update_avg_time("ml", ml_time)
        
        total_time = (time.perf_counter() - start) * 1000
        
        return HybridAssessment(
            payload=payload,
            score=combined_score,
            is_malicious=is_malicious,
            attack_type=semantic_result.attack_type or ml_result.attack_type,
            action="honeypot" if is_malicious else "allow",
            tier_used="combined",
            ml_result=ml_result,
            semantic_result=semantic_result,
            total_time_ms=total_time,
            ml_time_ms=ml_time,
            semantic_time_ms=semantic_time,
        )
    
    def _decide_action(
        self, 
        prediction: str, 
        confidence: float,
    ) -> Literal["allow", "block", "honeypot"]:
        """Decide action based on prediction and confidence."""
        if prediction == "safe":
            return "allow"
        elif confidence >= 0.9:
            return "honeypot"  # High confidence attack -> trap them
        elif confidence >= 0.7:
            return "honeypot"  # Medium-high -> still trap
        else:
            return "allow"  # Low confidence -> let through
    
    def _update_avg_time(self, tier: str, time_ms: float) -> None:
        """Update running average time."""
        key = f"avg_{tier}_time_ms"
        n = self.stats["total_requests"]
        if n > 1:
            self.stats[key] = (self.stats[key] * (n - 1) + time_ms) / n
        else:
            self.stats[key] = time_ms
    
    def get_stats(self) -> dict:
        """Get scoring statistics."""
        stats = self.stats.copy()
        if stats["total_requests"] > 0:
            stats["ml_only_ratio"] = stats["ml_only_decisions"] / stats["total_requests"]
            stats["escalation_ratio"] = stats["gemini_escalations"] / stats["total_requests"]
        return stats
    
    def score_request(
        self,
        method: str,
        path: str,
        query_string: str,
        body: str,
        headers: dict,
    ) -> HybridAssessment:
        """
        Score a full HTTP request.
        
        Combines multiple parts of the request for comprehensive scoring.
        """
        # Combine all parts
        combined = f"""
Method: {method}
Path: {path}
Query: {query_string}
Body: {body}
"""
        # Add suspicious headers
        for key, value in headers.items():
            if key.lower() in ["user-agent", "x-forwarded-for", "referer", "cookie"]:
                combined += f"{key}: {value}\n"
        
        return self.score(combined)


# Singleton instance
hybrid_scorer = HybridThreatScorer(mode="hybrid")
