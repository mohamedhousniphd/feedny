# Quick Start Guide - Feedny

Guide de démarrage rapide pour déployer Feedny en quelques minutes.

---

## 🚀 Démarrage Rapide (Local)

### 1. Préparer l'environnement

```bash
cd mini-services/feedny

# Copier les variables d'environnement
cp .env.example .env
```

### 2. Configurer les variables minimales

Éditez `.env`:

```env
SECRET_KEY=une-cle-secrete-longue-et-aleatoire
TEACHER_PASSWORD=votre-mot-de-passe-enseignant
DEEPSEEK_API_KEY=votre-cle-api-deepseek  # Optionnel pour tests
```

### 3. Lancer l'application

```bash
docker-compose up -d
```

### 4. Accéder à l'application

- **Étudiants**: http://localhost:8000
- **Enseignants**: http://localhost:8000/teacher

### 5. Arrêter l'application

```bash
docker-compose down
```

---

## ☁️ Démarrage Rapide (Railway)

### Prérequis

- Compte Railway (gratuit)
- Compte GitHub
- Clé API DeepSeek

### Étapes

#### 1. Pushez sur GitHub

```bash
cd mini-services/feedny
git init
git add .
git commit -m "Initial Feedny app"
git branch -M main
git remote add origin https://github.com/votre-username/feedny.git
git push -u origin main
```

#### 2. Déployer sur Railway

1. Connectez-vous à [Railway](https://railway.app/)
2. Cliquez **"New Project"** → **"Deploy from GitHub repo"**
3. Sélectionnez votre repository `feedny`
4. Railway détectera automatiquement le Dockerfile

#### 3. Configurez les variables d'Environnement

Dans le projet Railway → **Variables**:

```
SECRET_KEY=clé-aleatoire-longue-et-sécurisée
TEACHER_PASSWORD=votre-mot-de-passe-fort
DEEPSEEK_API_KEY=votre-cle-api-deepseek
```

Générez une SECRET_KEY sécurisée:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

#### 4. Configurez le volume de stockage

1. **Settings** → **Volumes**
2. Cliquez **"Create Volume"**
3. Nom: `data`
4. Mount path: `/app/data`

#### 5. Attendez le déploiement

Railway déploiera automatiquement (~2-3 minutes).

#### 6. Testez l'application

L'URL sera affichée dans le dashboard Railway:
- Étudiants: `https://votre-app.railway.app/`
- Enseignants: `https://votre-app.railway.app/teacher`

#### 7. (Optionnel) Activer App Sleeping

Pour réduire les coûts:

1. **Settings** → **Usage**
2. Activez **"App Sleeping"**

Coût estimé: **$1-3/mois**

---

## 📝 Premiers Pas

### Pour les Enseignants

1. **Connectez-vous**: `/teacher`
2. **Entrez votre mot de passe**
3. **Partagez le lien** avec les étudiants (sans le `/teacher`)
4. **Attendez les feedbacks**
5. **Sélectionnez** les feedbacks à analyser
6. **Ajoutez un contexte** (ex: "Cours de maths sur les équations")
7. **Cliquez "Analyser"**
8. **Téléchargez** le nuage de mots
9. **Exportez en CSV** si nécessaire
10. **Réinitialisez** pour une nouvelle collecte

### Pour les Étudiants

1. **Accédez** au lien partagé
2. **Tapez** votre feedback (max 240 caractères)
3. **Cliquez** "Envoyer"
4. **Vous recevrez** un message de confirmation
5. **Attendez** que l'enseignant ouvre une nouvelle collecte

---

## 🔧 Obtenir une Clé API DeepSeek

1. Visitez [https://platform.deepseek.com/](https://platform.deepseek.com/)
2. Créez un compte gratuit
3. Allez dans **API Keys**
4. Cliquez **"Create New Key"**
5. Copiez la clé
6. Collez-la dans vos variables d'environnement

**Coût**: ~$0.01-0.03 par analyse

---

## 🐛 Résolution de Problèmes Rapides

### Port déjà utilisé

```bash
# Changez le port dans docker-compose.yml
ports:
  - "8001:8000"
```

### Impossible de se connecter

```bash
# Vérifiez les logs
docker-compose logs -f feedny

# Redémarrez
docker-compose restart
```

### Wordcloud ne s'affiche pas

- Assurez-vous d'avoir sélectionné au moins 3 feedbacks
- Vérifiez que la clé API DeepSeek est configurée
- Consultez les logs pour les erreurs

### Base de données vide après redéploiement

- Assurez-vous que le volume `/app/data` est attaché (Railway)
- Les données SQLite sont dans `data/feedny.db`

---

## 📚 Documentation Complète

Pour plus de détails, consultez [README.md](README.md):

- Architecture détaillée
- Instructions de déploiement complètes
- Guide d'utilisation avancé
- Sécurité et optimisation
- Dépannage détaillé

---

## 💡 Astuces

### Pour tester sans DeepSeek

- L'analyse échouera mais le reste de l'app fonctionnera
- Les feedbacks seront quand même collectés
- Le wordcloud ne nécessite pas DeepSeek

### Pour réduire les coûts

- Activez App Sleeping sur Railway
- Sélectionnez uniquement les feedbacks pertinents pour l'analyse
- Utilisez l'export CSV régulièrement

### Pour augmenter la sécurité

- Utilisez un mot de passe enseignant fort
- Changez SECRET_KEY après le premier déploiement
- Configurez ALLOWED_ORIGINS avec votre domaine exact

---

**Questions? Consultez le [README.md](README.md) complet ou ouvrez une issue sur GitHub.**
