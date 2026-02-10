# Feedny - Enterprise Student Feedback & AI Synthesis Platform

<!-- Railway build trigger: updated 2026-02-10 -->

<div align="center">

![Feedny Header](https://img.shields.io/badge/Feedny-Enterprise_AI_Analysis-blue?style=for-the-badge&logo=fastapi)
<br>
![Version](https://img.shields.io/badge/Version-2.1.0_LTS-green?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104.0-009688?style=flat-square&logo=fastapi)
![SQLite](https://img.shields.io/badge/DB-SQLite_WAL-003B57?style=flat-square&logo=sqlite)
![DeepSeek](https://img.shields.io/badge/AI-DeepSeek_v3-black?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-gray?style=flat-square)

**"Closing the pedagogical feedback loop with secure, anonymous, and intelligent analysis."**

[Project Overview](#-project-overview) • [Feature Set](#-feature-set) • [Architecture](#-technical-architecture) • [Deployment](#-deployment-guide) • [Security](#-security--privacy) • [API Docs](#-api-documentation)

</div>

---

## 📖 Project Overview

**Feedny** is an enterprise-grade, multi-tenant SaaS application designed to revolutionize how educational institutions collect and process student feedback. Traditional feedback methods are often slow, identifiable, or difficult to synthesize. Feedny addresses these challenges by providing a secure, anonymous, and AI-powered platform where students can voice their opinions freely, and teachers can instantly transform hundreds of comments into strategic pedagogical insights.

### The Problem it Solves
- **Student Reticence**: Fear of identification leads to filtered or dishonest feedback.
- **Data Overload**: Assessing 50+ feedbacks manually takes hours of a teacher's limited time.
- **Fragmented Data**: Lack of a centralized history of course performance over time.

### The Feedny Solution
- **Zero-Login Anonymity**: Students interact with a simple landing page—no accounts, no tracking.
- **LLM-Powered Synthesis**: Using DeepSeek-V3 (or OpenAI), the system clusters feedback themes and suggests actionable improvements.
- **Multi-Tenant Hub**: A single deployment supports thousands of teachers, each with their own isolated data, settings, and credit balance.

---

## ✨ Feature Set

### 👨‍🏫 For Teachers (Power & Control)
- **Advanced Dashboard**: Real-time monitoring of feedback volume, time-series data, and sentiment trends.
- **Selective AI Analysis**: Curate which feedbacks are sent to the AI to optimize costs and focus on relevant issues.
- **Smart WordClouds**: Instant visual identification of the most frequent student sentiments and topics.
- **Professional PDF Reporting**: Generate high-fidelity reports for administrative reviews or self-reflection.
- **Credit Management**: A built-in credit system ensures sustainable AI usage, with referrals rewarding active users.
- **Unique Teacher Codes**: Every teacher gets a unique alphanumeric code to distribute to their classes.

### 📱 For Students (Simplicity & Privacy)
- **Ultra-Mobile First**: Optimized for one-handed operation on smartphones (where 90% of students provide feedback).
- **Emotion Tagging**: Express sentiments through high-quality emojis that feed into the teacher's sentiment analytics.
- **Haptic Feedback & Micro-animations**: A premium, responsive UI that makes giving feedback a delight.
- **Session Protection**: Intelligent device fingerprints prevent spam while maintaining 100% student anonymity.

### 🛡️ For Administrators (Governance)
- **Global Control Panel**: Manage teacher accounts, adjust credit balances, and monitor system health.
- **Invitation-Only Growth**: Secure the platform by requiring referral codes for new signups.

---

## 🏗️ Technical Architecture

Feedny is built on a high-performance asynchronous stack designed for low latency and high reliability.

### 💻 Stack Breakdown
- **Backend**: Python 3.11+ with **FastAPI**. Fully asynchronous I/O.
- **Database**: **SQLite** with **WAL (Write-Ahead Logging)** mode enabled, providing high concurrency without the overhead of a full RDBMS.
- **Frontend**: Vanila HTML5/CSS3/JS. Zero-dependency frontend ensures rapid load times and maximum compatibility.
- **AI Integration**: **DeepSeek API** (compatible with OpenAI SDK) for complex qualitative synthesis.
- **Reporting**: **ReportLab** for PDF generation and **WordCloud** for NLP-based imagery.

### 🗄️ Database Schema
The SQLite database (`feedny.db`) follows a strict relational structure to ensure multi-tenant integrity:

- **`teachers`**: Stores profile data, hashed passwords (bcrypt), unique teacher codes, and credit balances.
- **`feedbacks`**: Stores feedback content, emotion tags, and timestamps. Linked via `teacher_id`.
- **`device_limits`**: Tracks anonymized device identifiers to enforce rate limiting without storing PII.
- **`settings`**: Global and per-teacher configuration store.

---

## 🚀 Deployment Guide

### 🐳 Deployment with Docker (Preferred)
The easiest way to get Feedny up and running is via Docker.

1.  **Clone and Configure**:
    ```bash
    git clone https://github.com/mohamedhousniphd/feedny.git
    cd feedny
    cp .env.example .env
    ```
2.  **Environment Setup**: EDIT the `.env` file with your credentials (see [Configuration](#-configuration-options)).
3.  **Launch**:
    ```bash
    docker-compose up -d --build
    ```
    The app is now live at `http://localhost:8000`.

### ☁️ Cloud Deployment (Railway.app)
1.  **New Project**: Create a new project from your GitHub fork.
2.  **Volumes**: **CRITICAL** - Add a volume named `data` and mount it to `/app/data`. Feedny stores its database there.
3.  **Variable Injection**: Add `DEEPSEEK_API_KEY`, `TEACHER_PASSWORD`, etc., in the Railway variables tab.
4.  **Networking**: Railway will automatically detect the `PORT` and provide a public URL.

---

## 🔒 Security & Privacy

Feedny is built from the ground up to protect both the user (Teacher) and the subject (Student).

- **Multi-Tenant Data Silos**: Every database query is scoped by a `teacher_id`. It is computationally impossible for a teacher to view another teacher's data without administrative access.
- **JWT Authentication**: Secure sessions use JSON Web Tokens stored in `HttpOnly`, `Secure`, and `SameSite: Lax` cookies, mitigating XSS and CSRF risks.
- **PII Anonymization**: No IP addresses, names, or student emails are ever stored in the database.
- **Hash-based Fingerprinting**: Device IDs are used to prevent multiple submissions but are stored in a way that protects individual identity.

---

## 🛠️ Configuration Options

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `SECRET_KEY` | string | `FEEDNY_SECRET` | Used for JWT encryption. Change this immediately! |
| `TEACHER_PASSWORD` | string | `Teacher123` | Legacy master password (overridden by individual accounts). |
| `ADMIN_INVITE_CODE` | string | `FEEDNY2024` | Master code required for the very first teacher signups. |
| `DEEPSEEK_API_KEY` | string | `None` | Your API key from platform.deepseek.com. |
| `DEEPSEEK_BASE_URL` | url | `https://api.deepseek.com` | Base URL for the AI provider (OpenAI compatible). |
| `CREDITS_PER_SIGNUP` | integer | `3` | Number of free AI analyses given to new teachers. |
| `DATABASE_URL` | string | `sqlite:///./data/feedny.db` | Connection string for the persistence layer. |

---

## 📊 API Documentation

Feedny exposes a clean RESTful API for both internal and external integrations.

### Auth Endpoints
- `POST /api/auth/signup`: Create a new teacher account (requires `invitation_code`).
- `POST /api/auth/login`: Authenticate and receive session cookies.
- `POST /api/teacher/logout`: Terminate session and clear security cookies.

### Teacher Operations
- `GET /api/feedbacks`: List all feedbacks for the logged-in teacher.
- `POST /api/analyze`: Trigger AI synthesis (Costs 1 credit).
- `GET /api/stats`: Retrieve historical statistics and sentiment trends.

### Student Operations
- `POST /api/feedback`: Submit a new anonymous entry.
- `GET /api/status`: Check if the submission window is open for a specific teacher.

---

## 🤝 Contribution & Roadmap

Feedny is an evolving project. We welcome contributions that align with our mission of pedagogical excellence.

### 🌟 Planned Roadmap
- [ ] **Automated Payments**: Stripe integration for seamless credit refills.
- [ ] **Advanced NLP**: Multi-language sentiment analysis for non-Latin scripts.
- [ ] **Integration Hub**: Plugins for Canvas, Moodle, and Blackboard.
- [ ] **Real-time Push**: WebSocket notifications for live classroom feedback.

### 📝 How to Contribute
1. Fork the repository.
2. Create your feature branch (`git checkout -b feature/AmazingFeature`).
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`).
4. Push to the branch (`git push origin feature/AmazingFeature`).
5. Open a Pull Request.

---

## 📄 License

This project is licensed under the **MIT License**. You are free to use, modify, and distribute it for personal or commercial purposes.

---

<div align="center">

**Developed and maintained by Mohamed HOUSNI Ph.D.**

Développé avec ❤️ pour l'enseignement

[Email Contact](mailto:admin@feedny.com) | [Official Website](https://github.com/mohamedhousniphd/feedny)

<br>

*"L'éducation est l'arme la plus puissante que vous puissiez utiliser pour changer le monde."* - Nelson Mandela

</div>
