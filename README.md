# Rapport de Projet de Fin d'Études : Feedny
## Système Intelligent de Collecte et d'Analyse de Feedback Pédagogique

<!-- Mise à jour du déclencheur de build Railway : 2026-02-10 -->

<div align="center">

![Badge Feedny](https://img.shields.io/badge/Projet-Feedny_Pédagogie-blue?style=for-the-badge)
<br>
**Auteur : Mohamed HOUSNI Ph.D.**

---

### Résumé (Abstract)

*Ce document présente le développement de Feedny, une plateforme web innovante conçue pour optimiser l'interaction entre les enseignants et les étudiants. En utilisant des technologies de pointe telles que l'intelligence artificielle (IA) et l'architecture multi-utilisateurs (multi-tenancy), ce projet propose une solution robuste au défi de la collecte de feedbacks anonymes et de leur synthèse pédagogique. Ce chapitre détaille la conception, l'implémentation et les perspectives de cette plateforme.*

</div>

---

## 📖 Table des Matières

1. [Remerciements](#-remerciements)
2. [Introduction Générale](#-introduction-générale)
3. [Contexte et Problématique](#-contexte-et-problématique)
4. [Analyse Fonctionnelle](#-analyse-fonctionnelle)
5. [Architecture Technique et Implémentation](#-architecture-technique-et-implémentation)
6. [Sécurité et Confidentialité](#-sécurité-et-confidentialité)
7. [Guide de Déploiement et d'Installation](#-guide-de-déploiement-et-dinstallation)
8. [Résultats et Analyse des Coûts](#-résultats-et-analyse-des-coûts)
9. [Conclusion et Perspectives](#-conclusion-et-perspectives)
10. [Références Bibliographiques](#-références-bibliographiques)
11. [Annexes](#-annexes)

---

## 🙏 Remerciements

Je tiens à exprimer ma gratitude envers tous ceux qui ont contribué, de près ou de loin, à la réalisation de ce projet de recherche et développement. Un merci tout particulier aux institutions académiques et aux collègues enseignants dont les retours sur le terrain ont permis d'affiner les fonctionnalités de Feedny pour mieux répondre aux besoins réels des salles de classe modernes.

---

## 1. Introduction Générale

Dans le paysage éducatif contemporain, le feedback étudiant est reconnu comme un levier majeur de l'amélioration de la qualité de l'enseignement. Cependant, la collecte de ces données précieuses se heurte souvent à des obstacles psychologiques (crainte d'identification) et logistiques (temps de traitement). **Feedny** émerge comme une réponse technologique à ces défis, offrant un environnement sécurisé et intelligent pour transformer la "voix de l'étudiant" en stratégie d'enseignement concrète.

---

## 2. Contexte et Problématique

### 2.1 Le Défi du Feedback Anonyme
Le manque de sincérité est le principal biais des évaluations classiques. Pour obtenir une critique constructive, l'anonymat absolu est une condition *sine qua non*. Feedny garantit cet anonymat à travers une architecture qui ne conserve aucune donnée nominative étudiante.

### 2.2 La Charge Cognitive de l'Enseignant
Traiter manuellement des centaines de commentaires après chaque séance est une tâche chronophage. L'intégration d'un modèle de langage (LLM) permet de synthétiser ces données en quelques secondes, dégageant ainsi du temps pour l'action pédagogique.

---

## 3. Analyse Fonctionnelle

### 3.1 Profil Étudiant (Simplicité et Accessibilité)
- **Accès par Code** : L'étudiant accède au formulaire via un code unique fourni par l'enseignant.
- **Formulaire Minimaliste** : Zone de saisie limitée à 240 caractères pour encourager la concision.
- **Gestion des Émotions** : Sélection d'emojis pour une analyse quantitative immédiate du ressenti.

### 3.2 Profil Enseignant (Gestion et Analyse)
- **Tableau de Bord Personnel** : Chaque enseignant dispose de son espace propre (multi-tenancy).
- **Filtrage Intelligent** : Possibilité de sélectionner les feedbacks les plus pertinents pour l'analyse IA.
- **Génération de Nuages de Mots** : Visualisation instantanée des mots-clés prédominants.
- **Exportation des Résultats** : Téléchargement des analyses en format PDF ou CSV pour archivage.

### 3.3 Système d'Invitation et de Crédits
Pour assurer la viabilité du service, un système de crédits gère les appels aux API d'intelligence artificielle. Un système d'invitation permet une croissance contrôlée de la communauté enseignante.

---

## 4. Architecture Technique et Implémentation

### 4.1 Stack Technologique
Le choix des technologies a été guidé par des impératifs de performance et de légèreté :
- **Backend** : FastAPI (Python), choisi pour son asynchronisme natif.
- **Base de Données** : SQLite avec mode WAL pour une gestion robuste des écritures concurrentes.
- **IA** : DeepSeek-V3, utilisé pour sa grande précision dans les résumés pédagogiques.
- **Frontend** : HTML5/JS/CSS pur (Vanille), garantissant une compatibilité maximale sans lourdeur de frameworks.

### 4.2 Structure du Projet
```text
feedny/
├── app/
│   ├── main.py         # Logique API et routage
│   ├── auth.py         # Gestion de la sécurité (JWT)
│   ├── database.py     # Manipulation des données SQLite
│   ├── models.py       # Schémas de données (Pydantic)
│   └── static/         # Interfaces utilisateurs (HTML/JS/CSS)
├── data/               # Stockage persistant de la base de données
├── Dockerfile          # Conteneurisation du système
└── docker-compose.yml  # Orchestration multi-conteneurs
```

---

## 5. Sécurité et Confidentialité

Le respect de la vie privée est au cœur de Feedny :
- **Isolation des Données** : Les données sont compartimentées par `teacher_id`. Un enseignant ne peut en aucun cas accéder aux données d'un collègue.
- **Sécurité JWT** : L'authentification repose sur des JSON Web Tokens stockés dans des cookies `HttpOnly`, protégeant contre les attaques XSS.
- **Fingerprinting** : Utilisation d'identifiants d'appareils hachés pour limiter les abus sans identifier l'individu.

---

## 6. Guide de Déploiement et d'Installation

### 6.1 Installation via Docker (Recommandé)
1. Télécharger le dépôt.
2. Configurer le fichier `.env` à partir de `.env.example`.
3. Lancer la commande :
   ```bash
   docker-compose up --build
   ```

### 6.2 Déploiement Cloud (Railway)
- Créer un projet Railway lié au dépôt GitHub.
- Ajouter un volume pour le répertoire `/app/data`.
- Configurer les variables d'environnement (`SECRET_KEY`, `DEEPSEEK_API_KEY`).

---

## 7. Résultats et Analyse des Coûts

Feedny a été optimisé pour un coût d'exploitation minimal :
- **Hébergement** : ~2-5$ / mois (en fonction de l'usage).
- **Analyse IA** : Coût négligeable grâce à l'efficacité du modèle DeepSeek (environ 0.01$ par analyse complète).

---

## 8. Conclusion et Perspectives

### 8.1 Synthèse
Feedny démontre qu'une application légère et ciblée peut transformer radicalement l'interaction pédagogique. Le passage réussi à une architecture multi-utilisateurs permet désormais une mise à l'échelle pour des institutions complètes.

### 8.2 Perspectives Futures
- **Intégration LTI** : Pour une connexion directe avec Moodle ou Canvas.
- **Analyse de Sentiment Avancée** : Détection automatique du ton des messages.
- **Multi-langage** : Support complet de l'arabe et de l'anglais pour une portée internationale.

---

## 9. Références Bibliographiques

1. **Hattie, J., & Timperley, H. (2007)**. *The Power of Feedback*. Review of Educational Research.
2. **FastAPI Documentation**. https://fastapi.tiangolo.com
3. **DeepSeek AI Research**. https://platform.deepseek.com
4. **SQLite Optimization**. https://www.sqlite.org/wal.html

---

## 10. Annexes

### Annexe A : Schéma de la Base de Données
- Table `teachers` : `id, name, email, password_hash, unique_code, credits`.
- Table `feedbacks` : `id, teacher_id, content, emotion, timestamp`.

### Annexe B : Guide d'Utilisation Enseignant
1. Se connecter au dashboard.
2. Partager le code unique avec les étudiants.
3. Attendre la fin de la séance.
4. Cocher les feedbacks et cliquer sur "Analyser".

---

<div align="center">

**Développé avec ❤️ pour l'enseignement**

**Mohamed HOUSNI Ph.D.**

[Contact](mailto:admin@feedny.com) | [GitHub](https://github.com/mohamedhousniphd/feedny)

*"L'éducation est l'arme la plus puissante que vous puissiez utiliser pour changer le monde."*

</div>
