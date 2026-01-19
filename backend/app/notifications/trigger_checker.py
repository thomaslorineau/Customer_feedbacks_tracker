"""
Trigger checker module for evaluating if a post matches notification trigger conditions.
"""
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class TriggerChecker:
    """Checks if posts match trigger conditions."""
    
    @staticmethod
    def post_matches_trigger(post: Dict, trigger: Dict) -> bool:
        """
        Check if a post matches the trigger conditions.
        
        Args:
            post: Post dictionary with keys: source, sentiment_label, relevance_score, language, etc.
            trigger: Trigger dictionary with 'conditions' (JSON string)
        
        Returns:
            bool: True if post matches conditions
        """
        try:
            conditions = json.loads(trigger.get('conditions', '{}'))
            
            # Check sentiment
            if 'sentiment' in conditions:
                required_sentiment = conditions['sentiment'].lower()
                if required_sentiment != 'all':
                    post_sentiment = post.get('sentiment_label', 'neutral').lower()
                    if post_sentiment != required_sentiment:
                        return False
            
            # Check relevance score minimum
            if 'relevance_score_min' in conditions:
                min_relevance = float(conditions['relevance_score_min'])
                post_relevance = float(post.get('relevance_score', 0.0))
                if post_relevance < min_relevance:
                    return False
            
            # Check sources
            if 'sources' in conditions and conditions['sources']:
                allowed_sources = [s.lower() for s in conditions['sources']]
                post_source = post.get('source', '').lower()
                if post_source not in allowed_sources:
                    return False
            
            # Check language
            if 'language' in conditions and conditions['language']:
                required_language = conditions['language'].lower()
                if required_language != 'all':
                    post_language = post.get('language', 'unknown').lower()
                    if post_language != required_language:
                        return False
            
            # Check priority score minimum (optional)
            if 'priority_score_min' in conditions:
                min_priority = float(conditions['priority_score_min'])
                # Calculate priority score: sentiment * relevance * recency
                priority_score = TriggerChecker._calculate_priority_score(post)
                if priority_score < min_priority:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking trigger conditions: {e}", exc_info=True)
            return False
    
    @staticmethod
    def _calculate_priority_score(post: Dict) -> float:
        """
        Calculate priority score for a post.
        
        Formula: sentiment_value × relevance_score × recency_value
        
        Args:
            post: Post dictionary
        
        Returns:
            float: Priority score (0.0 to 1.0)
        """
        # Sentiment value
        sentiment_label = post.get('sentiment_label', 'neutral').lower()
        sentiment_values = {
            'negative': 1.0,
            'neutral': 0.5,
            'positive': 0.2
        }
        sentiment_value = sentiment_values.get(sentiment_label, 0.5)
        
        # Relevance score
        relevance_score = float(post.get('relevance_score', 0.0))
        
        # Recency value (decay over time)
        try:
            created_at = post.get('created_at', '')
            if created_at:
                post_date = datetime.fromisoformat(created_at.replace('Z', '+00:00').replace('+00:00', ''))
                now = datetime.now()
                age_hours = (now - post_date.replace(tzinfo=None)).total_seconds() / 3600
                # Exponential decay: 1.0 for < 1 hour, 0.5 for 24 hours, 0.1 for 7 days
                recency_value = max(0.1, 1.0 / (1.0 + age_hours / 24.0))
            else:
                recency_value = 0.5
        except Exception:
            recency_value = 0.5
        
        return sentiment_value * relevance_score * recency_value
    
    @staticmethod
    def is_cooldown_active(trigger: Dict) -> bool:
        """
        Check if trigger is in cooldown period.
        
        Args:
            trigger: Trigger dictionary with 'last_notification_sent_at' and 'cooldown_minutes'
        
        Returns:
            bool: True if cooldown is active (should not send notification)
        """
        last_sent = trigger.get('last_notification_sent_at')
        if not last_sent:
            return False  # No previous notification, cooldown not active
        
        cooldown_minutes = int(trigger.get('cooldown_minutes', 60))
        
        try:
            last_sent_dt = datetime.fromisoformat(last_sent.replace('Z', '+00:00').replace('+00:00', ''))
            now = datetime.now()
            elapsed_minutes = (now - last_sent_dt.replace(tzinfo=None)).total_seconds() / 60
            
            return elapsed_minutes < cooldown_minutes
        except Exception as e:
            logger.error(f"Error checking cooldown: {e}")
            return False  # If error, allow notification
    
    @staticmethod
    def sort_posts_by_priority(posts: List[Dict]) -> List[Dict]:
        """
        Sort posts by priority score (highest first).
        
        Args:
            posts: List of post dictionaries
        
        Returns:
            List of posts sorted by priority (highest first)
        """
        def get_priority(post):
            return TriggerChecker._calculate_priority_score(post)
        
        return sorted(posts, key=get_priority, reverse=True)

