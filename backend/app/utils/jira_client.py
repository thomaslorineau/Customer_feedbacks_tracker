"""Jira API client for creating tickets."""
import os
import logging
import httpx
from typing import Optional, Dict, Any
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


def load_jira_config() -> Dict[str, Optional[str]]:
    """Load Jira configuration from environment variables."""
    # Reload .env to get latest values
    backend_path = Path(__file__).resolve().parents[2]
    env_path = backend_path / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=True)
    
    return {
        'server_url': os.getenv('JIRA_SERVER_URL', '').rstrip('/'),
        'username': os.getenv('JIRA_USERNAME', ''),
        'api_token': os.getenv('JIRA_API_TOKEN', ''),
        'project_key': os.getenv('JIRA_PROJECT_KEY', ''),
    }


def is_jira_configured() -> bool:
    """Check if Jira is properly configured."""
    config = load_jira_config()
    return all([
        config['server_url'],
        config['username'],
        config['api_token'],
        config['project_key']
    ])


async def create_jira_ticket(
    title: str,
    description: str,
    issue_type: str = 'Bug',
    priority: str = 'Medium',
    labels: Optional[list] = None
) -> Dict[str, Any]:
    """
    Create a Jira ticket.
    
    Args:
        title: Ticket title/summary
        description: Ticket description
        issue_type: Issue type (Bug, Task, Story, etc.)
        priority: Priority level (Lowest, Low, Medium, High, Highest)
        labels: Optional list of labels
    
    Returns:
        Dict with 'success', 'ticket_key', 'ticket_url', and optional 'error'
    """
    config = load_jira_config()
    
    if not is_jira_configured():
        return {
            'success': False,
            'error': 'Jira is not configured. Please configure Jira settings in Settings page.'
        }
    
    # Prepare authentication (Basic Auth with API token)
    auth = (config['username'], config['api_token'])
    base_url = config['server_url']
    project_key = config['project_key']
    
    # Build ticket payload
    payload = {
        'fields': {
            'project': {
                'key': project_key
            },
            'summary': title,
            'description': {
                'type': 'doc',
                'version': 1,
                'content': [
                    {
                        'type': 'paragraph',
                        'content': [
                            {
                                'type': 'text',
                                'text': description
                            }
                        ]
                    }
                ]
            },
            'issuetype': {
                'name': issue_type
            },
            'priority': {
                'name': priority
            }
        }
    }
    
    # Add labels if provided
    if labels:
        payload['fields']['labels'] = labels
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Create ticket
            response = await client.post(
                f'{base_url}/rest/api/3/issue',
                auth=auth,
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                json=payload
            )
            
            if response.status_code == 201:
                result = response.json()
                ticket_key = result.get('key', '')
                ticket_url = f'{base_url}/browse/{ticket_key}'
                
                logger.info(f"Jira ticket created successfully: {ticket_key}")
                return {
                    'success': True,
                    'ticket_key': ticket_key,
                    'ticket_url': ticket_url
                }
            else:
                error_text = response.text
                logger.error(f"Failed to create Jira ticket: {response.status_code} - {error_text}")
                return {
                    'success': False,
                    'error': f'Failed to create ticket: {response.status_code} - {error_text[:200]}'
                }
    
    except httpx.TimeoutException:
        logger.error("Jira API timeout")
        return {
            'success': False,
            'error': 'Request timeout. Please check your Jira server URL and try again.'
        }
    except httpx.ConnectError:
        logger.error("Jira connection error")
        return {
            'success': False,
            'error': 'Could not connect to Jira server. Please check your server URL.'
        }
    except Exception as e:
        logger.error(f"Error creating Jira ticket: {type(e).__name__}: {e}", exc_info=True)
        return {
            'success': False,
            'error': f'Unexpected error: {str(e)}'
        }


async def test_jira_connection() -> Dict[str, Any]:
    """Test Jira connection and authentication."""
    config = load_jira_config()
    
    if not is_jira_configured():
        return {
            'success': False,
            'error': 'Jira is not configured. Please fill all required fields.'
        }
    
    auth = (config['username'], config['api_token'])
    base_url = config['server_url']
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Test connection by getting current user
            response = await client.get(
                f'{base_url}/rest/api/3/myself',
                auth=auth,
                headers={'Accept': 'application/json'}
            )
            
            if response.status_code == 200:
                user_info = response.json()
                return {
                    'success': True,
                    'message': f'Connected as {user_info.get("displayName", config["username"])}'
                }
            else:
                return {
                    'success': False,
                    'error': f'Authentication failed: {response.status_code} - {response.text[:200]}'
                }
    
    except httpx.TimeoutException:
        return {
            'success': False,
            'error': 'Connection timeout. Please check your server URL.'
        }
    except httpx.ConnectError:
        return {
            'success': False,
            'error': 'Could not connect to Jira server. Please check your server URL.'
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Error: {str(e)}'
        }

