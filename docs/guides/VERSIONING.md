# Système de Versioning Automatique

Ce projet utilise un système de versioning automatique qui incrémente MINOR automatiquement lors d'un push.

## Format de Version

Le format utilisé est **Semantic Versioning** : `MAJOR.MINOR.PATCH` (3 numéros)
- **MAJOR** : Changements incompatibles avec les versions précédentes (modifié manuellement dans `VERSION`)
- **MINOR** : Incrémenté automatiquement à chaque push (stocké dans `.version_minor`)
- **PATCH** : 2 derniers chiffres du nombre de commits (pour garder la version courte)

## Fichiers de Version

- Le fichier `VERSION` à la racine contient uniquement le numéro **MAJOR** (ex: `1`)
- Le fichier `.version_minor` contient le numéro **MINOR** (auto-incrémenté lors du push)

Les numéros sont lus par la fonction `get_version()` dans `backend/app/main.py`.

## Calcul Automatique

### MAJOR
- Lu depuis le fichier `VERSION` à la racine
- Modifié manuellement lors de changements incompatibles

### MINOR
- Lu depuis le fichier `.version_minor`
- **Incrémenté automatiquement** lors d'un push via le script `scripts/utils/push.sh`
- S'incrémente de 1 à chaque push (ex: 0 → 1 → 2 → 3...)

### PATCH
- Calculé automatiquement depuis `git rev-list --count HEAD`
- Prend les **2 derniers chiffres** du nombre de commits (ex: 177 commits → PATCH = 77)
- Permet de garder la version courte et lisible

## Exemple

Si `VERSION` contient `1` et que :
- `.version_minor` contient `5` → MINOR = 5
- Il y a 177 commits → PATCH = 77 (2 derniers chiffres)

La version affichée sera : `1.5.77`

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
   - PATCH s'incrémente automatiquement (basé sur le nombre de commits)
3. Push via le script : `bash scripts/utils/push.sh`
   - **MINOR s'incrémente automatiquement** avant le push
   - Un commit automatique est créé pour mettre à jour `.version_minor`
   - La version sera automatiquement calculée et visible dans l'interface utilisateur

**Note :** Si vous utilisez `git push` directement au lieu du script, MINOR ne s'incrémentera pas automatiquement. Utilisez toujours `bash scripts/utils/push.sh` pour bénéficier de l'incrémentation automatique.

## Fallback

Si Git n'est pas disponible ou en cas d'erreur :
- La version retournée sera `MAJOR.0.0` (ex: `1.0.0`)
- Un message de debug sera loggé mais l'application continuera de fonctionner


