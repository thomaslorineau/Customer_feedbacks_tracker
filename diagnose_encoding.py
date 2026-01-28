"""Diagnostic script to identify problematic characters at positions 11-14"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

def diagnose_encoding():
    """Diagnose encoding issues in OVH API key and endpoint"""
    from app.database import pg_get_config
    
    # Get OVH configuration
    ovh_key = pg_get_config('OVH_API_KEY')
    ovh_endpoint = pg_get_config('OVH_ENDPOINT_URL')
    
    # Normalize empty strings
    if ovh_key == '':
        ovh_key = None
    if ovh_endpoint == '':
        ovh_endpoint = None
    
    # Use default endpoint if not configured
    if not ovh_endpoint:
        ovh_endpoint = 'https://oai.endpoints.kepler.ai.cloud.ovh.net/v1'
    
    print("=" * 80)
    print("DIAGNOSTIC D'ENCODAGE - Caractères problématiques")
    print("=" * 80)
    print()
    
    # Test API Key
    if ovh_key:
        print(f"[API KEY] Longueur: {len(ovh_key)} caractères")
        print(f"[API KEY] Premiers 20 caractères (repr): {repr(ovh_key[:20])}")
        print(f"[API KEY] Premiers 20 caractères (affichage): {ovh_key[:20]}")
        print()
        
        # Check each character around positions 11-14
        print("[API KEY] Analyse des caractères aux positions 11-14:")
        for i in range(max(0, 8), min(len(ovh_key), 20)):
            char = ovh_key[i]
            char_code = ord(char)
            is_ascii = char_code < 128
            try:
                ascii_test = char.encode('ascii')
                ascii_ok = True
            except UnicodeEncodeError:
                ascii_ok = False
            
            marker = " <-- PROBLÉMATIQUE" if not ascii_ok else ""
            print(f"  Position {i:2d}: '{char}' (code: {char_code:3d}, ASCII: {is_ascii}, encode ASCII: {ascii_ok}){marker}")
        
        print()
        
        # Test "Bearer " + API key
        bearer_key = f'Bearer {ovh_key}'
        print(f"[HEADER Authorization] Longueur: {len(bearer_key)} caractères")
        print(f"[HEADER Authorization] Premiers 30 caractères (repr): {repr(bearer_key[:30])}")
        print()
        
        print("[HEADER Authorization] Analyse des caractères aux positions 11-14:")
        for i in range(max(0, 8), min(len(bearer_key), 20)):
            char = bearer_key[i]
            char_code = ord(char)
            is_ascii = char_code < 128
            try:
                ascii_test = char.encode('ascii')
                ascii_ok = True
            except UnicodeEncodeError:
                ascii_ok = False
            
            marker = " <-- PROBLÉMATIQUE" if not ascii_ok else ""
            print(f"  Position {i:2d}: '{char}' (code: {char_code:3d}, ASCII: {is_ascii}, encode ASCII: {ascii_ok}){marker}")
        
        print()
        
        # Test encoding of the full header
        print("[TEST] Encodage ASCII du header complet:")
        try:
            bearer_key.encode('ascii')
            print("  [OK] Le header peut etre encode en ASCII")
        except UnicodeEncodeError as e:
            print(f"  [ERROR] ERREUR: {e}")
            print(f"  Position problematique: {e.start}-{e.end}")
            if e.start is not None and e.end is not None:
                problematic_chars = bearer_key[e.start:e.end]
                print(f"  Caracteres problematiques: {repr(problematic_chars)}")
                print(f"  Codes Unicode: {[ord(c) for c in problematic_chars]}")
                print(f"  Caracteres en hex: {[hex(ord(c)) for c in problematic_chars]}")
        
        print()
    
    # Test Endpoint
    if ovh_endpoint:
        print(f"[ENDPOINT] Longueur: {len(ovh_endpoint)} caractères")
        print(f"[ENDPOINT] Valeur: {ovh_endpoint}")
        print()
        
        print("[ENDPOINT] Analyse des caractères aux positions 11-14:")
        for i in range(max(0, 8), min(len(ovh_endpoint), 20)):
            char = ovh_endpoint[i]
            char_code = ord(char)
            is_ascii = char_code < 128
            try:
                ascii_test = char.encode('ascii')
                ascii_ok = True
            except UnicodeEncodeError:
                ascii_ok = False
            
            marker = " <-- PROBLÉMATIQUE" if not ascii_ok else ""
            print(f"  Position {i:2d}: '{char}' (code: {char_code:3d}, ASCII: {is_ascii}, encode ASCII: {ascii_ok}){marker}")
        
        print()
        
        # Test encoding of endpoint URL
        print("[TEST] Encodage ASCII de l'endpoint URL:")
        try:
            ovh_endpoint.encode('ascii')
            print("  [OK] L'endpoint peut etre encode en ASCII")
        except UnicodeEncodeError as e:
            print(f"  ❌ ERREUR: {e}")
            print(f"  Position problématique: {e.start}-{e.end}")
            if e.start is not None and e.end is not None:
                problematic_chars = ovh_endpoint[e.start:e.end]
                print(f"  Caractères problématiques: {repr(problematic_chars)}")
                print(f"  Codes Unicode: {[ord(c) for c in problematic_chars]}")
        
        print()
    
    # Test full URL
    if ovh_endpoint:
        full_url = f'{ovh_endpoint}/models'
        print(f"[URL COMPLÈTE] {full_url}")
        try:
            full_url.encode('ascii')
            print("  [OK] L'URL peut etre encodee en ASCII")
        except UnicodeEncodeError as e:
            print(f"  ❌ ERREUR: {e}")
            print(f"  Position problématique: {e.start}-{e.end}")
            if e.start is not None and e.end is not None:
                problematic_chars = full_url[e.start:e.end]
                print(f"  Caractères problématiques: {repr(problematic_chars)}")
                print(f"  Codes Unicode: {[ord(c) for c in problematic_chars]}")
        
        print()
    
    print("=" * 80)
    print("RÉSUMÉ")
    print("=" * 80)
    if ovh_key:
        try:
            f'Bearer {ovh_key}'.encode('ascii')
            print("[OK] Header Authorization: OK")
        except UnicodeEncodeError as e:
            print(f"[ERROR] Header Authorization: ERREUR aux positions {e.start}-{e.end}")
    if ovh_endpoint:
        try:
            ovh_endpoint.encode('ascii')
            print("[OK] Endpoint URL: OK")
        except UnicodeEncodeError as e:
            print(f"[ERROR] Endpoint URL: ERREUR aux positions {e.start}-{e.end}")

if __name__ == "__main__":
    diagnose_encoding()
