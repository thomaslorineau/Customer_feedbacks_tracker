#!/usr/bin/env python3
"""
Script pour nettoyer la clé API OVH dans la base de données.
Supprime tous les caractères non-ASCII qui pourraient causer des problèmes d'encodage.
"""
import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_path))

def clean_ovh_api_key(value: str) -> str:
    """
    Clean OVH API key to ensure it only contains ASCII-safe characters.
    JWT tokens should only contain: A-Z, a-z, 0-9, +, /, =, -, _, .
    """
    if not value:
        return value
    # Keep only ASCII characters that are valid in JWT/base64
    cleaned = ''.join(c for c in value if ord(c) < 128 and (c.isalnum() or c in '+-/=_.'))
    return cleaned

def main():
    """Clean OVH API key in database."""
    from app.database import pg_get_config, pg_set_config
    
    print("🔍 Récupération de la clé OVH depuis la base de données...")
    ovh_key = pg_get_config('OVH_API_KEY')
    
    if not ovh_key:
        print("❌ Aucune clé OVH trouvée dans la base de données.")
        return
    
    print(f"📋 Clé actuelle: longueur={len(ovh_key)}")
    print(f"   Début: {ovh_key[:20]}...")
    print(f"   Fin: ...{ovh_key[-20:]}")
    
    # Check for non-ASCII characters
    non_ascii_chars = [c for c in ovh_key if ord(c) >= 128]
    if non_ascii_chars:
        print(f"⚠️  Caractères non-ASCII détectés: {len(non_ascii_chars)} caractères")
        print(f"   Positions: {[i for i, c in enumerate(ovh_key) if ord(c) >= 128][:10]}")
    else:
        print("✅ Aucun caractère non-ASCII détecté")
    
    # Clean the key
    cleaned_key = clean_ovh_api_key(ovh_key)
    
    if cleaned_key != ovh_key:
        print(f"\n🧹 Nettoyage nécessaire:")
        print(f"   Avant: {len(ovh_key)} caractères")
        print(f"   Après: {len(cleaned_key)} caractères")
        
        if cleaned_key:
            print(f"\n💾 Sauvegarde de la clé nettoyée...")
            pg_set_config('OVH_API_KEY', cleaned_key)
            print("✅ Clé nettoyée et sauvegardée avec succès!")
            print(f"   Nouvelle clé: {cleaned_key[:20]}...{cleaned_key[-20:]}")
        else:
            print("❌ La clé nettoyée est vide - aucune sauvegarde effectuée")
    else:
        print("\n✅ La clé est déjà propre, aucune action nécessaire")

if __name__ == "__main__":
    main()
