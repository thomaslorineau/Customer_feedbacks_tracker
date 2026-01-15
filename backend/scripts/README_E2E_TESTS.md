# Tests E2E - Documentation

## Scripts disponibles

### `e2e_full_test.py` ⭐ **RECOMMANDÉ**
Suite complète de tests E2E (12 tests).

**Usage:**
```bash
python backend/scripts/e2e_full_test.py
```

**Tests inclus:**
- Health check
- API endpoints
- Scrapers (Reddit, Stack Overflow)
- Pages frontend
- Logs
- Configuration
- Sécurité

### `e2e_test_real_server.py`
Test basique de démarrage serveur et jobs.

**Usage:**
```bash
python backend/scripts/e2e_test_real_server.py
```

### `ci_test_endpoints.py`
Tests d'endpoints pour CI/CD (utilise TestClient).

**Usage:**
```bash
python backend/scripts/ci_test_endpoints.py
```

---

## Recommandation

**Utiliser `e2e_full_test.py`** pour une validation complète avant la démo.


