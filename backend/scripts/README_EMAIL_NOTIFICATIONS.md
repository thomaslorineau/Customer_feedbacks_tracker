# Test des Notifications Email

## Prérequis

1. **Démarrer le serveur backend** :
   ```powershell
   cd backend
   python -m uvicorn app.main:app --reload --port 8000
   ```

2. **Configurer SMTP dans `.env`** (dans le dossier `backend/`) :
   ```
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=votre_email@gmail.com
   SMTP_PASSWORD=votre_mot_de_passe_app
   SMTP_FROM_EMAIL=votre_email@gmail.com
   SMTP_FROM_NAME=OVH Feedbacks Tracker
   ```

## Test rapide

### 1. Créer un trigger de test et tester l'envoi

```powershell
cd backend
python scripts/test_email_notifications.py
```

Ce script va :
- Vérifier la configuration SMTP
- Créer un trigger de test avec l'email `thomas.lorineau@ovhcloud.com`
- Tester l'envoi d'un email
- Afficher l'ID du trigger créé pour pouvoir le supprimer

### 2. Supprimer le trigger de test

```powershell
cd backend
python scripts/delete_test_trigger.py
```

Ce script supprime automatiquement tous les triggers contenant "TEST" dans le nom ou l'email de test.

## Test manuel via l'interface

1. Ouvrir http://localhost:8000/settings
2. Aller dans la section "Email Notifications"
3. Cliquer sur "Add Trigger"
4. Configurer :
   - **Nom** : "Test - Posts négatifs"
   - **Sentiment** : Negative
   - **Score de pertinence** : ≥ 0.3
   - **Emails** : `thomas.lorineau@ovhcloud.com` (un par ligne)
   - **Cooldown** : 60 minutes
   - **Max posts** : 10
5. Cliquer sur "Test Email Connection" pour vérifier SMTP
6. Le trigger enverra automatiquement un email quand un nouveau post négatif correspondant aux critères sera détecté

## Supprimer un trigger via l'API

```powershell
# Récupérer la liste des triggers
curl http://localhost:8000/api/email/triggers

# Supprimer un trigger (remplacer {id} par l'ID réel)
curl -X DELETE http://localhost:8000/api/email/triggers/{id}
```

## Notes

- Les triggers de test sont identifiables par "TEST" dans leur nom
- L'email de test `thomas.lorineau@ovhcloud.com` peut être facilement supprimé via le script `delete_test_trigger.py`
- Le cooldown empêche l'envoi de multiples emails si plusieurs posts arrivent rapidement
- Les emails sont regroupés : si plusieurs posts correspondent, ils sont envoyés dans un seul email

