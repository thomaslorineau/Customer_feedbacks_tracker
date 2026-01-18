# 🚨 ACTION URGENTE - Clé API OpenAI exposée

## ⚠️ PROBLÈME CRITIQUE

Votre clé API OpenAI était exposée dans le fichier `backend/.env`:
```
OPENAI_API_KEY=sk-proj-hiswPnhfaJO...
```

Cette clé a été **masquée** dans le fichier mais doit être **RÉVOQUÉE IMMÉDIATEMENT** et **REMPLACÉE** car elle a pu être compromise.

---

## 🔥 ÉTAPES À SUIVRE MAINTENANT

### 1. Révoquer la clé compromise

**Ouvrir:** https://platform.openai.com/api-keys

**Se connecter** avec vos identifiants OpenAI

**Localiser la clé:**
- Rechercher une clé commençant par: `sk-proj-hiswPnhf...`
- Elle devrait être dans votre liste de clés API

**Révoquer:**
- Cliquer sur l'icône de suppression (⋮) ou "Revoke"
- Confirmer la suppression

---

### 2. Générer une nouvelle clé

**Sur la même page:** https://platform.openai.com/api-keys

**Créer une nouvelle clé:**
- Cliquer sur "+ Create new secret key"
- Donner un nom descriptif: "OVH Complaints Tracker - Dev"
- (Optionnel) Limiter les permissions si possible

**Copier la clé:**
- ⚠️ **Important:** Copier immédiatement la clé
- Elle ne sera affichée qu'une seule fois!

---

### 3. Mettre à jour le fichier .env

**Ouvrir le fichier:**
```bash
# Windows
notepad backend\.env

# VS Code
code backend\.env
```

**Remplacer la ligne:**
```dotenv
# SECURITY WARNING: This key should be regenerated!
# The previous key was exposed in logs and should be considered compromised.
# Get a new key from: https://platform.openai.com/api-keys
OPENAI_API_KEY=your_openai_api_key_here
```

**Par:**
```dotenv
# OpenAI API Key - Generated on 2026-01-15
OPENAI_API_KEY=sk-proj-VOTRE_NOUVELLE_CLE_ICI
```

**Sauvegarder le fichier**

---

### 4. Vérifier que .env est bien ignoré par Git

**Exécuter:**
```bash
# Vérifier que .env est dans .gitignore
cat .gitignore | grep .env

# Vérifier que .env n'est pas tracké
git status

# Si .env apparaît, l'ajouter à .gitignore:
echo "*.env" >> .gitignore
echo ".env" >> .gitignore
git add .gitignore
git commit -m "Add .env to gitignore"
```

---

### 5. Redémarrer le serveur

```powershell
# Arrêter le serveur actuel (Ctrl+C dans le terminal)

# Redémarrer
.\start_server.ps1
```

---

## ✅ Vérifications

### Vérification 1: La nouvelle clé fonctionne

```bash
# Tester que la clé API est bien chargée
curl http://localhost:8000/posts?limit=1
```

Si la clé est invalide, vous verrez des erreurs dans les logs.

### Vérification 2: .env n'est pas dans Git

```bash
# Vérifier l'historique Git
git log --all --full-history -- "*/.env"

# Résultat attendu: Aucun commit trouvé
```

Si des commits contiennent `.env`, l'historique doit être purgé:
```bash
# ATTENTION: Opération destructive - À faire avec précaution
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch backend/.env" \
  --prune-empty --tag-name-filter cat -- --all

# Forcer le push (si dépôt distant)
git push origin --force --all
```

### Vérification 3: Ancienne clé révoquée

Retourner sur https://platform.openai.com/api-keys et vérifier que:
- ❌ L'ancienne clé (`sk-proj-hiswPnhf...`) n'apparaît plus
- ✅ La nouvelle clé est active

---

## 🔒 Bonnes pratiques pour l'avenir

### 1. Ne jamais commiter de secrets

```bash
# Toujours vérifier avant de commit
git diff --cached

# Si un secret apparaît, le retirer immédiatement
git reset HEAD backend/.env
```

### 2. Utiliser des clés API avec permissions limitées

Sur OpenAI:
- Créer des clés avec des limites de dépenses
- Activer les alertes de facturation
- Utiliser des clés différentes pour dev/staging/prod

### 3. Rotation régulière des clés

- Renouveler les clés tous les 3-6 mois
- Utiliser un gestionnaire de secrets en production (Vault, AWS Secrets Manager)

### 4. Surveillance des clés

- Activer les notifications OpenAI
- Surveiller l'utilisation sur le dashboard
- Réagir immédiatement à toute activité suspecte

---

## 📋 Checklist finale

- [ ] Connecté sur https://platform.openai.com/api-keys
- [ ] Ancienne clé révoquée (`sk-proj-hiswPnhf...`)
- [ ] Nouvelle clé générée
- [ ] Nouvelle clé copiée
- [ ] Fichier `backend/.env` mis à jour
- [ ] `.env` dans `.gitignore`
- [ ] Serveur redémarré
- [ ] Test API réussi
- [ ] Pas de `.env` dans l'historique Git
- [ ] Dashboard OpenAI vérifié

---

## 🆘 En cas de problème

### Problème 1: La nouvelle clé ne fonctionne pas

**Solution:**
- Vérifier que la clé est bien copiée sans espaces
- Vérifier qu'elle commence par `sk-proj-`
- Redémarrer le serveur
- Vérifier les logs: `cat backend/logs/app.log`

### Problème 2: .env est déjà dans Git

**Solution:**
- Voir "Vérification 2" ci-dessus
- Purger l'historique Git avec `git filter-branch`
- Contacter le support GitHub si le dépôt est public

### Problème 3: Activité suspecte sur OpenAI

**Solution:**
- Révoquer TOUTES les clés immédiatement
- Changer le mot de passe OpenAI
- Activer l'authentification à deux facteurs (2FA)
- Contacter le support OpenAI: support@openai.com

---

## 📞 Support

**Documentation OpenAI:**
- Gestion des clés: https://platform.openai.com/docs/api-reference/authentication
- Sécurité: https://platform.openai.com/docs/guides/safety-best-practices

**En cas de facturation anormale:**
- Email: support@openai.com
- Révoquer toutes les clés
- Fournir les logs d'utilisation

---

## ✅ Une fois terminé

Quand toutes les étapes sont complétées:

1. ✅ Ancienne clé révoquée
2. ✅ Nouvelle clé active
3. ✅ Serveur redémarré avec succès
4. ✅ .env protégé par .gitignore

**Vous pouvez continuer à utiliser l'application en toute sécurité!**

---

**Créé le:** 15 janvier 2026  
**Priorité:** 🔥 CRITIQUE - À traiter IMMÉDIATEMENT  
**Status:** ⚠️ EN ATTENTE D'ACTION
