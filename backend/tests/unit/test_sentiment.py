"""Unit tests for analysis/sentiment.py module."""
import pytest
from app.analysis import sentiment


class TestAnalyze:
    """Tests for analyze function."""
    
    def test_analyze_positive_text(self):
        """Test sentiment analysis of positive text."""
        result = sentiment.analyze("I love OVH cloud services! They are amazing!")
        assert result['label'] == 'positive'
        assert result['score'] > 0.05
        assert isinstance(result['score'], float)
    
    def test_analyze_negative_text(self):
        """Test sentiment analysis of negative text."""
        result = sentiment.analyze("OVH services are terrible and unreliable.")
        assert result['label'] == 'negative'
        assert result['score'] < -0.05
        assert isinstance(result['score'], float)
    
    def test_analyze_neutral_text(self):
        """Test sentiment analysis of neutral text."""
        result = sentiment.analyze("OVH is a cloud provider.")
        assert result['label'] == 'neutral'
        assert -0.05 <= result['score'] <= 0.05
        assert isinstance(result['score'], float)
    
    def test_analyze_empty_string(self):
        """Test sentiment analysis of empty string."""
        result = sentiment.analyze("")
        assert result['label'] == 'neutral'
        assert result['score'] == 0.0
    
    def test_analyze_none(self):
        """Test sentiment analysis with None input."""
        result = sentiment.analyze(None)
        assert result['label'] == 'neutral'
        assert result['score'] == 0.0
    
    def test_analyze_mixed_sentiment(self):
        """Test sentiment analysis of mixed sentiment text."""
        result = sentiment.analyze("OVH has good prices but slow support.")
        # Should classify based on overall compound score
        assert result['label'] in ['positive', 'negative', 'neutral']
        assert 'score' in result
        assert isinstance(result['score'], float)
    
    def test_analyze_very_positive(self):
        """Test sentiment analysis of very positive text."""
        result = sentiment.analyze("OVH is absolutely fantastic! Best cloud provider ever! Amazing service!")
        assert result['label'] == 'positive'
        assert result['score'] > 0.5  # Very positive
    
    def test_analyze_very_negative(self):
        """Test sentiment analysis of very negative text."""
        result = sentiment.analyze("OVH is absolutely terrible! Worst service ever! Completely unreliable!")
        assert result['label'] == 'negative'
        assert result['score'] < -0.5  # Very negative
    
    def test_analyze_french_text(self):
        """Test sentiment analysis of French text."""
        result = sentiment.analyze("OVH offre d'excellents services cloud.")
        # VADER works better with English, but should still return a result
        assert 'label' in result
        assert 'score' in result
        assert result['label'] in ['positive', 'negative', 'neutral']
    
    def test_analyze_result_structure(self):
        """Test that analyze returns correct structure."""
        result = sentiment.analyze("Test text")
        assert isinstance(result, dict)
        assert 'score' in result
        assert 'label' in result
        assert isinstance(result['score'], float)
        assert isinstance(result['label'], str)
        assert result['label'] in ['positive', 'negative', 'neutral']
















