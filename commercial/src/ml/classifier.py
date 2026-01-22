# src/ml/classifier.py
"""
Threat Classifier: Mixture of Experts Model.

Combines XGBoost (speed) and DistilBERT (accuracy) in a 
Mixture of Experts architecture for optimal threat detection.

Architecture:
    Request → Gating Network → [XGBoost weight, BERT weight]
                    ↓
         Weighted ensemble of both experts
                    ↓
             Final prediction
"""

import time
import pickle
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Literal, List, Dict, Tuple
from loguru import logger


@dataclass
class ClassificationResult:
    """Result of threat classification."""
    prediction: Literal["safe", "attack"]  # Binary classification
    confidence: float                       # 0.0 - 1.0
    attack_type: Optional[str]              # "sqli", "xss", "traversal", "cmdi", "network", None
    inference_time_ms: float                # Time taken for inference
    expert_used: str                        # "xgboost", "distilbert", "ensemble"
    expert_scores: Dict[str, float]         # Individual expert scores
    
    @property
    def needs_deep_scan(self) -> bool:
        """Check if Gemini deep scan is needed (uncertain prediction)."""
        return 0.5 < self.confidence < 0.95
    
    @property
    def high_confidence(self) -> bool:
        """Check if prediction is high confidence."""
        return self.confidence >= 0.95
    
    def __repr__(self) -> str:
        return (
            f"ClassificationResult("
            f"prediction={self.prediction!r}, "
            f"confidence={self.confidence:.3f}, "
            f"attack_type={self.attack_type!r}, "
            f"time={self.inference_time_ms:.2f}ms, "
            f"expert={self.expert_used!r})"
        )


class FeatureExtractor:
    """
    Extract features from payloads for XGBoost classifier.
    
    Features:
    - Character distribution
    - Special character counts
    - Keyword presence
    - Structure analysis
    """
    
    # Attack-indicative keywords by type
    ATTACK_KEYWORDS = {
        "sqli": ["union", "select", "insert", "update", "delete", "drop", 
                 "table", "from", "where", "--", "/*", "*/", "or", "and",
                 "1=1", "1='1", "exec", "execute", "xp_", "sp_"],
        "xss": ["<script", "</script", "javascript:", "onerror", "onload",
                "onclick", "onmouseover", "onfocus", "alert", "document.",
                "eval(", "prompt(", "confirm(", "<img", "<svg", "<iframe"],
        "traversal": ["../", "..\\", "/etc/", "passwd", "shadow", "win.ini",
                      "boot.ini", "system32", "%2e%2e", "%252e", "file://"],
        "cmdi": [";", "|", "&", "`", "$(", "&&", "||", "cat ", "ls ", "rm ",
                 "wget", "curl", "bash", "sh ", "python", "perl", "nc ", "ncat"],
        "network": ["nmap", "scan", "flood", "ddos", "shellcode", "payload",
                    "169.254.169.254", "localhost", "127.0.0.1", "gopher://"],
    }
    
    def extract(self, text: str) -> List[float]:
        """Extract feature vector from text."""
        features = []
        
        # Length features
        features.append(len(text))
        features.append(len(text.split()))
        
        # Character type ratios
        total = max(len(text), 1)
        features.append(sum(c.isalpha() for c in text) / total)
        features.append(sum(c.isdigit() for c in text) / total)
        features.append(sum(c.isspace() for c in text) / total)
        
        # Special character counts
        special_chars = "'\";|&<>{}()[]$`\\!@#%^*"
        for char in special_chars:
            features.append(text.count(char) / total)
        
        # URL encoding detection
        features.append(text.count("%") / total)
        features.append(len(re.findall(r'%[0-9a-fA-F]{2}', text)) / max(total, 1))
        
        # Keyword presence for each attack type
        text_lower = text.lower()
        for attack_type, keywords in self.ATTACK_KEYWORDS.items():
            keyword_score = sum(1 for kw in keywords if kw.lower() in text_lower)
            features.append(keyword_score / len(keywords))
        
        # Structural features
        features.append(1.0 if "--" in text else 0.0)  # SQL comment
        features.append(1.0 if "/*" in text else 0.0)  # Block comment
        features.append(1.0 if "<" in text and ">" in text else 0.0)  # HTML-like
        features.append(1.0 if re.search(r'\.\./|\.\.\\', text) else 0.0)  # Traversal
        features.append(1.0 if re.search(r'[;|&`$]', text) else 0.0)  # Shell
        
        # Entropy (randomness indicator)
        if text:
            char_freq = {}
            for c in text:
                char_freq[c] = char_freq.get(c, 0) + 1
            entropy = 0
            for count in char_freq.values():
                prob = count / len(text)
                if prob > 0:
                    entropy -= prob * (prob if prob == 1 else __import__('math').log2(prob))
            features.append(entropy)
        else:
            features.append(0.0)
        
        return features
    
    def get_feature_names(self) -> List[str]:
        """Get feature names for debugging."""
        names = [
            "length", "word_count", 
            "alpha_ratio", "digit_ratio", "space_ratio",
        ]
        special_chars = "'\";|&<>{}()[]$`\\!@#%^*"
        for char in special_chars:
            names.append(f"char_{ord(char)}")
        names.extend(["pct_count", "url_encoded_count"])
        for attack_type in self.ATTACK_KEYWORDS:
            names.append(f"kw_{attack_type}")
        names.extend([
            "sql_comment", "block_comment", "html_like", 
            "traversal_pattern", "shell_chars", "entropy"
        ])
        return names


class XGBoostExpert:
    """
    XGBoost Expert: Ultra-fast threat classification.
    
    ~1ms inference time, good for high-volume filtering.
    """
    
    def __init__(self, model_path: Optional[Path] = None):
        """Initialize XGBoost expert."""
        self.model = None
        self.label_encoder = None
        self.feature_extractor = FeatureExtractor()
        self.model_path = model_path
        
        if model_path and Path(model_path).exists():
            self.load(model_path)
    
    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self.model is not None
    
    def predict(self, text: str) -> Tuple[str, float, str]:
        """
        Predict threat classification.
        
        Returns:
            Tuple of (prediction, confidence, attack_type)
        """
        if not self.is_loaded():
            # Fallback to rule-based when model not loaded
            return self._rule_based_predict(text)
        
        features = [self.feature_extractor.extract(text)]
        
        # Get prediction probabilities
        proba = self.model.predict_proba(features)[0]
        pred_idx = proba.argmax()
        confidence = float(proba[pred_idx])
        
        # Decode label
        label = self.label_encoder.inverse_transform([pred_idx])[0]
        
        # Determine binary prediction and attack type
        if label == "safe":
            return "safe", confidence, None
        else:
            return "attack", confidence, label
    
    def _rule_based_predict(self, text: str) -> Tuple[str, float, str]:
        """Fallback rule-based prediction when model not available."""
        text_lower = text.lower()
        
        # Check each attack type
        for attack_type, keywords in self.feature_extractor.ATTACK_KEYWORDS.items():
            matches = sum(1 for kw in keywords if kw.lower() in text_lower)
            if matches >= 2:
                confidence = min(0.5 + (matches * 0.1), 0.95)
                return "attack", confidence, attack_type
        
        # Default to safe
        return "safe", 0.7, None
    
    def save(self, path: Path) -> None:
        """Save trained model."""
        with open(path, "wb") as f:
            pickle.dump({
                "model": self.model,
                "label_encoder": self.label_encoder,
            }, f)
        logger.info(f"XGBoost model saved to {path}")
    
    def load(self, path: Path) -> None:
        """Load trained model."""
        with open(path, "rb") as f:
            data = pickle.load(f)
        self.model = data["model"]
        self.label_encoder = data["label_encoder"]
        logger.info(f"XGBoost model loaded from {path}")


class DistilBERTExpert:
    """
    DistilBERT Expert: High-accuracy threat classification.
    
    ~5ms inference time, better semantic understanding.
    """
    
    def __init__(self, model_path: Optional[Path] = None):
        """Initialize DistilBERT expert."""
        self.model = None
        self.tokenizer = None
        self.model_path = model_path
        self._device = "cpu"
        
        if model_path and Path(model_path).exists():
            self.load(model_path)
    
    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self.model is not None
    
    def predict(self, text: str) -> Tuple[str, float, str]:
        """
        Predict threat classification.
        
        Returns:
            Tuple of (prediction, confidence, attack_type)
        """
        if not self.is_loaded():
            # Fallback to semantic heuristics
            return self._heuristic_predict(text)
        
        import torch
        
        # Tokenize
        inputs = self.tokenizer(
            text, 
            return_tensors="pt", 
            truncation=True, 
            max_length=512,
            padding=True,
        ).to(self._device)
        
        # Inference
        with torch.no_grad():
            outputs = self.model(**inputs)
            proba = torch.softmax(outputs.logits, dim=-1)[0]
        
        pred_idx = proba.argmax().item()
        confidence = float(proba[pred_idx])
        
        # Map to labels (assuming id2label in model config)
        label = self.model.config.id2label.get(pred_idx, "unknown")
        
        if label == "safe":
            return "safe", confidence, None
        else:
            return "attack", confidence, label
    
    def _heuristic_predict(self, text: str) -> Tuple[str, float, str]:
        """Fallback semantic heuristics when model not available."""
        text_lower = text.lower()
        
        # Semantic patterns
        patterns = {
            "sqli": [
                r"'\s*(or|and)\s*['\"0-9]",
                r"union\s+(all\s+)?select",
                r"(;|--)\s*(drop|delete|truncate)",
            ],
            "xss": [
                r"<\s*script[^>]*>",
                r"on(error|load|click|focus)\s*=",
                r"javascript\s*:",
            ],
            "traversal": [
                r"\.\.[/\\]",
                r"/etc/(passwd|shadow)",
                r"%2e%2e[%/]",
            ],
            "cmdi": [
                r"[;&|`]\s*(cat|ls|rm|wget|curl|bash|sh|nc)\b",
                r"\$\([^)]+\)",
                r"`[^`]+`",
            ],
        }
        
        for attack_type, regexes in patterns.items():
            for pattern in regexes:
                if re.search(pattern, text_lower):
                    return "attack", 0.85, attack_type
        
        return "safe", 0.75, None
    
    def save(self, path: Path) -> None:
        """Save trained model."""
        if self.model:
            self.model.save_pretrained(path)
            self.tokenizer.save_pretrained(path)
            logger.info(f"DistilBERT model saved to {path}")
    
    def load(self, path: Path) -> None:
        """Load trained model."""
        try:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
            import torch
            
            self.tokenizer = AutoTokenizer.from_pretrained(path)
            self.model = AutoModelForSequenceClassification.from_pretrained(path)
            
            # Use GPU if available
            if torch.cuda.is_available():
                self._device = "cuda"
                self.model = self.model.to(self._device)
            
            self.model.eval()
            logger.info(f"DistilBERT model loaded from {path}")
        except Exception as e:
            logger.warning(f"Could not load DistilBERT model: {e}")


class ThreatClassifier:
    """
    Mixture of Experts Threat Classifier.
    
    Combines XGBoost (speed) and DistilBERT (accuracy) using
    a learned or heuristic gating mechanism.
    
    Architecture:
        Input → Gate → Weighted Expert Ensemble → Output
        
    Gate Modes:
    - "fast": Always use XGBoost (1ms)
    - "accurate": Always use DistilBERT (5ms)  
    - "adaptive": Use XGBoost first, DistilBERT if uncertain
    - "ensemble": Weighted combination of both experts
    """
    
    def __init__(
        self,
        mode: Literal["fast", "accurate", "adaptive", "ensemble"] = "adaptive",
        xgboost_path: Optional[Path] = None,
        distilbert_path: Optional[Path] = None,
    ):
        """Initialize the Mixture of Experts classifier."""
        self.mode = mode
        
        # Initialize experts
        model_dir = Path(__file__).parent / "models"
        
        xgb_path = xgboost_path or (model_dir / "xgboost_threat.pkl")
        bert_path = distilbert_path or (model_dir / "distilbert_threat")
        
        self.xgboost = XGBoostExpert(xgb_path if xgb_path.exists() else None)
        self.distilbert = DistilBERTExpert(bert_path if bert_path.exists() else None)
        
        # Gating weights (can be learned or fixed)
        self.xgb_weight = 0.4
        self.bert_weight = 0.6
        
        logger.info(
            f"ThreatClassifier initialized: mode={mode}, "
            f"xgb_loaded={self.xgboost.is_loaded()}, "
            f"bert_loaded={self.distilbert.is_loaded()}"
        )
    
    def classify(self, payload: str) -> ClassificationResult:
        """
        Classify a payload as safe or attack.
        
        Args:
            payload: Request body, query string, or full request
            
        Returns:
            ClassificationResult with prediction, confidence, and metadata
        """
        start = time.perf_counter()
        
        if self.mode == "fast":
            result = self._classify_fast(payload)
        elif self.mode == "accurate":
            result = self._classify_accurate(payload)
        elif self.mode == "adaptive":
            result = self._classify_adaptive(payload)
        else:  # ensemble
            result = self._classify_ensemble(payload)
        
        # Update timing
        elapsed = (time.perf_counter() - start) * 1000
        result.inference_time_ms = elapsed
        
        return result
    
    def _classify_fast(self, payload: str) -> ClassificationResult:
        """Fast mode: XGBoost only."""
        pred, conf, attack_type = self.xgboost.predict(payload)
        
        return ClassificationResult(
            prediction=pred,
            confidence=conf,
            attack_type=attack_type,
            inference_time_ms=0,  # Updated by caller
            expert_used="xgboost",
            expert_scores={"xgboost": conf},
        )
    
    def _classify_accurate(self, payload: str) -> ClassificationResult:
        """Accurate mode: DistilBERT only."""
        pred, conf, attack_type = self.distilbert.predict(payload)
        
        return ClassificationResult(
            prediction=pred,
            confidence=conf,
            attack_type=attack_type,
            inference_time_ms=0,
            expert_used="distilbert",
            expert_scores={"distilbert": conf},
        )
    
    def _classify_adaptive(self, payload: str) -> ClassificationResult:
        """Adaptive mode: XGBoost first, DistilBERT if uncertain."""
        # First try fast XGBoost
        xgb_pred, xgb_conf, xgb_type = self.xgboost.predict(payload)
        
        # High confidence - use XGBoost result
        if xgb_conf >= 0.90:
            return ClassificationResult(
                prediction=xgb_pred,
                confidence=xgb_conf,
                attack_type=xgb_type,
                inference_time_ms=0,
                expert_used="xgboost",
                expert_scores={"xgboost": xgb_conf},
            )
        
        # Low confidence - escalate to DistilBERT
        bert_pred, bert_conf, bert_type = self.distilbert.predict(payload)
        
        # Use higher confidence result
        if bert_conf > xgb_conf:
            return ClassificationResult(
                prediction=bert_pred,
                confidence=bert_conf,
                attack_type=bert_type,
                inference_time_ms=0,
                expert_used="distilbert",
                expert_scores={"xgboost": xgb_conf, "distilbert": bert_conf},
            )
        else:
            return ClassificationResult(
                prediction=xgb_pred,
                confidence=xgb_conf,
                attack_type=xgb_type,
                inference_time_ms=0,
                expert_used="xgboost",
                expert_scores={"xgboost": xgb_conf, "distilbert": bert_conf},
            )
    
    def _classify_ensemble(self, payload: str) -> ClassificationResult:
        """Ensemble mode: Weighted combination of both experts."""
        # Get both predictions
        xgb_pred, xgb_conf, xgb_type = self.xgboost.predict(payload)
        bert_pred, bert_conf, bert_type = self.distilbert.predict(payload)
        
        # Weighted voting
        xgb_attack_score = xgb_conf if xgb_pred == "attack" else (1 - xgb_conf)
        bert_attack_score = bert_conf if bert_pred == "attack" else (1 - bert_conf)
        
        ensemble_attack_score = (
            self.xgb_weight * xgb_attack_score + 
            self.bert_weight * bert_attack_score
        )
        
        # Final decision
        if ensemble_attack_score > 0.5:
            prediction = "attack"
            confidence = ensemble_attack_score
            attack_type = bert_type or xgb_type  # Prefer BERT's type classification
        else:
            prediction = "safe"
            confidence = 1 - ensemble_attack_score
            attack_type = None
        
        return ClassificationResult(
            prediction=prediction,
            confidence=confidence,
            attack_type=attack_type,
            inference_time_ms=0,
            expert_used="ensemble",
            expert_scores={"xgboost": xgb_conf, "distilbert": bert_conf},
        )
    
    def batch_classify(
        self, 
        payloads: List[str],
    ) -> List[ClassificationResult]:
        """Classify multiple payloads."""
        return [self.classify(p) for p in payloads]


# Singleton instance with adaptive mode
threat_classifier = ThreatClassifier(mode="adaptive")
