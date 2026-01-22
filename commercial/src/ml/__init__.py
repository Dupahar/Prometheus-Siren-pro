# src/ml/__init__.py
"""
Local ML Engine for Prometheus-Siren.

Provides fast, on-device threat classification using a Mixture of Experts
architecture combining XGBoost (speed) and DistilBERT (accuracy).
"""

from src.ml.classifier import ThreatClassifier, ClassificationResult
from src.ml.dataset import AttackDataset, DatasetBuilder
from src.ml.trainer import ModelTrainer
from src.ml.hybrid_scorer import HybridThreatScorer, HybridAssessment, hybrid_scorer

__all__ = [
    "ThreatClassifier",
    "ClassificationResult", 
    "AttackDataset",
    "DatasetBuilder",
    "ModelTrainer",
    "HybridThreatScorer",
    "HybridAssessment",
    "hybrid_scorer",
]
