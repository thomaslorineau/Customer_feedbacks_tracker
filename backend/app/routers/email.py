"""
Email notification routes.
"""
import re
import datetime
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .. import database as db
from ..auth.dependencies import require_auth

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# MODELS
# ============================================================================

class NotificationTriggerCreate(BaseModel):
    """Request model for creating a notification trigger."""
    name: str = Field(..., min_length=1, max_length=100)
    enabled: bool = Field(default=True)
    conditions: dict = Field(..., description="Trigger conditions (JSON)")
    emails: List[str] = Field(..., min_items=1, max_items=50, description="List of recipient emails")
    cooldown_minutes: int = Field(default=60, ge=1, le=1440, description="Cooldown in minutes")
    max_posts_per_email: int = Field(default=10, ge=1, le=50, description="Max posts per email")


class NotificationTriggerUpdate(BaseModel):
    """Request model for updating a notification trigger."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    enabled: Optional[bool] = None
    conditions: Optional[dict] = None
    emails: Optional[List[str]] = Field(None, min_items=1, max_items=50)
    cooldown_minutes: Optional[int] = Field(None, ge=1, le=1440)
    max_posts_per_email: Optional[int] = Field(None, ge=1, le=50)


class EmailConfigResponse(BaseModel):
    """Response model for email configuration status."""
    smtp_configured: bool = Field(..., description="Whether SMTP is configured")
    smtp_host: Optional[str] = Field(None, description="SMTP host (masked)")
    smtp_port: Optional[int] = None
    from_email: Optional[str] = Field(None, description="From email address")
    from_name: Optional[str] = None


class EmailTestRequest(BaseModel):
    """Request model for testing email."""
    recipient_email: str = Field(..., description="Email address to send test email to")


# ============================================================================
# TRIGGER ENDPOINTS
# ============================================================================

@router.get("/api/email/triggers")
async def get_email_triggers():
    """Get all notification triggers."""
    try:
        triggers = db.get_all_notification_triggers()
        return {"triggers": triggers, "total": len(triggers)}
    except Exception as e:
        logger.error(f"Error getting triggers: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/email/triggers/{trigger_id}")
async def get_email_trigger(trigger_id: int):
    """Get a specific notification trigger by ID."""
    try:
        trigger = db.get_notification_trigger(trigger_id)
        if not trigger:
            raise HTTPException(status_code=404, detail="Trigger not found")
        return trigger
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting trigger {trigger_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/email/triggers", response_model=dict)
async def create_email_trigger(trigger: NotificationTriggerCreate):
    """Create a new notification trigger."""
    try:
        # Validate email addresses
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        for email in trigger.emails:
            if not email_pattern.match(email):
                raise HTTPException(status_code=400, detail=f"Invalid email address: {email}")
        
        trigger_id = db.create_notification_trigger(
            name=trigger.name,
            conditions=trigger.conditions,
            emails=trigger.emails,
            cooldown_minutes=trigger.cooldown_minutes,
            max_posts_per_email=trigger.max_posts_per_email,
            enabled=trigger.enabled
        )
        return {"id": trigger_id, "message": "Trigger created successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating trigger: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/api/email/triggers/{trigger_id}", response_model=dict)
async def update_email_trigger(trigger_id: int, trigger: NotificationTriggerUpdate):
    """Update a notification trigger."""
    try:
        # Validate email addresses if provided
        if trigger.emails:
            email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
            for email in trigger.emails:
                if not email_pattern.match(email):
                    raise HTTPException(status_code=400, detail=f"Invalid email address: {email}")
        
        success = db.update_notification_trigger(
            trigger_id=trigger_id,
            name=trigger.name,
            conditions=trigger.conditions,
            emails=trigger.emails,
            cooldown_minutes=trigger.cooldown_minutes,
            max_posts_per_email=trigger.max_posts_per_email,
            enabled=trigger.enabled
        )
        if not success:
            raise HTTPException(status_code=404, detail="Trigger not found")
        return {"message": "Trigger updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating trigger {trigger_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/email/triggers/{trigger_id}", response_model=dict)
async def delete_email_trigger(trigger_id: int):
    """Delete a notification trigger."""
    try:
        success = db.delete_notification_trigger(trigger_id)
        if not success:
            raise HTTPException(status_code=404, detail="Trigger not found")
        return {"message": "Trigger deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting trigger {trigger_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/email/triggers/{trigger_id}/toggle", response_model=dict)
async def toggle_email_trigger(trigger_id: int):
    """Toggle enable/disable status of a trigger."""
    try:
        trigger = db.get_notification_trigger(trigger_id)
        if not trigger:
            raise HTTPException(status_code=404, detail="Trigger not found")
        
        new_status = not trigger['enabled']
        success = db.update_notification_trigger(trigger_id, enabled=new_status)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update trigger")
        
        return {"enabled": new_status, "message": f"Trigger {'enabled' if new_status else 'disabled'}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling trigger {trigger_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CONFIG ENDPOINTS
# ============================================================================

@router.get("/api/email/config", response_model=EmailConfigResponse)
async def get_email_config():
    """Get email configuration status (without exposing sensitive data)."""
    from ..notifications.email_sender import EmailSender
    sender = EmailSender()
    
    # Mask SMTP host if configured
    smtp_host_masked = None
    if sender.smtp_host:
        parts = sender.smtp_host.split('.')
        if len(parts) >= 2:
            smtp_host_masked = f"{parts[0][:2]}***.{'.'.join(parts[1:])}"
        else:
            smtp_host_masked = f"{sender.smtp_host[:2]}***"
    
    return EmailConfigResponse(
        smtp_configured=sender.is_configured(),
        smtp_host=smtp_host_masked,
        smtp_port=sender.smtp_port if sender.is_configured() else None,
        from_email=sender.from_email if sender.is_configured() else None,
        from_name=sender.from_name if sender.is_configured() else None
    )


@router.post("/api/email/test", response_model=dict)
async def test_email_connection(request: EmailTestRequest):
    """Test SMTP connection and send a test email."""
    try:
        from ..notifications.email_sender import EmailSender
        
        # Validate email format
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        if not email_pattern.match(request.recipient_email):
            raise HTTPException(status_code=400, detail="Invalid email address format")
        
        sender = EmailSender()
        
        if not sender.is_configured():
            raise HTTPException(status_code=400, detail="SMTP not configured. Set SMTP_HOST, SMTP_USER, SMTP_PASSWORD in .env")
        
        # Test connection
        success, error = sender.test_connection()
        if not success:
            raise HTTPException(status_code=500, detail=f"SMTP connection test failed: {error}")
        
        # Send test email to specified recipient
        test_posts = [{
            'id': 0,
            'source': 'Test',
            'author': 'System',
            'content': 'This is a test email to verify email notifications are working correctly.',
            'url': 'http://localhost:8000/dashboard',
            'created_at': datetime.datetime.now().isoformat(),
            'sentiment_label': 'neutral',
            'relevance_score': 1.0
        }]
        
        success, error = sender.send_negative_posts_notification(
            to_emails=[request.recipient_email],
            posts=test_posts,
            trigger_name="Test Notification"
        )
        
        if not success:
            raise HTTPException(status_code=500, detail=f"Failed to send test email: {error}")
        
        return {"message": f"Test email sent successfully to {request.recipient_email}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing email: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# NOTIFICATIONS HISTORY
# ============================================================================

@router.get("/api/email/notifications")
async def get_email_notifications(limit: int = 50, offset: int = 0):
    """Get email notification history."""
    try:
        notifications = db.get_email_notifications(limit=limit, offset=offset)
        return {"notifications": notifications, "total": len(notifications)}
    except Exception as e:
        logger.error(f"Error getting email notifications: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
