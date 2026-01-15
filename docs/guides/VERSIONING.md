# Système de Versioning Automatique

Ce projet utilise un système de versioning automatique qui incrémente la version à chaque push.

## Format de Version

Le format utilisé est **Semantic Versioning** : `MAJOR.MINOR.PATCH`
- **MAJOR** : Changements incompatibles avec les versions précédentes
- **MINOR** : Nouvelles fonctionnalités compatibles
- **PATCH** : Corrections de bugs (incrémenté automatiquement)

## Fichier de Version

La version actuelle est stockée dans le fichier `VERSION` à la racine du projet.

## Incrémentation Automatique

### Méthode 1 : Script PowerShell (Recommandé pour Windows)

Avant chaque push, exécutez :

```powershell
.\scripts\bump-version.ps1
git push
```

Le script :
1. Lit la version actuelle depuis `VERSION`
2. Incrémente le numéro PATCH
3. Met à jour le fichier `VERSION`
4. Crée un commit automatique avec le message "chore: bump version to X.Y.Z"

### Méthode 2 : Hook Git (Optionnel)

Des hooks Git sont disponibles dans `.git/hooks/` mais peuvent nécessiter une configuration supplémentaire sur Windows.

## Affichage dans l'UI

La version est automatiquement affichée dans :
- La barre de navigation (en haut à droite, à côté du bouton de thème)
- Accessible via l'endpoint API `/api/version`

## Endpoint API

```http
GET /api/version
```

Réponse :
```json
{
  "version": "1.0.0",
  "build_date": "2024-01-15T10:30:00"
}
```

## Workflow Recommandé

1. Faire vos modifications
2. Commit vos changements : `git commit -m "feat: nouvelle fonctionnalité"`
3. Incrémenter la version : `.\scripts\bump-version.ps1`
4. Push : `git push`

La version sera automatiquement mise à jour et visible dans l'interface utilisateur.


