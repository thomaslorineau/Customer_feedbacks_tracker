#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test Discord scraper directly."""
import sys
import io
import asyncio

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

async def test_discord():
    """Test Discord scraper."""
    try:
        from app.scraper import discord
        from app.database import pg_get_config
        
        print("=== TEST DU SCRAPER DISCORD ===\n")
        
        # Check configuration
        bot_token = pg_get_config('DISCORD_BOT_TOKEN')
        guild_id = pg_get_config('DISCORD_GUILD_ID')
        
        print(f"Bot Token: {'Configure' if bot_token else 'NON CONFIGURE'} (length: {len(bot_token) if bot_token else 0})")
        print(f"Guild ID: {'Configure' if guild_id else 'NON CONFIGURE'} (value: {guild_id})")
        
        if not bot_token:
            print("\nERREUR: Bot token non configure!")
            return
        
        if not guild_id:
            print("\nERREUR: Guild ID non configure!")
            return
        
        print("\n=== LANCEMENT DU SCRAPING ===")
        print("Query: '' (vide, devrait recuperer tous les messages)")
        print("Limit: 10\n")
        
        # Test scraping
        messages = await discord.scrape_discord_async("", limit=10)
        
        print(f"\n=== RESULTAT ===")
        print(f"Messages trouves: {len(messages)}")
        
        if messages:
            print("\nPremiers messages:")
            for i, msg in enumerate(messages[:5], 1):
                print(f"{i}. [{msg.get('author', 'N/A')}] {msg.get('content', '')[:100]}")
        else:
            print("\nAucun message trouve.")
            print("Causes possibles:")
            print("  - Aucun message dans les channels")
            print("  - Le bot n'a pas acces aux channels")
            print("  - Les channels sont vides")
            print("  - Erreur API Discord (verifiez les logs ci-dessus)")
        
    except Exception as e:
        print(f"\nERREUR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_discord())
