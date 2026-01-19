"""
Notification manager for handling email notifications when new posts are inserted.
"""
import json
import logging
import threading
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from . import email_sender
from . import trigger_checker
from .. import db

logger = logging.getLogger(__name__)

# Global email sender instance
_email_sender = None

def get_email_sender():
    """Get or create email sender instance."""
    global _email_sender
    if _email_sender is None:
        _email_sender = email_sender.EmailSender()
    return _email_sender


def check_and_send_notifications(post_id: int):
    """
    Check if newly inserted post triggers any notifications and send emails.
    
    This function is called asynchronously after a post is inserted.
    It should not block the main insertion flow.
    
    Args:
        post_id: ID of the newly inserted post
    """
    try:
        # Run in background thread to avoid blocking
        thread = threading.Thread(
            target=_check_and_send_notifications_sync,
            args=(post_id,),
            daemon=True
        )
        thread.start()
    except Exception as e:
        logger.error(f"Error starting notification check thread: {e}", exc_info=True)


def _check_and_send_notifications_sync(post_id: int):
    """Synchronous version of notification check (runs in background thread)."""
    try:
        # Get the post from database
        post = db.get_post_by_id(post_id)
        if not post:
            logger.warning(f"Post {post_id} not found for notification check")
            return
        
        # Get all active triggers
        triggers = db.get_active_notification_triggers()
        if not triggers:
            return  # No triggers configured
        
        # Check each trigger
        for trigger in triggers:
            try:
                # Check if post matches trigger conditions
                if not trigger_checker.TriggerChecker.post_matches_trigger(post, trigger):
                    continue
                
                # Check cooldown
                if trigger_checker.TriggerChecker.is_cooldown_active(trigger):
                    logger.debug(f"Trigger {trigger['id']} in cooldown, skipping notification")
                    continue
                
                # Get recent problematic posts (last 24 hours) for this trigger
                recent_posts = _get_recent_problematic_posts(trigger, max_posts=trigger.get('max_posts_per_email', 10))
                
                if not recent_posts:
                    continue
                
                # Send email notification
                emails = json.loads(trigger.get('emails', '[]'))
                if not emails:
                    logger.warning(f"Trigger {trigger['id']} has no email addresses configured")
                    continue
                
                success, error = _send_notification_email(trigger, recent_posts, emails)
                
                # Update trigger's last notification time
                if success:
                    db.update_trigger_last_notification_time(trigger['id'])
                
                # Log notification
                db.log_email_notification(
                    trigger_id=trigger['id'],
                    post_ids=[p['id'] for p in recent_posts],
                    recipient_emails=emails,
                    status='sent' if success else 'failed',
                    error_message=error
                )
                
            except Exception as e:
                logger.error(f"Error processing trigger {trigger.get('id')}: {e}", exc_info=True)
                continue
                
    except Exception as e:
        logger.error(f"Error in notification check: {e}", exc_info=True)


def _get_recent_problematic_posts(trigger: Dict, max_posts: int = 10) -> List[Dict]:
    """
    Get recent posts that match trigger conditions (last 24 hours).
    
    Args:
        trigger: Trigger dictionary
        max_posts: Maximum number of posts to return
    
    Returns:
        List of post dictionaries sorted by priority
    """
    try:
        # Get posts from last 24 hours
        recent_posts = db.get_recent_posts(hours=24)
        
        # Filter posts that match trigger conditions
        matching_posts = []
        for post in recent_posts:
            if trigger_checker.TriggerChecker.post_matches_trigger(post, trigger):
                matching_posts.append(post)
        
        # Sort by priority and limit
        sorted_posts = trigger_checker.TriggerChecker.sort_posts_by_priority(matching_posts)
        return sorted_posts[:max_posts]
        
    except Exception as e:
        logger.error(f"Error getting recent problematic posts: {e}", exc_info=True)
        return []


def _send_notification_email(trigger: Dict, posts: List[Dict], emails: List[str]) -> tuple[bool, Optional[str]]:
    """
    Send notification email for matching posts.
    
    Args:
        trigger: Trigger dictionary
        posts: List of post dictionaries to include in email
        emails: List of recipient email addresses
    
    Returns:
        (success: bool, error_message: Optional[str])
    """
    try:
        sender = get_email_sender()
        if not sender.is_configured():
            return False, "SMTP not configured"
        
        trigger_name = trigger.get('name', 'Unknown Trigger')
        success, error = sender.send_negative_posts_notification(emails, posts, trigger_name)
        
        return success, error
        
    except Exception as e:
        error_msg = f"Error sending notification email: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return False, error_msg

