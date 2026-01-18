# Système de Versioning Automatique

Ce projet utilise un système de versioning automatique basé sur Git qui calcule automatiquement MINOR et PATCH.

## Format de Version

Le format utilisé est **Semantic Versioning** : `MAJOR.MINOR.PATCH` (3 numéros)
- **MAJOR** : Changements incompatibles avec les versions précédentes (modifié manuellement dans `VERSION`)
- **MINOR** : Nombre de push (calculé depuis les tags Git de format `vMAJOR.*`)
- **PATCH** : Nombre de commits (calculé depuis `git rev-list --count HEAD`)

## Fichier de Version

Le fichier `VERSION` à la racine du projet contient uniquement le numéro **MAJOR** (ex: `1`).

Les numéros **MINOR** et **PATCH** sont calculés automatiquement par la fonction `get_version()` dans `backend/app/main.py`.

## Calcul Automatique

### MAJOR
- Lu depuis le fichier `VERSION` à la racine
- Modifié manuellement lors de changements incompatibles

### MINOR (Option A - Recommandée)
- Calculé depuis les tags Git de format `vMAJOR.*` (ex: `v1.0`, `v1.1`, `v1.2`)
- Le système compte les tags uniques et utilise le maximum + 1
- Pour incrémenter MINOR, créer un tag : `git tag v1.5` puis `git push --tags`

### MINOR (Option B - Alternative)
- Utiliser un hook Git pre-push qui incrémente MINOR dans un fichier `.version_minor`
- Moins recommandé car nécessite configuration manuelle

### PATCH
- Calculé automatiquement depuis `git rev-list --count HEAD`
- Représente le nombre total de commits dans le repository
- S'incrémente automatiquement à chaque commit

## Exemple

Si `VERSION` contient `1` et que :
- Il y a 3 tags Git : `v1.0`, `v1.1`, `v1.2` → MINOR = 3
- Il y a 77 commits → PATCH = 77

La version affichée sera : `1.3.77`

## Affichage dans l'UI

La version est automatiquement affichée dans :
- La barre de navigation (en haut à droite, à côté du bouton de thème)
- Accessible via l'endpoint API `/api/version`
- Rafraîchissement automatique toutes les 30 secondes

## Endpoint API

```http
GET /api/version
```

Réponse :
```json
{
  "version": "1.3.77",
  "build_date": "2024-01-15T10:30:00"
}
```

## Workflow Recommandé

1. Faire vos modifications
2. Commit vos changements : `git commit -m "feat: nouvelle fonctionnalité"`
   - PATCH s'incrémente automatiquement
3. Pour incrémenter MINOR (nouvelles fonctionnalités) :
   ```bash
   git tag v1.5
   git push --tags
   ```
4. Push : `git push`
   - La version sera automatiquement calculée et visible dans l'interface utilisateur

## Fallback

Si Git n'est pas disponible ou en cas d'erreur :
- La version retournée sera `MAJOR.0.0` (ex: `1.0.0`)
- Un message de debug sera loggé mais l'application continuera de fonctionner


