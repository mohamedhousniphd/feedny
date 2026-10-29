#!/usr/bin/env python3
"""Afeedny — test de bout en bout (A → Z) sur une instance live.

Flux testé :
  1. Santé de l'API (/health, /healthz, /api/status)
  2. Connexion enseignant/admin
  3. Page d'accueil + code de session (HOUSNI)
  4. Soumission de feedbacks étudiants (avec émotions)
  5. Sélection des feedbacks à analyser
  6. Analyse IA (DeepSeek flash) + nuage de mots
  7. Statistiques
  8. Exports CSV / JSON
  9. Génération du rapport PDF

Usage:
    python scripts/e2e_autotest.py --password "$TEACHER_PASSWORD"
    python scripts/e2e_autotest.py --base-url https://afeedny.com --code HOUSNI --keep

Options:
    --base-url   URL de l'app (défaut: https://afeedny.com)
    --email      Compte admin (défaut: mohamedhousni@afeedny.com)
    --password   Mot de passe admin (ou env TEACHER_PASSWORD)
    --code       Code de session à tester (défaut: HOUSNI)
    --count      Nombre de feedbacks de démo (défaut: 8)
    --keep       Conserver les feedbacks de démo (défaut: nettoyage via /api/reset)
    --out        Dossier de sortie des artefacts (défaut: ./e2e-artifacts)
"""

import argparse
import base64
import json
import os
import re
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

import httpx

DEMO_FEEDBACKS = [
    ("J'utilise déjà ChatGPT pour préparer mes cours et gagner du temps sur les exercices.", 8),
    ("Je ne sais pas trop ce qu'est l'IA, j'aimerais comprendre les bases et les risques.", 5),
    ("L'IA me fait un peu peur, surtout pour la triche et la fiabilité des réponses.", 3),
    ("J'aimerais apprendre à rédiger de bons prompts pour mes projets et mes exposés.", 7),
    ("Je veux savoir comment l'IA peut m'aider à réviser plus efficacement.", 8),
    ("Les outils d'IA sont utiles mais je perds du temps, il me faut une méthode claire.", 5),
    ("Je suis très intéressé par la création d'images et de présentations avec l'IA.", 9),
    ("Je souhaite une formation pratique, avec des exemples concrets et de l'éthique.", 7),
    ("L'IA devrait nous aider à personnaliser l'apprentissage selon chaque étudiant.", 6),
    ("Je veux comprendre comment vérifier les sources et éviter les fausses informations.", 4),
]

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    RESULTS.append((name, ok, detail))
    icon = "OK  " if ok else "FAIL"
    print(f"[{icon}] {name}" + (f" — {detail}" if detail else ""))
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="https://afeedny.com")
    ap.add_argument("--email", default="mohamedhousni@afeedny.com")
    ap.add_argument("--password", default=os.getenv("TEACHER_PASSWORD", ""))
    ap.add_argument("--code", default=os.getenv("ADMIN_CODE", "HOUSNI"))
    ap.add_argument("--count", type=int, default=8)
    ap.add_argument("--keep", action="store_true")
    ap.add_argument("--out", default="e2e-artifacts")
    args = ap.parse_args()

    if not args.password:
        print("ERREUR: mot de passe manquant (--password ou TEACHER_PASSWORD)", file=sys.stderr)
        return 2

    base = args.base_url.rstrip("/")
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    client = httpx.Client(base_url=base, timeout=120.0, follow_redirects=False)
    t0 = time.time()

    # 1. Santé
    for path in ("/health", "/healthz"):
        r = client.get(path)
        ok = r.status_code == 200 and r.json().get("status") == "healthy"
        check(f"GET {path}", ok, f"{r.status_code}")
    r = client.get("/api/status")
    check("GET /api/status (collecte ouverte)", r.status_code == 200, r.text[:80])

    # 2. Landing = session
    r = client.get("/")
    html = r.text
    check("Landing: bouton 'Rejoindre une session'", "Rejoindre une session" in html)
    check("Landing: placeholder du code", f"Ex: {args.code}" in html)
    check("Landing: pas de 'cours' résiduel", "Code du cours" not in html and "Rejoindre un cours" not in html)

    # 3. Connexion admin
    r = client.post(
        "/api/auth/login",
        data={"username": args.email, "password": args.password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    logged = r.status_code == 200
    check("POST /api/auth/login", logged, f"{r.status_code}")
    if not logged:
        _summary()
        return 1

    # 4. Session + question IA
    r = client.get(f"/?code={args.code}")
    check(f"GET /?code={args.code} (session admin)", r.status_code == 200, f"{r.status_code}")
    check("Question IA affichée aux étudiants", "attentes concernant l&#x27;IA" in r.text or "attentes concernant l'IA" in r.text)

    r = client.get("/api/question")
    question = r.json().get("question", "")
    check("GET /api/question", r.status_code == 200 and "IA" in question, question[:70])

    r = client.get("/api/admin/teachers")
    teachers = r.json().get("teachers", [])
    admin = next((t for t in teachers if t["email"] == args.email), {})
    check("Code de session = " + args.code, admin.get("unique_code") == args.code, str(admin.get("unique_code")))
    check("Compte admin (is_admin)", bool(admin.get("is_admin")))

    # 4b. Contexte technique anonyme (page d'ouverture de session)
    html_form = client.get(f"/?code={args.code}").text
    check("Formulaire étudiant pointe sur /api/feedback", 'fetch(\'/api/feedback\'' in html_form)
    device_ctx = {
        "userAgent": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36",
        "platform": "Linux armv8l",
        "language": "fr-MA",
        "timezone": "Africa/Casablanca",
        "screen": [1080, 2400],
        "viewport": [412, 915],
        "connectionType": "3g",
        "downlink": 1.5,
        "rtt": 300,
        "saveData": False,
        "touch": True,
        "memory": 4,
        "cores": 8,
        "firstInputSeconds": 4.2,
        "typingSeconds": 38.0,
        "totalSeconds": 47.5,
        "keystrokes": 142,
        "backspaces": 11,
        "pasted": False,
        "pasteChars": 0,
        "idleSeconds": 9.3,
    }
    r = client.post("/api/client-info", json={"client_info": device_ctx})
    check("POST /api/client-info (join)", r.status_code == 200, r.text[:60])

    # 5. Feedbacks étudiants (un device par feedback)
    created_ids: list[int] = []
    demo = (DEMO_FEEDBACKS * ((args.count // len(DEMO_FEEDBACKS)) + 1))[: args.count]
    for content, emotion in demo:
        client.cookies.set("device_id", str(uuid.uuid4()))
        r = client.post("/api/feedback", json={
            "content": content,
            "emotion": emotion,
            "client_info": device_ctx,
            "fill_seconds": 42.0,
        })
        if r.status_code in (200, 201):
            created_ids.append(r.json().get("id"))
        else:
            check(f"POST /api/feedback ({content[:24]}…)", False, f"{r.status_code} {r.text[:80]}")
            break
    check(f"Création de {len(created_ids)} feedbacks démo", len(created_ids) == len(demo), str(len(created_ids)))

    # 6. Statistiques
    r = client.get("/api/stats")
    stats = r.json() if r.status_code == 200 else {}
    check("GET /api/stats", r.status_code == 200 and stats.get("total", 0) >= len(created_ids), json.dumps(stats))

    # 7. Sélection pour analyse
    toggled = 0
    for fid in created_ids:
        r = client.put(f"/api/feedbacks/{fid}/toggle")
        if r.status_code == 200:
            toggled += 1
    check("Sélection des feedbacks (toggle)", toggled == len(created_ids), f"{toggled}/{len(created_ids)}")

    # 8. Analyse IA + nuage de mots
    t1 = time.time()
    r = client.post(
        "/api/analyze",
        json={"feedback_ids": created_ids, "context": "Formation à l'IA : besoins, intérêts et attentes"},
    )
    elapsed = time.time() - t1
    analysis = r.json() if r.status_code == 200 else {}
    summary = analysis.get("summary", "")
    wordcloud_b64 = (analysis.get("wordcloud_data") or {}).get("image", "") or analysis.get("wordcloud") or ""
    check("POST /api/analyze", r.status_code == 200, f"{r.status_code} en {elapsed:.1f}s")
    check("Résumé IA généré (non vide)", len(summary) > 120, f"{len(summary)} car.")
    check("Résumé IA non dégradé", "pas disponible actuellement" not in summary.lower())
    technical = analysis.get("technical") or {}
    check("Contexte technique renvoyé par l'analyse", bool(technical.get("lines")), f"{len(technical.get('lines') or [])} ligne(s)")
    check("Nuage de mots (base64 PNG)", wordcloud_b64.startswith("data:image/png;base64,") or wordcloud_b64.startswith("iVBOR"), f"{len(wordcloud_b64)} car.")

    if wordcloud_b64:
        payload = wordcloud_b64.split(",", 1)[-1]
        png = base64.b64decode(payload)
        png_path = outdir / f"wordcloud-{stamp}.png"
        png_path.write_bytes(png)
        check("Fichier nuage de mots écrit", png[:8] == b"\x89PNG\r\n\x1a\n", str(png_path))

    # 9. Exports
    r = client.get("/api/export/csv")
    csv_ok = r.status_code == 200 and len(r.text.strip().splitlines()) >= 2
    (outdir / f"export-{stamp}.csv").write_text(r.text, encoding="utf-8")
    check("GET /api/export/csv", csv_ok, f"{len(r.text)} car.")

    r = client.get("/api/export/json")
    json_ok = r.status_code == 200 and len(r.json().get("feedbacks", [])) >= len(created_ids)
    (outdir / f"export-{stamp}.json").write_text(r.text, encoding="utf-8")
    check("GET /api/export/json", json_ok, f"{len(r.text)} car.")

    # 10. Rapport PDF
    if wordcloud_b64 and summary:
        r = client.post(
            "/api/export/pdf",
            json={
                "wordcloud_image": wordcloud_b64,
                "analysis_text": summary,
                "context": "Formation à l'IA",
                "technical": technical,
            },
        )
        pdf_ok = r.status_code == 200 and r.content[:5] == b"%PDF-"
        if pdf_ok:
            (outdir / f"rapport-{stamp}.pdf").write_bytes(r.content)
        check("POST /api/export/pdf (rapport)", pdf_ok, f"{len(r.content)} octets, {r.status_code}")

    # 10b. Insights techniques
    r = client.get("/api/insights/technical")
    insights = (r.json() or {}).get("insights", {}) if r.status_code == 200 else {}
    check(
        "GET /api/insights/technical",
        r.status_code == 200 and insights.get("submits", 0) >= len(created_ids),
        f"joins={insights.get('joins')} submits={insights.get('submits')} conv={insights.get('conversion_rate')}%",
    )

    # 11. Historique des analyses
    r = client.get("/api/analyses")
    analyses = r.json().get("analyses", []) if r.status_code == 200 else []
    check("GET /api/analyses (historique)", r.status_code == 200 and len(analyses) >= 1, f"{len(analyses)} entrée(s)")

    # 12. Modèle DeepSeek utilisé par l'app
    key = os.getenv("DEEPSEEK_API_KEY", "")
    if key:
        try:
            mr = httpx.get(
                "https://api.deepseek.com/models",
                headers={"Authorization": f"Bearer {key}"},
                timeout=30.0,
            )
            ids = [m["id"] for m in mr.json().get("data", [])]
            check("Modèles DeepSeek disponibles", "deepseek-flash" in ids, ", ".join(ids))
        except Exception as exc:  # noqa: BLE001
            check("Modèles DeepSeek disponibles", False, str(exc))

    # 13. Sauvegardes (persistance)
    r = client.post("/api/backup")
    backup_ok = r.status_code == 200 and bool((r.json() or {}).get("backup"))
    check("POST /api/backup (snapshot base)", backup_ok, (r.json().get("backup") or {}).get("name", r.text[:60]))
    r = client.get("/api/backups")
    check("GET /api/backups", r.status_code == 200 and r.json().get("count", 0) >= 1, f"{r.text[:80]}")

    # 14. Suppression protégée
    r = client.post("/api/reset")
    check("POST /api/reset sans confirmation refusé", r.status_code == 400, r.text[:80])

    # 15. Nettoyage (jamais silencieux : confirmation + sauvegarde)
    if not args.keep:
        r = client.post("/api/reset", json={"confirm": "SUPPRIMER"})
        backup_name = (r.json() or {}).get("backup", "")
        r2 = client.get("/api/stats")
        check(
            "Nettoyage confirmé + sauvegarde auto",
            r.status_code == 200 and r2.json().get("total") == 0 and bool(backup_name),
            f"backup={backup_name or '—'} restant={r2.json().get('total')}",
        )

    duration = time.time() - t0
    print(f"\nDurée totale : {duration:.1f}s — artefacts : {outdir.resolve()}")
    return _summary()


def _summary() -> int:
    failed = [r for r in RESULTS if not r[1]]
    print("\n" + "=" * 60)
    print(f"RÉSULTAT : {len(RESULTS) - len(failed)}/{len(RESULTS)} vérifications réussies")
    for name, _, detail in failed:
        print(f"  ✗ {name} — {detail}")
    print("=" * 60)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
