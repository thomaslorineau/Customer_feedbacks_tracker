"""
Email sender module for sending notifications via SMTP.
"""
import smtplib
import os
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Optional
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class EmailSender:
    """Handles sending emails via SMTP."""
    
    def __init__(self):
        self.smtp_host = os.getenv('SMTP_HOST', '')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_user = os.getenv('SMTP_USER', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.from_email = os.getenv('SMTP_FROM_EMAIL', self.smtp_user)
        self.from_name = os.getenv('SMTP_FROM_NAME', 'OVH Feedbacks Tracker')
        self.enabled = bool(self.smtp_host and self.smtp_user and self.smtp_password)
        
        if not self.enabled:
            logger.warning("Email notifications disabled: SMTP configuration missing")
    
    def is_configured(self) -> bool:
        """Check if SMTP is properly configured."""
        return self.enabled
    
    def send_email(
        self,
        to_emails: List[str],
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Send email to multiple recipients.
        
        Args:
            to_emails: List of recipient email addresses
            subject: Email subject
            html_content: HTML email body
            text_content: Plain text email body (optional)
        
        Returns:
            (success: bool, error_message: Optional[str])
        """
        if not self.enabled:
            return False, "SMTP not configured"
        
        if not to_emails:
            return False, "No recipient emails provided"
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = ', '.join(to_emails)
            
            # Add text and HTML parts
            if text_content:
                text_part = MIMEText(text_content, 'plain', 'utf-8')
                msg.attach(text_part)
            
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            # Connect to SMTP server
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg, to_addrs=to_emails)
            
            logger.info(f"Email sent successfully to {len(to_emails)} recipients")
            return True, None
            
        except smtplib.SMTPAuthenticationError as e:
            error_msg = f"SMTP authentication failed: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except smtplib.SMTPException as e:
            error_msg = f"SMTP error: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error sending email: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg
    
    def send_negative_posts_notification(
        self,
        to_emails: List[str],
        posts: List[Dict],
        trigger_name: str
    ) -> tuple[bool, Optional[str]]:
        """
        Send notification email for negative/problematic posts.
        
        Args:
            to_emails: List of recipient email addresses
            posts: List of post dictionaries with keys: id, source, author, content, url, 
                   created_at, sentiment_score, sentiment_label, relevance_score
            trigger_name: Name of the trigger that activated this notification
        
        Returns:
            (success: bool, error_message: Optional[str])
        """
        if not posts:
            return False, "No posts to send"
        
        # Generate HTML content
        html_content = self._generate_email_html(posts, trigger_name)
        
        # Generate text content
        text_content = self._generate_email_text(posts, trigger_name)
        
        # Subject
        subject = f"🚨 {len(posts)} nouveau(x) post(s) problématique(s) détecté(s) - {trigger_name}"
        
        return self.send_email(to_emails, subject, html_content, text_content)
    
    def _generate_email_html(self, posts: List[Dict], trigger_name: str) -> str:
        """Generate HTML email content."""
        posts_html = []
        
        for post in posts:
            source = post.get('source', 'Unknown')
            author = post.get('author', 'Unknown')
            content = post.get('content', '')
            url = post.get('url', '#')
            created_at = post.get('created_at', '')
            sentiment_label = post.get('sentiment_label', 'neutral')
            relevance_score = post.get('relevance_score', 0.0)
            
            # Truncate content
            content_preview = content[:200] + "..." if len(content) > 200 else content
            
            # Sentiment emoji
            sentiment_emoji = {
                'negative': '🔴',
                'positive': '🟢',
                'neutral': '🟡'
            }.get(sentiment_label, '⚪')
            
            post_html = f"""
            <div style="margin-bottom: 20px; padding: 15px; background: #f5f5f5; border-radius: 8px; border-left: 4px solid #e74c3c;">
                <div style="margin-bottom: 10px;">
                    <strong>{sentiment_emoji} {source}</strong> | 
                    <span style="color: #666;">{author}</span> | 
                    <span style="color: #666; font-size: 0.9em;">{created_at}</span>
                </div>
                <div style="margin-bottom: 10px; color: #333;">
                    {content_preview.replace(chr(10), '<br>')}
                </div>
                <div style="font-size: 0.85em; color: #666;">
                    Score de pertinence: {relevance_score:.2%} | 
                    <a href="{url}" style="color: #3498db;">Voir le post original</a>
                </div>
            </div>
            """
            posts_html.append(post_html)
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background: #2c3e50; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .footer {{ background: #ecf0f1; padding: 15px; text-align: center; font-size: 0.9em; color: #666; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🚨 Nouveaux posts problématiques détectés</h1>
                <p>Trigger: {trigger_name}</p>
            </div>
            <div class="content">
                <p><strong>{len(posts)} post(s) problématique(s)</strong> ont été détectés et nécessitent votre attention.</p>
                <hr style="margin: 20px 0; border: none; border-top: 1px solid #ddd;">
                {''.join(posts_html)}
            </div>
            <div class="footer">
                <p>OVH Customer Feedbacks Tracker</p>
                <p><a href="http://localhost:8000/dashboard" style="color: #3498db;">Accéder au dashboard</a></p>
            </div>
        </body>
        </html>
        """
        return html
    
    def _generate_email_text(self, posts: List[Dict], trigger_name: str) -> str:
        """Generate plain text email content."""
        lines = [
            f"🚨 Nouveaux posts problématiques détectés",
            f"Trigger: {trigger_name}",
            "",
            f"{len(posts)} post(s) problématique(s) ont été détectés:",
            "",
        ]
        
        for i, post in enumerate(posts, 1):
            source = post.get('source', 'Unknown')
            author = post.get('author', 'Unknown')
            content = post.get('content', '')
            url = post.get('url', '#')
            created_at = post.get('created_at', '')
            sentiment_label = post.get('sentiment_label', 'neutral')
            relevance_score = post.get('relevance_score', 0.0)
            
            content_preview = content[:200] + "..." if len(content) > 200 else content
            
            lines.extend([
                f"--- Post {i} ---",
                f"Source: {source}",
                f"Auteur: {author}",
                f"Date: {created_at}",
                f"Sentiment: {sentiment_label}",
                f"Pertinence: {relevance_score:.2%}",
                f"Contenu: {content_preview}",
                f"URL: {url}",
                "",
            ])
        
        lines.append("Accéder au dashboard: http://localhost:8000/dashboard")
        
        return "\n".join(lines)
    
    def test_connection(self) -> tuple[bool, Optional[str]]:
        """
        Test SMTP connection and authentication.
        
        Returns:
            (success: bool, error_message: Optional[str])
        """
        if not self.enabled:
            return False, "SMTP not configured"
        
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
            return True, None
        except Exception as e:
            error_msg = f"SMTP test failed: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

