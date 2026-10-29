# Checklist de Déploiement - Feedny

Checklist pour s'assurer que tout est prêt avant le déploiement en production.

---

## ✅ Avant le Déploiement

### Configuration

- [ ] Cloner le repository localement
- [ ] Copier `.env.example` vers `.env`
- [ ] Configurer `SECRET_KEY` avec une valeur aléatoire longue
- [ ] Configurer `TEACHER_PASSWORD` avec un mot de passe fort
- [ ] Obtenir et configurer `DEEPSEEK_API_KEY`
- [ ] Vérifier que `ALLOWED_ORIGINS` est correct (désactivez `*` en production)

### Tests Locaux

- [ ] Lancer l'application: `docker-compose up -d`
- [ ] Vérifier que l'application démarre: http://localhost:8000
- [ ] Tester la soumission de feedback étudiant
- [ ] Vérifier le rate limiting (un feedback par device)
- [ ] Tester la connexion enseignant: http://localhost:8000/teacher
- [ ] Tester la sélection de feedbacks
- [ ] Tester l'analyse IA (nécessite clé DeepSeek)
- [ ] Tester la génération du wordcloud
- [ ] Tester l'export CSV
- [ ] Vérifier que les accents sont lisibles dans le CSV
- [ ] Tester le reset de la base de données
- [ ] Vérifier les logs: `docker-compose logs -f`

### Docker

- [ ] Vérifier le Dockerfile est optimisé (multi-stage build)
- [ ] Tester le build: `docker-compose build --no-cache`
- [ ] Vérifier que l'image taille est acceptable (< 500MB)
- [ ] Tester le redémarrage: `docker-compose restart`

---

## ✅ Déploiement Railway

### Préparation GitHub

- [ ] Créer un repository GitHub pour Feedny
- [ ] Pousser le code: `git push origin main`
- [ ] Vérifier que tous les fichiers sont commités
- [ ] Vérifier que `.gitignore` exclut `.env` et `*.db`

### Configuration Railway

- [ ] Créer un compte Railway (ou se connecter)
- [ ] Connecter le compte GitHub à Railway
- [ ] Créer un nouveau projet
- [ ] Sélectionner le repository Feedny
- [ ] Attendre que Railway détecte le Dockerfile

### Variables d'Environnement

- [ ] Configurer `SECRET_KEY` (clé aléatoire sécurisée)
- [ ] Configurer `TEACHER_PASSWORD`
- [ ] Configurer `DEEPSEEK_API_KEY`
- [ ] Configurer `DEEPSEEK_BASE_URL` (default: https://api.deepseek.com)
- [ ] Configurer `DATABASE_URL` (default: sqlite:///./data/feedny.db)
- [ ] Configurer `DB_PATH=/app/data/feedny.db` (prioritaire sur `DATABASE_URL`, obligatoire pour la persistance)
- [ ] Configurer `ADMIN_CODE` (optionnel, default: `HOUSNI`)
- [ ] Configurer `ALLOWED_ORIGINS` (votre domaine Railway)

### Stockage Persistant

- [ ] Créer un volume nommé `data`
- [ ] Attacher le volume au path `/app/data`
- [ ] Vérifier que le volume est connecté au service
- [ ] Vérifier que `DB_PATH` pointe bien vers le volume (`/app/data/feedny.db`)
- [ ] Tester la persistance: redéployer et vérifier les données
- [ ] Sauvegarde manuelle: `railway volume files --volume feedny-volume download /feedny.db ./backup.db`


### Optimisation Coûts

- [ ] Activer **App Sleeping** dans Settings → Usage
- [ ] Vérifier que le plan est Hobby ($5/mois)
- [ ] Surveiller les métriques dans l'onglet Metrics

### Déploiement

- [ ] Vérifier que le build réussit
- [ ] Attendre que le déploiement soit "Active"
- [ ] Obtenir l'URL publique de Railway

### Tests en Production

- [ ] Tester la page étudiante: `https://votre-app.railway.app/`
- [ ] Tester la page enseignant: `https://votre-app.railway.app/teacher`
- [ ] Tester l'authentification enseignant
- [ ] Soumettre un feedback test
- [ ] Vérifier que le feedback apparaît dans le dashboard
- [ ] Tester l'analyse IA
- [ ] Tester le wordcloud
- [ ] Tester l'export CSV
- [ ] Vérifier les logs Railway: onglet Logs

### Domaine Personnalisé (Optionnel)

- [ ] Achat d'un domaine (ex: feedny-ecole.fr)
- [ ] Ajouter le domaine dans Railway: Settings → Networking
- [ ] Configurer les DNS chez le registraire
- [ ] Activer HTTPS (Railway le fait automatiquement)
- [ ] Mettre à jour `ALLOWED_ORIGINS` avec le nouveau domaine

---

## ✅ Après le Déploiement

### Monitoring

- [ ] Surveiller les logs Railway régulièrement
- [ ] Vérifier les métriques (CPU, RAM, bandwidth)
- [ ] Surveiller les coûts dans le billing
- [ ] Configurer des alertes si nécessaire

### Maintenance

- [ ] Exporter régulièrement les CSV (backup)
- [ ] Surveiller l'utilisation de l'API DeepSeek
- [ ] Mettre à jour les variables d'environnement si nécessaire
- [ ] Garder le code à jour (security patches)

### Documentation

- [ ] Partager l'URL avec les enseignants
- [ ] Fournir le mot de passe enseignant de manière sécurisée
- [ ] Créer un guide pour les étudiants (QR code vers l'URL)
- [ ] Documenter les procédures de backup
- [ ] Documenter la procédure de reset

### Sécurité

- [ ] Changer régulièrement le mot de passe enseignant
- [ ] Vérifier que `ALLOWED_ORIGINS` ne contient pas `*`
- [ ] Surveiller les logs pour activité suspecte
- [ ] Activer les notifications Railway

---

## 🚨 Dépannage en Production

### Problème: Application ne démarre pas

- [ ] Vérifier les logs Railway
- [ ] Vérifier que toutes les variables d'environnement sont configurées
- [ ] Vérifier que le volume est attaché
- [ ] Redéployer manuellement si nécessaire

### Problème: Données perdues

- [ ] Vérifier que le volume `/app/data` est attaché
- [ ] Restaurer depuis le dernier export CSV
- [ ] Vérifier que le volume n'a pas été supprimé

### Problème: Coûts trop élevés

- [ ] Activer App Sleeping
- [ ] Vérifier que le plan est Hobby ($5/mois)
- [ ] Surveiller l'utilisation API DeepSeek
- [ ] Optimiser le nombre de feedbacks analysés

### Problème: DeepSeek API échoue

- [ ] Vérifier que `DEEPSEEK_API_KEY` est correcte
- [ ] Vérifier que la clé est active et a des crédits
- [ ] Surveiller les logs pour les erreurs API
- [ ] Considérer une autre clé API ou service

---

## 📞 Support

Si vous rencontrez des problèmes:

1. Consultez le [README.md](README.md) pour la documentation complète
2. Consultez [QUICKSTART.md](QUICKSTART.md) pour le démarrage rapide
3. Vérifiez les logs Railway pour les erreurs
4. Ouvrez une issue sur GitHub avec:
   - Description du problème
   - Logs pertinents
   - Screenshots si applicable

---

## ✨ Checklist Finale

- [ ] Application déployée et fonctionnelle
- [ ] URL partagée avec les enseignants
- [ ] Mot de passe enseignant communiqué
- [ ] Tests étudiants réussis
- [ ] Documentation complète
- [ ] Procédures de backup en place
- [ ] Coûts sous contrôle (< $5/mois)
- [ ] Monitoring configuré

**✅ Feedny est prêt à être utilisé!**
