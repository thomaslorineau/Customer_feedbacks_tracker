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
            from ..database import pg_get_config
            import os
            
            # Récupérer depuis la base de données en priorité, puis env
            self._bot_token = pg_get_config('DISCORD_BOT_TOKEN') or os.getenv('DISCORD_BOT_TOKEN')
            self._guild_id = pg_get_config('DISCORD_GUILD_ID') or os.getenv('DISCORD_GUILD_ID')
            self._config = True  # Mark as loaded
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
        # Normalize query: if empty, use empty string (will match all messages)
        query = query.strip() if query else ""
        self.logger.log_scraping_start(query or "(all messages)", limit)
        
        if not self.bot_token:
            self.logger.log("warning", "Discord bot token not configured. Set DISCORD_BOT_TOKEN in .env")
            return []
        
        if not self.guild_id:
            self.logger.log("warning", "Discord guild ID not configured. Set DISCORD_GUILD_ID in .env")
            return []
        
        logger.info(f"[Discord] Starting scrape with bot_token length: {len(self.bot_token) if self.bot_token else 0}, guild_id: {self.guild_id}")
        
        try:
            messages = await self._search_messages(query, limit)
            
            if messages:
                duration = time.time() - start_time
                self.logger.log_scraping_success(len(messages), duration)
                logger.info(f"[Discord] Successfully scraped {len(messages)} messages")
                return messages
            else:
                duration = time.time() - start_time
                self.logger.log("warning", f"No messages found for query: {query or '(all messages)'}", duration=duration)
                logger.warning(f"[Discord] No messages found. Query: '{query or '(all messages)'}', Guild ID: {self.guild_id}")
                return []
        
        except Exception as e:
            duration = time.time() - start_time
            self.logger.log_scraping_error(e, duration)
            logger.error(f"[Discord] Error during scraping: {type(e).__name__}: {e}", exc_info=True)
            return []
    
    async def _search_messages(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Search messages in Discord guild channels."""
        all_messages = []
        seen_message_ids = set()
        
        logger.info(f"[Discord] _search_messages called with query='{query}', limit={limit}")
        
        # Get all channels in the guild
        channels = await self._get_guild_channels()
        if not channels:
            self.logger.log("warning", "No channels found in Discord guild")
            logger.warning(f"[Discord] No channels found in guild {self.guild_id}")
            return []
        
        logger.info(f"[Discord] 🔍 Searching in {len(channels)} channels")
        
        if not channels:
            logger.warning(f"[Discord] ⚠️ No channels found in guild {self.guild_id}")
            return []
        
        # Search in each channel
        for idx, channel in enumerate(channels):
            if len(all_messages) >= limit:
                logger.info(f"[Discord] Reached limit of {limit} messages, stopping")
                break
            
            channel_id = channel.get('id')
            channel_name = channel.get('name', 'unknown')
            
            logger.info(f"[Discord] Searching channel {idx+1}/{len(channels)}: {channel_name} (ID: {channel_id})")
            
            try:
                # Search messages in this channel
                messages = await self._search_channel_messages(channel_id, query, limit - len(all_messages))
                
                logger.info(f"[Discord] ✅ Channel {channel_name} (ID: {channel_id}): found {len(messages)} matching messages")
                
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
                error_msg = f"Error searching channel {channel_name}: {type(e).__name__}: {e}"
                self.logger.log("warning", error_msg)
                logger.warning(f"[Discord] {error_msg}", exc_info=True)
                continue
        
        logger.info(f"[Discord] 📊 Total messages collected: {len(all_messages)} (limit: {limit})")
        
        if len(all_messages) == 0:
            logger.warning(f"[Discord] ⚠️ No messages found! Query: '{query or '(all)'}', Channels searched: {len(channels)}")
            # Log channel details for debugging
            for ch in channels[:5]:
                logger.info(f"[Discord]   - Channel: {ch.get('name', 'unknown')} (ID: {ch.get('id')}, Type: {ch.get('type')})")
        
        return all_messages[:limit]
    
    async def _get_guild_channels(self) -> List[Dict[str, Any]]:
        """Get all channels in the Discord guild."""
        url = f"https://discord.com/api/v10/guilds/{self.guild_id}/channels"
        # Ensure token doesn't already have "Bot " prefix
        token = self.bot_token.strip()
        if token.startswith("Bot "):
            token = token[4:].strip()
        headers = {
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
            "User-Agent": "OVH-Tracker-Bot/1.0"
        }
        
        try:
            logger.info(f"[Discord] Fetching channels for guild {self.guild_id}")
            response = await self._fetch_get(url, headers=headers)
            response.raise_for_status()
            channels = response.json()
            
            logger.info(f"[Discord] Received {len(channels)} total channels from API")
            
            # Filter to only text channels (type 0)
            text_channels = [ch for ch in channels if ch.get('type') == 0]
            logger.info(f"[Discord] Found {len(text_channels)} text channels (type 0) out of {len(channels)} total channels")
            
            if text_channels:
                channel_names = [ch.get('name', 'unknown') for ch in text_channels[:5]]
                logger.info(f"[Discord] Sample channel names: {channel_names}")
            
            self.logger.log("info", f"Found {len(text_channels)} text channels in guild")
            return text_channels
        
        except Exception as e:
            error_msg = f"Failed to get guild channels: {type(e).__name__}: {e}"
            self.logger.log("error", error_msg)
            logger.error(f"[Discord] {error_msg}", exc_info=True)
            if hasattr(e, 'response'):
                logger.error(f"[Discord] Response status: {e.response.status_code if hasattr(e.response, 'status_code') else 'unknown'}")
                logger.error(f"[Discord] Response text: {e.response.text[:500] if hasattr(e.response, 'text') else 'N/A'}")
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
            # Ensure token doesn't already have "Bot " prefix
            token = self.bot_token.strip()
            if token.startswith("Bot "):
                token = token[4:].strip()
            headers = {
                "Authorization": f"Bot {token}",
                "Content-Type": "application/json",
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
                    logger.warning(f"[Discord] Rate limited on channel {channel_id}, waiting {retry_after}s")
                    await asyncio.sleep(retry_after)
                    continue
                
                response.raise_for_status()
                messages = response.json()
                
                logger.info(f"[Discord] ✅ Fetched {len(messages)} raw messages from channel {channel_id} (status: {response.status_code})")
                
                if not messages:
                    logger.info(f"[Discord] ⚠️ No more messages in channel {channel_id}, stopping pagination")
                    break
                
                # Filter messages that contain the query (if query is provided)
                # If query is empty, include all messages
                query_lower = query.lower() if query else None
                total_fetched = len(messages)
                matching_count = 0
                
                logger.info(f"[Discord] 🔍 Filtering {total_fetched} messages with query='{query or '(all)'}'")
                
                # Log first few message contents for debugging
                if total_fetched > 0:
                    sample_messages = messages[:3]
                    for idx, msg in enumerate(sample_messages):
                        content_preview = msg.get('content', '')[:100]
                        logger.info(f"[Discord] Sample message {idx+1}: content_length={len(msg.get('content', ''))}, preview='{content_preview}...'")
                
                for msg in messages:
                    content = msg.get('content', '')
                    content_lower = content.lower() if content else ''
                    
                    # If query is empty/None, include all messages; otherwise filter by query
                    # Also include messages with empty content if query is empty (they might have embeds/attachments)
                    should_include = False
                    if query_lower is None or query == "":
                        # Include all messages when query is empty
                        should_include = True
                    elif content_lower:
                        # Only filter by query if message has content
                        should_include = query_lower in content_lower
                    else:
                        # Message has no content and query is not empty - skip it
                        logger.debug(f"[Discord] Skipping message with no content (query='{query}')")
                        should_include = False
                    
                    if should_include:
                        matching_count += 1
                        try:
                            # Parse message
                            author = msg.get('author', {})
                            if not author:
                                logger.warning(f"[Discord] Message {msg.get('id', 'unknown')} has no author, skipping")
                                continue
                            
                            author_name = author.get('username', 'unknown')
                            author_discriminator = author.get('discriminator', '')
                            if author_discriminator and author_discriminator != '0':
                                author_display = f"{author_name}#{author_discriminator}"
                            else:
                                author_display = author_name
                            
                            # Use content or fallback to a placeholder if empty
                            content_text = content if content else "[Message sans contenu texte]"
                            
                            # Check for embeds or attachments
                            embeds = msg.get('embeds', [])
                            attachments = msg.get('attachments', [])
                            if not content_text and (embeds or attachments):
                                content_text = f"[Message avec {len(embeds)} embed(s) et {len(attachments)} pièce(s) jointe(s)]"
                            
                            message_id = msg.get('id')
                            if not message_id:
                                logger.warning(f"[Discord] Message has no ID, skipping")
                                continue
                            
                            channel_id_from_msg = msg.get('channel_id', channel_id)
                            
                            # Parse timestamp
                            timestamp = msg.get('timestamp')
                            if timestamp:
                                # Discord timestamps are ISO 8601 strings
                                try:
                                    created_at = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).isoformat()
                                except Exception as e:
                                    logger.warning(f"[Discord] Failed to parse timestamp '{timestamp}': {e}")
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
                            logger.debug(f"[Discord] ✅ Added message: {author_display} - {content_text[:50]}...")
                        except Exception as e:
                            logger.error(f"[Discord] ❌ Error parsing Discord message: {e}", exc_info=True)
                            self.logger.log("warning", f"Error parsing Discord message: {e}")
                            continue
                    else:
                        logger.debug(f"[Discord] ⏭️ Message filtered out (query='{query}' not in content)")
                    
                    # Update before_id for pagination
                    before_id = msg.get('id')
                
                logger.info(f"[Discord] Channel {channel_id}: {matching_count}/{total_fetched} messages matched query '{query or '(all)'}' (total collected in this channel: {len(all_messages)})")
                
                # If we got fewer messages than requested, we've reached the end
                if len(messages) < params["limit"]:
                    logger.debug(f"[Discord] Reached end of channel {channel_id} (got {len(messages)} < {params['limit']} requested)")
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

