#!/usr/bin/env python3
"""Afeedny — test navigateur de bout en bout (Playwright + Chrome).

Parcourt l'interface réelle :
  étudiant  : code de session -> formulaire -> emoji -> feedback -> succès
  enseignant: connexion -> dashboard -> stats -> panneau technique
Vérifie aussi les erreurs JS, les requêtes en échec et la taille des emojis.

Usage:
    python scripts/ui_e2e.py --password "$TEACHER_PASSWORD"
    python scripts/ui_e2e.py --base-url https://afeedny.com --code HOUSNI --headed

Prérequis: pip install playwright (utilise le Chrome installé, aucun download).
"""

import argparse
import os
import sys
import uuid
from pathlib import Path

from playwright.sync_api import sync_playwright

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    RESULTS.append((name, ok, detail))
    print(f"[{'OK  ' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="https://afeedny.com")
    ap.add_argument("--code", default="HOUSNI")
    ap.add_argument("--email", default="mohamedhousni@afeedny.com")
    ap.add_argument("--password", default=os.getenv("TEACHER_PASSWORD", ""))
    ap.add_argument("--out", default="e2e-artifacts")
    ap.add_argument("--headed", action="store_true")
    args = ap.parse_args()

    if not args.password:
        print("ERREUR: --password ou TEACHER_PASSWORD requis", file=sys.stderr)
        return 2

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    base = args.base_url.rstrip("/")
    console_errors: list[str] = []
    failed_requests: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=not args.headed)
        student = browser.new_context(
            viewport={"width": 390, "height": 844},  # iPhone-ish: test mobile layout
            user_agent=(
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
            ),
            is_mobile=True,
            has_touch=True,
        )
        page = student.new_page()
        def _console(msg):
            if msg.type == "error" and "cloudflareinsights.com" not in msg.text:
                console_errors.append(msg.text)

        page.on("console", _console)
        page.on("pageerror", lambda exc: console_errors.append(str(exc)))
        def _failed(req):
            # Ignore third-party analytics blocked by local DNS/adblock
            if "cloudflareinsights.com" in req.url:
                return
            failed_requests.append(f"{req.method} {req.url}")

        page.on("requestfailed", _failed)

        # 1. Landing
        page.goto(base + "/", wait_until="networkidle")
        check("Landing chargée", "Rejoindre une session" in page.content())
        check("Placeholder du code", f"Ex: {args.code}" in page.content())
        page.screenshot(path=str(outdir / "ui-1-landing.png"), full_page=True)

        # 2. Join session
        page.fill("#code", args.code)
        page.click("button[type=submit]")
        page.wait_for_load_state("networkidle")
        check("Session ouverte", args.code.lower() in page.url.lower() or "feedback" in page.content().lower())
        check("Question IA visible", "apprendre l'IA" in page.content())
        page.screenshot(path=str(outdir / "ui-2-form.png"), full_page=True)

        # 3. Emoji size + selection
        emoji_font = page.eval_on_selector(".emoji-btn", "el => parseFloat(getComputedStyle(el).fontSize)")
        check("Emojis agrandis (>= 20px)", emoji_font >= 20, f"{emoji_font:.0f}px")
        page.click('.emoji-btn[data-emotion="9"]')
        check("Emoji sélectionné", page.eval_on_selector(".emoji-btn.selected", "el => el.dataset.emotion") == "9")

        # 4. Submit feedback through the real UI
        content = f"Test UI automatisé {uuid.uuid4().hex[:6]} — je veux apprendre les prompts et les risques de l'IA."
        page.fill("#feedback-content", content)
        page.click("#submit-btn")
        page.wait_for_selector("#success-message:not(.hidden)", timeout=30000)
        check("Feedback envoyé via l'UI", page.is_visible("#success-message"))
        page.screenshot(path=str(outdir / "ui-3-success.png"), full_page=True)

        check("Aucune erreur JS (étudiant)", not console_errors, "; ".join(console_errors[:3]))
        check("Aucune requête échouée (étudiant)", not failed_requests, "; ".join(failed_requests[:3]))
        student.close()

        # 5. Teacher dashboard
        teacher = browser.new_context(viewport={"width": 1440, "height": 1000})
        tpage = teacher.new_page()
        teacher_errors: list[str] = []
        tpage.on("console", lambda msg: teacher_errors.append(msg.text) if msg.type == "error" else None)
        tpage.on("pageerror", lambda exc: teacher_errors.append(str(exc)))

        tpage.goto(base + "/login", wait_until="networkidle")
        tpage.fill("#email", args.email)
        tpage.fill("#password", args.password)
        tpage.click("#login-btn")
        tpage.wait_for_url("**/teacher/dashboard", timeout=30000)
        tpage.wait_for_load_state("networkidle")
        check("Connexion enseignant", "/teacher/dashboard" in tpage.url)

        total = tpage.inner_text("#total-feedbacks")
        check("Compteur de feedbacks > 0", int(total) > 0, total)
        check("Panneau technique présent", "Contexte technique (anonyme)" in tpage.content())
        check("Zone dangereuse protégée", "Supprimer des feedbacks" in tpage.content())
        check("Bouton sauvegarde présent", "Sauvegarder la base" in tpage.content())
        tpage.screenshot(path=str(outdir / "ui-4-dashboard.png"), full_page=True)

        # 6. Analyse IA via l'UI (1 seul feedback pour rester rapide)
        tpage.fill("#context", "Autotest UI — formation IA")
        first_checkbox = tpage.query_selector(".feedback-checkbox")
        if first_checkbox and not first_checkbox.is_checked():
            first_checkbox.check()
        tpage.click("#analyze-btn")
        tpage.wait_for_selector("#results-section:not(.hidden)", timeout=120000)
        summary = tpage.inner_text("#summary-text")
        check("Analyse IA via l'UI", len(summary) > 80, f"{len(summary)} car.")
        check("Nuage de mots affiché", tpage.is_visible("#wordcloud-image"))
        tpage.screenshot(path=str(outdir / "ui-5-analysis.png"), full_page=True)

        check("Aucune erreur JS (enseignant)", not teacher_errors, "; ".join(teacher_errors[:3]))
        teacher.close()
        browser.close()

    failed = [r for r in RESULTS if not r[1]]
    print("\n" + "=" * 60)
    print(f"RÉSULTAT UI : {len(RESULTS) - len(failed)}/{len(RESULTS)} vérifications réussies")
    for name, _, detail in failed:
        print(f"  ✗ {name} — {detail}")
    print(f"Captures : {outdir.resolve()}")
    print("=" * 60)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
