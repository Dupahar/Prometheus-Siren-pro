# tests/test_ml.py
"""
Tests for the ML module: classifier, dataset, trainer, and hybrid scorer.
"""

import pytest
from pathlib import Path


class TestDataset:
    """Tests for dataset building."""
    
    def test_dataset_builder_creates_samples(self):
        """Test that dataset builder creates balanced samples."""
        from src.ml.dataset import DatasetBuilder
        
        builder = DatasetBuilder()
        dataset = builder.build_full_dataset(
            attacks_per_type=10,
            safe_samples=50,
            include_qdrant=False,
        )
        
        assert len(dataset) > 0
        assert "safe" in dataset.stats()
    
    def test_dataset_balance(self):
        """Test dataset balancing."""
        from src.ml.dataset import DatasetBuilder
        
        builder = DatasetBuilder()
        builder.add_sqli_samples(20)
        builder.add_safe_samples(100)
        
        balanced = builder.dataset.balance(max_per_class=15)
        stats = balanced.stats()
        
        # Should have at most 15 per binary class
        safe_count = sum(1 for ex in balanced if ex.binary_label == "safe")
        attack_count = sum(1 for ex in balanced if ex.binary_label == "attack")
        
        assert safe_count <= 15
        assert attack_count <= 15
    
    def test_training_example_hash(self):
        """Test deduplication hash."""
        from src.ml.dataset import TrainingExample
        
        ex1 = TrainingExample(text="test", label="safe", source="test")
        ex2 = TrainingExample(text="test", label="attack", source="test")
        ex3 = TrainingExample(text="different", label="safe", source="test")
        
        # Same text should have same hash
        assert ex1.hash == ex2.hash
        # Different text should have different hash
        assert ex1.hash != ex3.hash


class TestFeatureExtractor:
    """Tests for feature extraction."""
    
    def test_extract_attack_features(self):
        """Test feature extraction for attack payloads."""
        from src.ml.classifier import FeatureExtractor
        
        extractor = FeatureExtractor()
        
        # SQL injection should have high sqlkeyword score
        sqli_features = extractor.extract("' OR 1=1--")
        safe_features = extractor.extract("Hello world")
        
        assert len(sqli_features) == len(safe_features)
        assert len(sqli_features) > 20  # Should have 20+ features
    
    def test_feature_names_match_length(self):
        """Test that feature names match extracted features."""
        from src.ml.classifier import FeatureExtractor
        
        extractor = FeatureExtractor()
        features = extractor.extract("test payload")
        names = extractor.get_feature_names()
        
        assert len(features) == len(names)


class TestClassifier:
    """Tests for threat classifier."""
    
    def test_classifier_init(self):
        """Test classifier initialization."""
        from src.ml.classifier import ThreatClassifier
        
        classifier = ThreatClassifier(mode="fast")
        assert classifier is not None
        assert classifier.mode == "fast"
    
    def test_classify_obvious_attack(self):
        """Test classification of obvious attack."""
        from src.ml.classifier import ThreatClassifier
        
        classifier = ThreatClassifier(mode="adaptive")
        
        # Obvious SQL injection
        result = classifier.classify("' OR 1=1--")
        
        assert result.prediction == "attack"
        assert result.confidence > 0.5
        assert result.attack_type is not None
    
    def test_classify_safe_traffic(self):
        """Test classification of safe traffic."""
        from src.ml.classifier import ThreatClassifier
        
        classifier = ThreatClassifier(mode="adaptive")
        
        result = classifier.classify("Hello, how are you today?")
        
        assert result.prediction == "safe"
        assert result.inference_time_ms >= 0
    
    def test_classifier_modes(self):
        """Test different classifier modes."""
        from src.ml.classifier import ThreatClassifier
        
        for mode in ["fast", "accurate", "adaptive", "ensemble"]:
            classifier = ThreatClassifier(mode=mode)
            result = classifier.classify("<script>alert(1)</script>")
            
            assert result.prediction == "attack"
            assert result.expert_used is not None


class TestHybridScorer:
    """Tests for hybrid threat scorer."""
    
    def test_hybrid_scorer_init(self):
        """Test hybrid scorer initialization."""
        from src.ml.hybrid_scorer import HybridThreatScorer
        
        scorer = HybridThreatScorer(mode="ml_only")
        assert scorer is not None
        assert scorer.mode == "ml_only"
    
    def test_ml_only_mode(self):
        """Test ML-only scoring mode."""
        from src.ml.hybrid_scorer import HybridThreatScorer
        
        scorer = HybridThreatScorer(mode="ml_only")
        result = scorer.score("' UNION SELECT * FROM users--")
        
        assert result.tier_used == "local_ml"
        assert result.ml_result is not None
        assert result.semantic_result is None
    
    def test_score_request(self):
        """Test full request scoring."""
        from src.ml.hybrid_scorer import HybridThreatScorer
        
        scorer = HybridThreatScorer(mode="ml_only")
        result = scorer.score_request(
            method="POST",
            path="/login",
            query_string="",
            body="username=admin'--&password=x",
            headers={"User-Agent": "Mozilla/5.0"},
        )
        
        assert result is not None
        assert result.action in ["allow", "block", "honeypot"]
    
    def test_stats_tracking(self):
        """Test statistics tracking."""
        from src.ml.hybrid_scorer import HybridThreatScorer
        
        scorer = HybridThreatScorer(mode="ml_only")
        
        # Score a few payloads
        scorer.score("test1")
        scorer.score("test2")
        scorer.score("test3")
        
        stats = scorer.get_stats()
        
        assert stats["total_requests"] == 3


class TestTrainingPipeline:
    """Tests for model training pipeline."""
    
    def test_dataset_split(self):
        """Test train/test split."""
        from src.ml.dataset import DatasetBuilder
        
        builder = DatasetBuilder()
        builder.add_sqli_samples(20)
        builder.add_safe_samples(30)
        
        train, test = builder.dataset.split(train_ratio=0.8)
        
        total = len(train) + len(test)
        assert total == len(builder.dataset)
        assert len(train) > len(test)
    
    @pytest.mark.skipif(
        not pytest.importorskip("xgboost", reason="XGBoost not installed"),
        reason="XGBoost required"
    )
    def test_xgboost_training(self):
        """Test XGBoost model training."""
        from src.ml.dataset import DatasetBuilder
        from src.ml.trainer import ModelTrainer
        import tempfile
        
        # Build small dataset
        builder = DatasetBuilder()
        builder.add_sqli_samples(20)
        builder.add_xss_samples(20)
        builder.add_safe_samples(40)
        
        train, test = builder.dataset.split()
        
        # Train
        with tempfile.TemporaryDirectory() as tmpdir:
            trainer = ModelTrainer(output_dir=Path(tmpdir))
            model_path, metrics = trainer.train_xgboost(train, test, binary=True)
            
            assert model_path.exists()
            assert metrics.accuracy > 0.5
