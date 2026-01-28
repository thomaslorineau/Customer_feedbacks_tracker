#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Script to analyze Discord scraping logs."""
import sys
import io
import requests
import json
from datetime import datetime

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

try:
    # Get Discord logs from API
    response = requests.get('http://localhost:8000/api/logs?source=Discord&limit=100')
    response.raise_for_status()
    data = response.json()
    logs = data.get('logs', [])
    
    print(f"\n=== ANALYSE DES LOGS DISCORD ({len(logs)} logs trouvés) ===\n")
    
    if not logs:
        print("❌ Aucun log Discord trouvé dans la base de données.")
        print("   Cela peut signifier que le scraping n'a pas été exécuté ou qu'il y a eu une erreur avant les logs.")
        exit(1)
    
    # Categorize logs
    errors = [log for log in logs if log.get('level') in ['error', 'Error']]
    warnings = [log for log in logs if log.get('level') in ['warning', 'Warning']]
    infos = [log for log in logs if log.get('level') in ['info', 'Info', 'success', 'Success']]
    
    print(f"📊 Statistiques:")
    print(f"   - Errors: {len(errors)}")
    print(f"   - Warnings: {len(warnings)}")
    print(f"   - Info/Success: {len(infos)}")
    
    # Show recent logs
    print(f"\n=== DERNIERS LOGS (20 plus récents) ===")
    for i, log in enumerate(logs[:20], 1):
        timestamp = log.get('timestamp', 'N/A')
        if isinstance(timestamp, str) and len(timestamp) > 19:
            timestamp = timestamp[:19]
        level = log.get('level', 'N/A')
        message = log.get('message', 'N/A')
        if len(message) > 200:
            message = message[:200] + "..."
        print(f"{i:2}. {timestamp} [{level:8}] {message}")
    
    # Show errors if any
    if errors:
        print(f"\n=== ERREURS TROUVÉES ({len(errors)}) ===")
        for i, log in enumerate(errors[:10], 1):
            timestamp = log.get('timestamp', 'N/A')
            if isinstance(timestamp, str) and len(timestamp) > 19:
                timestamp = timestamp[:19]
            message = log.get('message', 'N/A')
            print(f"{i}. {timestamp}: {message}")
    
    # Show warnings if any
    if warnings:
        print(f"\n=== AVERTISSEMENTS ({len(warnings)}) ===")
        for i, log in enumerate(warnings[:10], 1):
            timestamp = log.get('timestamp', 'N/A')
            if isinstance(timestamp, str) and len(timestamp) > 19:
                timestamp = timestamp[:19]
            message = log.get('message', 'N/A')
            print(f"{i}. {timestamp}: {message}")
    
    # Analyze patterns
    print(f"\n=== ANALYSE DES PATTERNS ===")
    
    # Check for common issues
    no_channels = [log for log in logs if 'No channels found' in log.get('message', '')]
    no_messages = [log for log in logs if 'No messages found' in log.get('message', '')]
    token_issues = [log for log in logs if 'token' in log.get('message', '').lower() or 'DISCORD_BOT_TOKEN' in log.get('message', '')]
    guild_issues = [log for log in logs if 'guild' in log.get('message', '').lower() or 'DISCORD_GUILD_ID' in log.get('message', '')]
    api_errors = [log for log in logs if 'API' in log.get('message', '') or '401' in log.get('message', '') or '403' in log.get('message', '') or '404' in log.get('message', '')]
    
    if no_channels:
        print(f"⚠️  {len(no_channels)} log(s) indiquant qu'aucun channel n'a été trouvé")
        print(f"   Dernier: {no_channels[0].get('message', 'N/A')}")
    
    if no_messages:
        print(f"⚠️  {len(no_messages)} log(s) indiquant qu'aucun message n'a été trouvé")
        print(f"   Dernier: {no_messages[0].get('message', 'N/A')}")
    
    if token_issues:
        print(f"🔑 {len(token_issues)} log(s) liés au token")
        for log in token_issues[:3]:
            print(f"   - {log.get('message', 'N/A')[:100]}")
    
    if guild_issues:
        print(f"🏰 {len(guild_issues)} log(s) liés au guild ID")
        for log in guild_issues[:3]:
            print(f"   - {log.get('message', 'N/A')[:100]}")
    
    if api_errors:
        print(f"❌ {len(api_errors)} log(s) d'erreurs API")
        for log in api_errors[:5]:
            print(f"   - {log.get('message', 'N/A')[:150]}")
    
    # Check for successful scraping
    success_logs = [log for log in logs if 'successfully scraped' in log.get('message', '').lower() or 'scraping success' in log.get('message', '').lower()]
    if success_logs:
        print(f"\n✅ {len(success_logs)} log(s) de succès trouvé(s)")
        for log in success_logs[:3]:
            print(f"   - {log.get('message', 'N/A')}")
    else:
        print(f"\n❌ Aucun log de succès trouvé - le scraping n'a probablement pas fonctionné")
    
except requests.exceptions.ConnectionError:
    print("❌ Erreur: Impossible de se connecter au serveur sur http://localhost:8000")
    print("   Assurez-vous que le serveur est démarré.")
except Exception as e:
    print(f"❌ Erreur lors de l'analyse: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
