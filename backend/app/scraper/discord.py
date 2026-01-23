"""Discord scraper for OVH-related messages."""
from datetime import datetime
import asyncio
import logging
import time
from typing import List, Dict, Any, Optional
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class DiscordScraper(BaseScraper):
    """Async Discord scraper using Discord API."""
    
    def __init__(self):
        super().__init__("Discord")
        # Delay config import to avoid circular dependencies
        # Import will happen lazily when needed
        self._config = None
        self._bot_token = None
        self._guild_id = None
    
    def _get_config(self):
        """Lazy load config to avoid import issues."""
        if self._config is None:
            # Use relative import like other scrapers
            from ..config import config
            self._config = config
            self._bot_token = config.get_api_key("discord")
            self._guild_id = config.discord_guild_id
        return self._config
    
    @property
    def bot_token(self):
        if self._bot_token is None:
            self._get_config()
        return self._bot_token
    
    @property
    def guild_id(self):
        if self._guild_id is None:
            self._get_config()
        return self._guild_id
    
    async def scrape(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Scrape Discord messages matching the query."""
        start_time = time.time()
        self.logger.log_scraping_start(query, limit)
        
        if not self.bot_token:
            self.logger.log("warning", "Discord bot token not configured. Set DISCORD_BOT_TOKEN in .env")
            return []
        
        if not self.guild_id:
            self.logger.log("warning", "Discord guild ID not configured. Set DISCORD_GUILD_ID in .env")
            return []
        
        try:
            messages = await self._search_messages(query, limit)
            
            if messages:
                duration = time.time() - start_time
                self.logger.log_scraping_success(len(messages), duration)
                return messages
            else:
                duration = time.time() - start_time
                self.logger.log("warning", f"No messages found for query: {query}", duration=duration)
                return []
        
        except Exception as e:
            duration = time.time() - start_time
            self.logger.log_scraping_error(e, duration)
            return []
    
    async def _search_messages(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Search messages in Discord guild channels."""
        all_messages = []
        seen_message_ids = set()
        
        # Get all channels in the guild
        channels = await self._get_guild_channels()
        if not channels:
            self.logger.log("warning", "No channels found in Discord guild")
            return []
        
        # Search in each channel
        for channel in channels:
            if len(all_messages) >= limit:
                break
            
            channel_id = channel.get('id')
            channel_name = channel.get('name', 'unknown')
            
            try:
                # Search messages in this channel
                messages = await self._search_channel_messages(channel_id, query, limit - len(all_messages))
                
                for msg in messages:
                    msg_id = msg.get('id')
                    if msg_id and msg_id not in seen_message_ids:
                        seen_message_ids.add(msg_id)
                        all_messages.append(msg)
                    
                    if len(all_messages) >= limit:
                        break
                
                # Small delay between channels to respect rate limits
                await asyncio.sleep(0.5)
            
            except Exception as e:
                self.logger.log("warning", f"Error searching channel {channel_name}: {e}")
                continue
        
        return all_messages[:limit]
    
    async def _get_guild_channels(self) -> List[Dict[str, Any]]:
        """Get all channels in the Discord guild."""
        url = f"https://discord.com/api/v10/guilds/{self.guild_id}/channels"
        headers = {
            "Authorization": f"Bot {self.bot_token}",
            "User-Agent": "OVH-Tracker-Bot/1.0"
        }
        
        try:
            response = await self._fetch_get(url, headers=headers)
            response.raise_for_status()
            channels = response.json()
            
            # Filter to only text channels (type 0)
            text_channels = [ch for ch in channels if ch.get('type') == 0]
            self.logger.log("info", f"Found {len(text_channels)} text channels in guild")
            return text_channels
        
        except Exception as e:
            self.logger.log("error", f"Failed to get guild channels: {e}")
            return []
    
    async def _search_channel_messages(
        self, 
        channel_id: str, 
        query: str, 
        limit: int
    ) -> List[Dict[str, Any]]:
        """Search messages in a specific channel."""
        all_messages = []
        before_id = None
        
        # Discord API allows fetching up to 100 messages per request
        while len(all_messages) < limit:
            url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
            headers = {
                "Authorization": f"Bot {self.bot_token}",
                "User-Agent": "OVH-Tracker-Bot/1.0"
            }
            
            params = {"limit": min(100, limit - len(all_messages))}
            if before_id:
                params["before"] = before_id
            
            try:
                response = await self._fetch_get(url, headers=headers, params=params)
                
                if response.status_code == 429:
                    # Rate limited - wait and retry
                    retry_after = float(response.headers.get("Retry-After", 1))
                    self.logger.log("warning", f"Rate limited, waiting {retry_after}s")
                    await asyncio.sleep(retry_after)
                    continue
                
                response.raise_for_status()
                messages = response.json()
                
                if not messages:
                    break
                
                # Filter messages that contain the query
                for msg in messages:
                    content = msg.get('content', '').lower()
                    if query.lower() in content:
                        try:
                            # Parse message
                            author = msg.get('author', {})
                            author_name = author.get('username', 'unknown')
                            author_discriminator = author.get('discriminator', '')
                            if author_discriminator and author_discriminator != '0':
                                author_display = f"{author_name}#{author_discriminator}"
                            else:
                                author_display = author_name
                            
                            content_text = msg.get('content', '')
                            message_id = msg.get('id')
                            channel_id_from_msg = msg.get('channel_id', channel_id)
                            
                            # Parse timestamp
                            timestamp = msg.get('timestamp')
                            if timestamp:
                                # Discord timestamps are ISO 8601 strings
                                try:
                                    created_at = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).isoformat()
                                except:
                                    created_at = datetime.now().isoformat()
                            else:
                                created_at = datetime.now().isoformat()
                            
                            # Build message URL
                            guild_id = msg.get('guild_id', self.guild_id)
                            message_url = f"https://discord.com/channels/{guild_id}/{channel_id_from_msg}/{message_id}"
                            
                            post = {
                                'source': 'Discord',
                                'author': author_display,
                                'content': content_text[:500],
                                'url': message_url,
                                'created_at': created_at,
                                'sentiment_score': 0.0,
                                'sentiment_label': 'neutral',
                            }
                            all_messages.append(post)
                        except Exception as e:
                            self.logger.log("warning", f"Error parsing Discord message: {e}")
                            continue
                    
                    # Update before_id for pagination
                    before_id = msg.get('id')
                
                # If we got fewer messages than requested, we've reached the end
                if len(messages) < params["limit"]:
                    break
                
                # Rate limit: Discord allows 50 requests per second per bot
                await asyncio.sleep(0.02)  # ~50 requests/second
            
            except Exception as e:
                self.logger.log("warning", f"Error fetching messages from channel {channel_id}: {e}")
                break
        
        return all_messages


# Global scraper instance - lazy initialization
_async_scraper = None

def _get_scraper():
    """Get or create the global scraper instance."""
    global _async_scraper
    if _async_scraper is None:
        _async_scraper = DiscordScraper()
    return _async_scraper


async def scrape_discord_async(query: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Async entry point for Discord scraper."""
    scraper = _get_scraper()
    return await scraper.scrape(query, limit)


def scrape_discord(query: str, limit: int = 50):
    """Synchronous wrapper for async scraper (for backward compatibility)."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return asyncio.run(scrape_discord_async(query, limit))
        else:
            return loop.run_until_complete(scrape_discord_async(query, limit))
    except RuntimeError:
        return asyncio.run(scrape_discord_async(query, limit))

