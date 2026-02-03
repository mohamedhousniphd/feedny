# Feedny - Application de Feedback Étudiant

<!-- Railway build trigger: updated 2025-02-03 -->

<div align="center">

![Feedny Logo](https://img.shields.io/badge/Feedny-Feedback_Anonyme-black?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-black?style=for-the-badge)

**Application web dockerisée pour collecter, analyser et résumer les feedbacks des étudiants**

</div>

---

## 📖 Table des Matières

1. [Description du Projet](#description-du-projet)
2. [Fonctionnalités](#fonctionnalités)
3. [Architecture de l'Application](#architecture-de-lapplication)
4. [Technologies Utilisées](#technologies-utilisées)
5. [Installation Locale avec Docker](#installation-locale-avec-docker)
6. [Déploiement sur Railway](#déploiement-sur-railway)
7. [Déploiement sur Vercel](#déploiement-sur-vercel)
8. [Déploiement sur Heroku](#déploiement-sur-heroku)
9. [Guide d'Utilisation](#guide-dutilisation)
10. [Configuration](#configuration)
11. [Coûts et Optimisation](#coûts-et-optimisation)
12. [Sécurité](#sécurité)
13. [Dépannage](#dépannage)
14. [Contribution](#contribution)
15. [Licence](#licence)

---

## 📝 Description du Projet

**Feedny** est une application web moderne et mobile-first qui permet aux enseignants de collecter des feedbacks anonymes auprès de leurs étudiants. L'application inclut des fonctionnalités d'analyse avancée utilisant l'IA pour générer des résumés et des nuages de mots.

### Objectifs Principaux

- ✅ Collecte de feedbacks anonyme et sécurisée
- ✅ Interface mobile-friendly (90% des étudiants utilisent smartphone)
- ✅ Analyse intelligente avec DeepSeek AI
- ✅ Génération automatique de nuages de mots
- ✅ Coût minimal (< $5/mois sur Railway)
- ✅ Déploiement simple et rapide

---

## ✨ Fonctionnalités

### Pour les Étudiants

- 📱 **Interface Mobile-First**
  - Design optimisé pour smartphones
  - Touch targets de 44x44px minimum
  - Typographie lisible (min 16px)
  - Validation en temps réel

- ✍️ **Feedback Simple**
  - Zone de texte unique
  - Limite de 240 caractères
  - Compteur de caractères en temps réel
  - Message de confirmation clair

- 🔒 **Anonymat Total**
  - Aucune information personnelle collectée
  - Identification par device ID uniquement
  - Un seul feedback par session

- 🚫 **Protection contre le Spam**
  - Limite d'un feedback par appareil
  - Pas d'acceptation tant que l'enseignant analyse

### Pour les Enseignants

- 🔐 **Authentification Sécurisée**
  - Page `/teacher` protégée par mot de passe
  - Session de 24 heures
  - Déconnexion simple

- 📊 **Tableau de Bord Complet**
  - Vue en tableau des feedbacks
  - Statistiques en temps réel
  - Case à cocher pour sélection
  - Filtrage des feedbacks malveillants

- 🤖 **Analyse IA Intelligente**
  - Integration DeepSeek API
  - Résumés concis (max 1 page)
  - Analyse des thèmes principaux
  - Recommandations pédagogiques

- ☁️ **Nuage de Mots**
  - Génération automatique
  - Stopwords français exclus
  - Design coloré et professionnel
  - Téléchargeable en PNG

- 📥 **Export et Gestion**
  - Export CSV des feedbacks
  - Réinitialisation de la base
  - Backup automatique avec SQLite WAL mode

---

## 🏗️ Architecture de l'Application

### Structure des Répertoires

```
feedny/
├── app/
│   ├── main.py                 # Point d'entrée FastAPI
│   ├── models.py               # Modèles Pydantic
│   ├── database.py             # Gestion SQLite
│   ├── routes/                 # Routes API (future extension)
│   ├── services/               # Services métier
│   │   ├── wordcloud.py        # Génération nuage de mots
│   │   └── deepseek.py         # Integration DeepSeek AI
│   └── static/                 # Frontend
│       ├── css/
│       │   └── styles.css      # Styles de l'application
│       └── index.html, login.html, dashboard.html
├── data/                       # Données persistantes
│   └── feedny.db              # Base SQLite
├── Dockerfile                  # Configuration Docker
├── docker-compose.yml          # Docker Compose
├── requirements.txt           # Dépendances Python
├── .env.example               # Variables d'environnement
└── README.md                   # Ce fichier
```

### Architecture Backend

```
┌─────────────┐
│   FastAPI   │
│  (Python)   │
└──────┬──────┘
       │
       ├─────────────────────────────┐
       │                             │
┌──────▼──────┐            ┌────────▼────────┐
│   SQLite    │            │  DeepSeek API   │
│  (Base DB)  │            │  (Analyse IA)   │
└─────────────┘            └─────────────────┘
       │
┌──────▼──────┐
│ Wordcloud   │
│  Service    │
└─────────────┘
```

### Base de Données (SQLite)

#### Table `feedbacks`

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | INTEGER | Identifiant unique (auto-incrémenté) |
| `content` | TEXT | Contenu du feedback (max 240 caractères) |
| `device_id` | TEXT | Identifiant unique de l'appareil |
| `created_at` | TIMESTAMP | Date et heure de création |
| `included_in_analysis` | BOOLEAN | Inclusion dans l'analyse |

#### Table `device_limits`

| Colonne | Type | Description |
|---------|------|-------------|
| `device_id` | TEXT | Identifiant unique de l'appareil (PK) |
| `feedback_count` | INTEGER | Nombre de feedbacks soumis |
| `last_feedback` | TIMESTAMP | Date du dernier feedback |

---

## 🛠️ Technologies Utilisées

### Backend

- **Python 3.11** - Langage principal
- **FastAPI 0.104** - Framework web moderne et rapide
- **SQLite** - Base de données légère et portable
- **Uvicorn** - Serveur ASGI
- **Pydantic** - Validation des données

### Frontend

- **HTML5** - Structure sémantique
- **CSS3** - Styles modernes avec variables CSS
- **JavaScript Vanilla** - Interactivité
- **Responsive Design** - Mobile-first

### Services Externes

- **DeepSeek API** - Analyse IA des feedbacks
  - Compatible OpenAI SDK
  - Modèle: `deepseek-chat`
  - Max tokens: 1000

### Développement et Déploiement

- **Docker** - Conteneurisation
- **Docker Compose** - Orchestration locale
- **Railway** - Plateforme de déploiement cible

### Libraries Python Spécialisées

- **wordcloud** - Génération de nuages de mots
- **stopwordsiso** - Stopwords français
- **matplotlib** - Rendu graphique
- **pandas** - Manipulation de données
- **httpx** - Client HTTP asynchrone

---

## 💻 Installation Locale avec Docker

### Prérequis

- **Docker** (v20.10+) - [Installation Guide](https://docs.docker.com/get-docker/)
- **Docker Compose** (v2.0+) - Inclu avec Docker Desktop

### Étapes d'Installation

#### 1. Cloner le Projet

```bash
git clone <repository-url>
cd feedny
```

#### 2. Configurer les Variables d'Environnement

```bash
cp .env.example .env
```

Éditer le fichier `.env`:

```env
# Server Configuration
HOST=0.0.0.0
PORT=8000
SECRET_KEY=votre-cle-secrete-personnalisee-ici
TEACHER_PASSWORD=votre-mot-de-passe-enseignant

# DeepSeek API (Optionnel pour les tests)
DEEPSEEK_API_KEY= votre-cle-api-deepseek
DEEPSEEK_BASE_URL=https://api.deepseek.com

# Database
DATABASE_URL=sqlite:///./data/feedny.db

# CORS
ALLOWED_ORIGINS=*
```

#### 3. Obtenir une Clé API DeepSeek

1. Visitez [DeepSeek](https://platform.deepseek.com/)
2. Créez un compte
3. Générez une clé API
4. Copiez-la dans votre fichier `.env`

#### 4. Lancer l'Application

```bash
docker-compose up -d
```

#### 5. Vérifier le Fonctionnement

```bash
# Voir les logs
docker-compose logs -f

# Vérifier le statut
docker-compose ps
```

L'application sera accessible à **http://localhost:8000**

#### 6. Arrêter l'Application

```bash
docker-compose down
```

#### 7. Nettoyer les Données

```bash
docker-compose down -v  # Supprime les volumes (données)
```

---

## 🚀 Déploiement sur Railway

Railway est la plateforme recommandée pour Feedny, offrant un excellent rapport qualité-prix (< $5/mois).

### Prérequis

- Compte Railway (gratuit)
- Git repository
- Clé API DeepSeek

### Étape 1: Préparer le Déploiement

#### Option A: Via GitHub (Recommandé)

1. Poussez votre code sur GitHub
2. Connectez votre compte GitHub à Railway

#### Option B: Via CLI Railway

```bash
npm install -g @railway/cli
railway login
```

### Étape 2: Créer un Nouveau Projet Railway

#### Via Web Dashboard

1. Connectez-vous à [Railway](https://railway.app/)
2. Cliquez sur **"New Project"**
3. Sélectionnez **"Deploy from GitHub repo"** (Option A)
   - OU **"Empty Project"** (Option B)

#### Via CLI

```bash
railway init
railway up
```

### Étape 3: Configurer le Service

#### Configuration du Dockerfile

Ajoutez le fichier `Procfile` à la racine (optionnel, Railway détecte automatiquement):

```procfile
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Étape 4: Configurer les Variables d'Environnement

#### Via Web Dashboard

1. Ouvrez votre projet Railway
2. Sélectionnez votre service
3. Cliquez sur l'onglet **"Variables"**
4. Ajoutez les variables suivantes:

```
SECRET_KEY=générez-une-clé-aléatoire-longue-et-sécurisée
TEACHER_PASSWORD=choisissez-un-mot-de-passe-fort
DEEPSEEK_API_KEY=votre-clé-api-deepseek
DEEPSEEK_BASE_URL=https://api.deepseek.com
DATABASE_URL=sqlite:///./data/feedny.db
ALLOWED_ORIGINS=*
```

Pour générer une `SECRET_KEY` sécurisée:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

#### Via CLI

```bash
railway variables set SECRET_KEY=your-secret-key
railway variables set TEACHER_PASSWORD=your-password
railway variables set DEEPSEEK_API_KEY=your-api-key
railway variables set DEEPSEEK_BASE_URL=https://api.deepseek.com
railway variables set DATABASE_URL=sqlite:///./data/feedny.db
railway variables set ALLOWED_ORIGINS=*
```

### Étape 5: Configurer le Stockage Persistant

Les fichiers SQLite doivent persister entre les redéploiements.

#### Via Web Dashboard

1. Onglet **"Settings"** → **"Volumes"**
2. Cliquez **"Create Volume"**
3. Nommez-le `data`
4. Attachez-le au chemin `/app/data`

### Étape 6: Activer App Sleeping (Optionnel)

Pour réduire les coûts, activez App Sleeping:

1. Onglet **"Settings"** → **"Usage"**
2. Activez **"App Sleeping"**
3. L'app s'endormira après 30 min d'inactivité
4. Premier chargement: ~30 secondes

### Étape 7: Vérifier le Déploiement

Railway déploiera automatiquement. Surveillez:

1. Onglet **"Deployments"** - Voir la progression
2. Onglet **"Metrics"** - Monitoring en temps réel
3. Onglet **"Logs"** - Logs d'application

Une fois déployé, Railway fournira une URL publique.

### Étape 8: Configurer le Domaine Personnalisé (Optionnel)

1. Onglet **"Settings"** → **"Networking"**
2. Cliquez **"Generate Domain"**
3. OU ajoutez un domaine personnalisé

### Coûts sur Railway

| Plan | Prix | Features |
|------|------|----------|
| Hobby | **$5/mois** | 500h/mois, 512MB RAM, SQLite gratuit |
| Avec App Sleeping | **$1-3/mois** | Usage intermittent optimal |

### Monitoring et Maintenance

```bash
# Voir les logs en temps réel
railway logs

# Redéployer
railway up

# Vérifier les métriques
railway open
```

---

## 🌐 Déploiement sur Vercel

Bien que Feedny soit optimisé pour Railway, il est possible de le déployer sur Vercel.

### Limitations sur Vercel

- Vercel est optimisé pour Node.js/static sites
- Python supporté mais moins idéal pour FastAPI + SQLite
- Base de données externe requise (PostgreSQL/MySQL)

### Étapes de Déploiement

#### 1. Prérequis

- Compte Vercel
- Base de données externe (ex: Supabase PostgreSQL)

#### 2. Configurer pour Vercel

Créer `vercel.json`:

```json
{
  "version": 2,
  "builds": [
    {
      "src": "app/main.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "app/main.py"
    }
  ]
}
```

#### 3. Adapter la Base de Données

Modifier `app/database.py` pour PostgreSQL au lieu de SQLite:

```python
import asyncpg
# Remplacer les appels SQLite par asyncpg
```

#### 4. Déployer

```bash
vercel login
vercel
```

#### 5. Configurer les Variables d'Environnement

Dans le dashboard Vercel → **Settings** → **Environment Variables**:

```
SECRET_KEY=...
TEACHER_PASSWORD=...
DEEPSEEK_API_KEY=...
DATABASE_URL=postgresql://user:pass@host/db
```

#### 6. Coûts sur Vercel

| Plan | Prix | Features |
|------|------|----------|
| Hobby | **Gratuit** | 100GB bandwidth, 1000ms timeout |
| Pro | **$20/mois** | 1TB bandwidth, Infractions |

**Note**: Nécessite une base de données externe payante (ex: Supabase $25/mois)

---

## 🚢 Déploiement sur Heroku

Heroku est une alternative à Railway pour déployer Feedny.

### Prérequis

- Compte Heroku
- Git
- Heroku CLI

### Étapes de Déploiement

#### 1. Installer Heroku CLI

```bash
# macOS
brew tap heroku/brew && brew install heroku

# Linux
curl https://cli-assets.heroku.com/install-ubuntu.sh | sh

# Windows
# Télécharger depuis https://devcenter.heroku.com/articles/heroku-cli
```

#### 2. Se Connecter à Heroku

```bash
heroku login
```

#### 3. Créer une Application

```bash
cd feedny
heroku create feedny-app
```

#### 4. Ajouter un Add-on PostgreSQL

Heroku ne supporte pas SQLite persistant. Nécessite PostgreSQL:

```bash
heroku addons:create heroku-postgresql:mini
```

Cela fournira une URL `DATABASE_URL` automatique.

#### 5. Configurer les Variables d'Environnement

```bash
heroku config:set SECRET_KEY=your-secret-key
heroku config:set TEACHER_PASSWORD=your-password
heroku config:set DEEPSEEK_API_KEY=your-api-key
heroku config:set DEEPSEEK_BASE_URL=https://api.deepseek.com
heroku config:set ALLOWED_ORIGINS=*
```

La variable `DATABASE_URL` est déjà définie par l'add-on PostgreSQL.

#### 6. Créer le Procfile

Créer `Procfile` à la racine:

```procfile
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1
```

#### 7. Déployer

```bash
git add .
git commit -m "Deploy to Heroku"
git push heroku main
```

#### 8. Vérifier le Déploiement

```bash
heroku open
heroku logs --tail
```

#### 9. Configurer les Dynos

```bash
# Activer le dyno web
heroku ps:scale web=1

# Vérifier l'état
heroku ps
```

### Coûts sur Heroku

| Plan | Prix | Features |
|------|------|----------|
| Eco | **$5/mois** | 1 dyno, 512MB RAM |
| Basic | **$7/mois** | 1 dyno, 512MB RAM, metrics |
| PostgreSQL Mini | **$5/mois** | 400h/mois, 10k lignes |

**Total estimé**: **$10-12/mois**

---

## 📚 Guide d'Utilisation

### Pour les Étudiants

#### Accéder à l'Application

1. Ouvrez le lien fourni par l'enseignant sur votre smartphone
2. Vous verrez un formulaire de feedback
3. Tapez votre feedback (max 240 caractères)
4. Cliquez sur "Envoyer"
5. Vous recevrez un message de confirmation
6. Impossible d'envoyer un autre feedback jusqu'à réouverture

#### Exemple d'Utilisation

```
📱 http://votre-app.railway.app

┌─────────────────────────┐
│  📝 Feedny              │
│  Partagez votre feedback │
└─────────────────────────┘

┌─────────────────────────┐
│ Votre feedback           │
│ ┌───────────────────┐   │
│ │ Les cours sont... │   │
│ │                   │   │
│ └───────────────────┘   │
│                  120/240│
│                         │
│      [  Envoyer  ]     │
└─────────────────────────┘
```

### Pour les Enseignants

#### Connexion

1. Accédez à `http://votre-app.railway.app/teacher`
2. Entrez votre mot de passe
3. Vous serez redirigé vers le tableau de bord

#### Examiner les Feedbacks

Le tableau de bord affiche:
- **Statistiques**: Nombre total et sélectionnés
- **Tableau des feedbacks**: Avec métadonnées
- **Case à cocher**: Pour inclure/exclure

#### Analyser les Feedbacks

1. Sélectionnez les feedbacks à analyser (case à cocher)
2. Ajoutez un contexte (ex: "Cours de maths sur les équations")
3. Cliquez "Analyser les Feedbacks Sélectionnés"
4. Attendez la génération (quelques secondes)
5. Consultez:
   - Le nuage de mots (visuel)
   - Le résumé IA (textuel)

#### Exporter et Réinitialiser

- **Exporter CSV**: Téléchargez tous les feedbacks
- **Réinitialiser**: Supprimez tout pour un nouveau cycle
  ⚠️ Action irréversible - confirme 2 fois

#### Déconnexion

Cliquez "Déconnexion" pour quitter la session.

---

## ⚙️ Configuration

### Variables d'Environnement

#### Obligatoires

| Variable | Description | Exemple |
|----------|-------------|---------|
| `SECRET_KEY` | Clé secrète pour sessions | `abc123xyz789` |
| `TEACHER_PASSWORD` | Mot de passe enseignant | `MySecurePass2024!` |

#### Optionnelles

| Variable | Description | Défaut |
|----------|-------------|--------|
| `DEEPSEEK_API_KEY` | Clé API DeepSeek | - |
| `DEEPSEEK_BASE_URL` | URL API DeepSeek | `https://api.deepseek.com` |
| `DATABASE_URL` | URL base de données | `sqlite:///./data/feedny.db` |
| `ALLOWED_ORIGINS` | CORS origins | `*` |

### Personnalisation

#### Modifier les Couleurs

Éditez `app/static/css/styles.css`:

```css
:root {
    --color-primary: #000000;
    --color-secondary: #ffffff;
    /* ... */
}
```

#### Ajuster la Limite de Caractères

1. Éditez `app/models.py`:
```python
content: str = Field(..., min_length=1, max_length=240)
```

2. Éditez `app/static/index.html`:
```html
<textarea maxlength="240">...</textarea>
```

#### Personnaliser les Stopwords

Éditez `app/services/wordcloud.py`:

```python
def get_french_stopwords() -> set[str]:
    return stopwords('fr')
    # OU liste personnalisée:
    # return set({'et', 'ou', 'mais', ...})
```

---

## 💰 Coûts et Optimisation

### Estimation Coûts par Plateforme

| Plateforme | Coût Mensuel | Notes |
|------------|--------------|-------|
| **Railway** | **$1-3** | Recommandé - avec App Sleeping |
| Railway (sans sleep) | $5 | Utilisation continue |
| Heroku | $10-12 | + PostgreSQL requis |
| Vercel | $25+ | + Base externe requise |

### Optimisation des Coûts DeepSeek

- **Feedbacks sélectionnés**: Réduisez la quantité
- **Max tokens**: Déjà optimisé à 1000
- **Cache**: Pas nécessaire (analyses uniques)

**Coût estimé par analyse**:
- ~500 tokens input
- ~800 tokens output
- **Total**: ~1300 tokens
- **Prix**: ~$0.01-0.03 par analyse

### Conseils d'Optimisation

✅ **Railway avec App Sleeping**
- Activé par défaut après 30 min
- Premier chargement: ~30 secondes
- Économie: 60-80%

✅ **Base de données SQLite**
- Gratuite et légère
- Aucun service externe
- WAL mode activé

✅ **Analyse ciblée**
- Sélectionnez uniquement les feedbacks pertinents
- Évitez l'analyse automatique de tous les feedbacks

---

## 🔒 Sécurité

### Mesures de Sécurité Implémentées

1. **Anonymat**
   - Aucune information personnelle stockée
   - Device ID uniquement (pas d'IP)
   - Feedbacks anonymes

2. **Authentification Enseignant**
   - Mot de passe requis
   - Session token (24h)
   - HttpOnly cookies

3. **Validation des Entrées**
   - Pydantic models
   - Limite de caractères
   - Nettoyage automatique

4. **CORS**
   - Configurable via `ALLOWED_ORIGINS`
   - Par défaut: ouvert pour développement

5. **Rate Limiting**
   - Un feedback par device
   - Protection contre le spam

### Recommandations de Sécurité

✅ **En Production**

- Changer `SECRET_KEY` avec une valeur aléatoire
- Utiliser un mot de passe fort pour `TEACHER_PASSWORD`
- Configurer `ALLOWED_ORIGINS` avec votre domaine
- Activer HTTPS (Railway le fait automatiquement)
- Ne pas exposer le port 8000 publiquement

✅ **Backup**

- Les données SQLite sont dans `/app/data`
- Volume Railway persistant
- Export CSV régulier recommandé

---

## 🐛 Dépannage

### Problèmes Communs

#### 1. L'application ne démarre pas

**Symptôme**: Container Docker crash immédiatement

**Solutions**:
```bash
# Vérifier les logs
docker-compose logs

# Vérifier les variables d'environnement
docker-compose config

# Reconstruire l'image
docker-compose build --no-cache
docker-compose up
```

#### 2. Erreur "DEEPSEEK_API_KEY is not configured"

**Symptôme**: Échec de l'analyse IA

**Solution**:
```bash
# Ajouter la clé dans .env
DEEPSEEK_API_KEY=your-actual-key

# Redémarrer
docker-compose restart
```

#### 3. Wordcloud vide

**Symptôme**: Pas de mots affichés

**Causes possibles**:
- Pas assez de feedbacks sélectionnés (< 3)
- Stopwords trop restrictifs
- Feedbacks trop courts

**Solution**: Sélectionnez plus de feedbacks

#### 4. Export CSV illisible (accents)

**Symptôme**: Caractères étranges dans Excel

**Cause**: Encodage incorrect

**Solution**: Déjà implémenté avec `encoding='utf-8-sig'`
- Ouvrir dans Excel: Données → À partir de texte
- Choisir UTF-8

#### 5. Erreur "You have already submitted a feedback"

**Symptôme**: Étudiant bloqué injustement

**Causes**:
- Cookie device ID partagé (ex: même navigateur)
- Reset nécessaire

**Solution**:
- Enseignant réinitialise la base
- Étudiant utilise navigateur privé

#### 6. App Sleeping lent sur Railway

**Symptôme**: Premier chargement prend ~30 secondes

**Cause**: App réveille de veille

**Solution**:
- Normale, attendre
- Désactiver App Sleeping si usage fréquent
- Garder l'app active avec un ping régulier

#### 7. Base de données vide après redéploiement

**Symptôme**: Feedbacks perdus

**Cause**: Volume non attaché

**Solution Railway**:
1. Settings → Volumes
2. Créer volume `data` attaché à `/app/data`

### Debug Mode

Pour activer les logs détaillés:

```dockerfile
# Dans Dockerfile
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "debug"]
```

---

## 🤝 Contribution

Contributions sont les bienvenues !

### Comment Contribuer

1. Fork le projet
2. Créez une branche (`git checkout -b feature/AmazingFeature`)
3. Commitez (`git commit -m 'Add some AmazingFeature'`)
4. Push (`git push origin feature/AmazingFeature`)
5. Ouvrez une Pull Request

### Idées d'Amélioration

- [ ] Multi-enseignant support
- [ ] Email notifications
- [ ] Thèmes personnalisables
- [ ] Historique des analyses
- [ ] Export PDF
- [ ] Intégration Moodle/Canvas
- [ ] Feedbacks multilingues

---

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

---

## 📞 Support

Pour toute question ou problème:

1. Consultez la section **Dépannage**
2. Ouvrez une issue sur GitHub
3. Contactez le mainteneur

---

## 🙏 Remerciements

- **FastAPI** - Framework web moderne
- **DeepSeek** - API d'analyse IA
- **Railway** - Plateforme de déploiement
- **wordcloud** - Génération de nuages de mots
- **stopwordsiso** - Stopwords multilingues

---

<div align="center">

**Développé avec ❤️ pour l'enseignement**

[⬆ Retour en haut](#feedny---application-de-feedback-étudiant)

</div>
