# Guide pour Prendre les Screenshots

Ce guide vous explique comment prendre les screenshots nécessaires pour le projet.

## 📋 Liste des Screenshots Requis

### 1. Dashboard Principal (01-main-dashboard.png)
**Instructions:**
1. Ouvrez l'application dans votre navigateur (`http://localhost:3000/index.html`)
2. Assurez-vous d'avoir quelques posts dans la base de données
3. Prenez une capture d'écran de la page principale montrant :
   - Les boutons de scraping en haut
   - Les statistiques (DATABASE STATS et FILTERED RESULTS)
   - Les filtres
   - Les cartes de posts
   - Le panneau de logs (si visible)

**Raccourci clavier:**
- **Windows**: `Win + Shift + S` (outil Capture d'écran)
- **Mac**: `Cmd + Shift + 4`
- **Linux**: `Print Screen` ou `Shift + Print Screen`

### 2. Modal Statistics (02-statistics-modal.png)
**Instructions:**
1. Cliquez sur le bouton "📊 Statistics"
2. Attendez que les graphiques se chargent
3. Prenez une capture montrant :
   - Le timeline/histogramme
   - Le pie chart des produits
   - Les filtres de date
   - Le filtre par produit

### 3. Backlog Sidebar (03-backlog-sidebar.png)
**Instructions:**
1. Ajoutez quelques posts au backlog (clic sur "📋 Add to Backlog")
2. Cliquez sur le bouton "📋 Backlog" pour ouvrir la sidebar
3. Prenez une capture montrant :
   - La sidebar ouverte à droite
   - Les posts dans le backlog
   - Les boutons d'action (Card View, Clear, Export, Generate Ideas)
   - Les commentaires sous les posts (si présents)

### 4. Post Preview Modal (04-post-preview.png)
**Instructions:**
1. Cliquez sur le bouton "👁️ Preview" sur une carte de post
2. Prenez une capture du modal montrant :
   - Le contenu complet du post
   - Les métadonnées (source, auteur, date, sentiment, produit)
   - Le lien vers le post original

### 5. Interface de Filtrage (05-filtering.png)
**Instructions:**
1. Appliquez plusieurs filtres :
   - Sélectionnez une source (ex: "Trustpilot")
   - Sélectionnez un sentiment (ex: "Negative")
   - Sélectionnez un produit OVH (ex: "VPS")
   - Ajoutez un mot-clé dans la recherche
2. Prenez une capture montrant :
   - Les filtres actifs
   - Les résultats filtrés
   - Le compteur de filtres actifs

### 6. Export CSV (06-export.png)
**Instructions:**
1. Appliquez des filtres pour avoir des résultats
2. Cliquez sur "📥 Export Posts"
3. Prenez une capture montrant :
   - Le message de succès (toast notification)
   - Ou le fichier CSV téléchargé ouvert dans Excel/éditeur

### 7. Mode Clair (07-light-mode.png)
**Instructions:**
1. Cliquez sur le bouton de thème (🌓) pour passer en mode clair
2. Prenez une capture du dashboard en mode clair
3. Montrez le contraste amélioré avec le texte noir

### 8. Mode Sombre (08-dark-mode.png)
**Instructions:**
1. Assurez-vous d'être en mode sombre (par défaut)
2. Prenez une capture du dashboard en mode sombre
3. Montrez l'interface avec les couleurs sombres

## 🛠️ Outils Recommandés

### Pour Windows:
- **Outil Capture d'écran intégré**: `Win + Shift + S`
- **Snipping Tool**: Recherchez "Snipping Tool" dans le menu Démarrer
- **ShareX**: Outil gratuit et puissant (https://getsharex.com/)

### Pour Mac:
- **Capture d'écran native**: `Cmd + Shift + 4`
- **Skitch**: Application Evernote pour annotations

### Pour Linux:
- **Flameshot**: `sudo apt install flameshot` (très recommandé)
- **GNOME Screenshot**: Intégré dans GNOME
- **KDE Spectacle**: Pour KDE

## 📐 Dimensions Recommandées

- **Résolution**: 1920x1080 (Full HD) ou 2560x1440 (2K)
- **Format**: PNG (meilleure qualité pour les interfaces)
- **Taille maximale**: 500KB par image (compressez si nécessaire)

## 🎨 Conseils pour de Meilleures Captures

1. **Masquez les informations sensibles**: Floutez ou masquez toute information personnelle
2. **Utilisez un navigateur moderne**: Chrome, Firefox, Edge pour de meilleurs rendus
3. **Plein écran**: Utilisez F11 pour le mode plein écran si nécessaire
4. **Zoom**: Assurez-vous que le zoom du navigateur est à 100%
5. **Données de démo**: Utilisez des données de test, pas de vraies données clients

## 📦 Compression des Images

Avant de commiter les screenshots, compressez-les :

### Outils en ligne:
- **TinyPNG**: https://tinypng.com/
- **Squoosh**: https://squoosh.app/

### Outils en ligne de commande:
```bash
# Avec ImageMagick
convert screenshot.png -quality 85 -strip screenshot_compressed.png

# Avec pngquant
pngquant --quality=65-80 screenshot.png
```

## ✅ Checklist Avant de Commiter

- [ ] Tous les 8 screenshots sont présents
- [ ] Les noms de fichiers suivent la convention (01-xxx.png, 02-xxx.png, etc.)
- [ ] Les images sont compressées (< 500KB chacune)
- [ ] Les screenshots montrent clairement les fonctionnalités
- [ ] Aucune information sensible n'est visible
- [ ] Les images sont en format PNG
- [ ] Le README.md principal référence les screenshots

## 🚀 Ajout au README

Une fois les screenshots prêts, ajoutez-les au README.md :

```markdown
## 📸 Screenshots

### Main Dashboard
![Main Dashboard](docs/screenshots/01-main-dashboard.png)
*Main dashboard showing posts, filters, and statistics*

### Statistics & Analysis
![Statistics](docs/screenshots/02-statistics-modal.png)
*Timeline, histogram, and product distribution charts*

### Backlog Management
![Backlog](docs/screenshots/03-backlog-sidebar.png)
*Backlog sidebar with posts and comments*

### Post Preview
![Post Preview](docs/screenshots/04-post-preview.png)
*Full post content preview modal*

### Filtering Interface
![Filtering](docs/screenshots/05-filtering.png)
*Active filters and filtered results*

### Export Functionality
![Export](docs/screenshots/06-export.png)
*CSV export functionality*

### Light Mode
![Light Mode](docs/screenshots/07-light-mode.png)
*Application in light mode theme*

### Dark Mode
![Dark Mode](docs/screenshots/08-dark-mode.png)
*Application in dark mode theme (default)*
```

