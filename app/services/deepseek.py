import os
import httpx
from typing import Optional


DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
# Latest DeepSeek model (V4.1 Flash). Override with DEEPSEEK_MODEL if needed.
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-flash")
# Reasoning effort: low keeps summaries fast and cheap ("low" | "high" | "max")
DEEPSEEK_EFFORT = os.getenv("DEEPSEEK_EFFORT", "low")


def _generate_prompts(feedbacks: list[str], context: str, emotions: Optional[list[int]] = None,
                      technical_lines: Optional[list[str]] = None) -> tuple[str, str]:
    # Combine feedbacks with emotions if available
    feedbacks_text = ""
    for i, fb in enumerate(feedbacks):
        emotion_str = ""
        if emotions and i < len(emotions) and emotions[i]:
            emotion_labels = {
                1: "très inquiet", 2: "inquiet", 3: "peu à l'aise", 4: "neutre", 5: "curieux",
                6: "intéressé", 7: "motivé", 8: "très motivé", 9: "enthousiaste", 10: "très enthousiaste"
            }
            emotion_str = f" [État émotionnel: {emotion_labels.get(emotions[i], 'inconnu')}]"
        feedbacks_text += f"- {fb}{emotion_str}\n"

    # Calculate emotion summary if available
    emotion_summary = ""
    if emotions:
        valid_emotions = [e for e in emotions if e is not None]
        if valid_emotions:
            avg_emotion = sum(valid_emotions) / len(valid_emotions)
            emotion_summary = f"\n\nRésumé émotionnel: Moyenne {avg_emotion:.1f}/10 sur {len(valid_emotions)} réponses."

    # Optimized prompt for faster and more accurate analysis
    system_prompt = """Tu es un assistant pédagogique expert qui analyse les feedbacks des étudiants.

Ta tâche:
- Analyser les feedbacks fournis rapidement et précisément
- Identifier les thèmes principaux et patterns
- Générer un résumé structuré et actionnable
- Prendre en compte l'état émotionnel des étudiants si fourni

Format de réponse (sois concis):
1. **Résumé général** (2-3 phrases max)
2. **Points positifs** (liste courte)
3. **Points à améliorer** (liste courte)
4. **Recommandations** (2-3 actions concrètes)

Écris en français. Sois direct et concis."""

    technical_block = ""
    if technical_lines:
        technical_block = (
            "\nContexte technique anonyme (collecté passivement, sans consentement "
            "spécifique : type d'appareil, navigateur, réseau, durée de rédaction):\n"
            + "\n".join(f"- {line}" for line in technical_lines)
            + "\nUtilise ces éléments pour nuancer les recommandations "
            "(ex: majorité sur mobile -> supports légers ; réseau lent -> éviter les vidéos lourdes).\n"
        )

    user_prompt = f"""Contexte: {context if context else "Non spécifié"}

Feedbacks des étudiants:
{feedbacks_text}{emotion_summary}
{technical_block}
Génère un résumé concis et actionnable."""

    return system_prompt, user_prompt


def _create_payload(system_prompt: str, user_prompt: str, max_tokens: int) -> dict:
    return {
        "model": DEEPSEEK_MODEL,
        "effort": DEEPSEEK_EFFORT,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "stream": False,
        "max_tokens": max_tokens,
        "temperature": 0.3  # Lower temperature for more consistent results
    }


async def analyze_feedbacks(
    feedbacks: list[str],
    context: str,
    max_tokens: int = 1200,
    emotions: Optional[list[int]] = None,
    technical_lines: Optional[list[str]] = None
) -> Optional[str]:
    """
    Analyze feedbacks using DeepSeek API with optimized settings.

    Args:
        feedbacks: List of feedback texts
        context: Context provided by the teacher
        max_tokens: Maximum tokens for the response (reduced for faster response)
        emotions: Optional list of emotion values (1-10) corresponding to feedbacks

    Returns:
        Generated summary or None if failed
    """
    if not DEEPSEEK_API_KEY:
        print("Warning: DEEPSEEK_API_KEY is not configured")
        return None

    if not feedbacks:
        print("Warning: No feedbacks to analyze")
        return None

    system_prompt, user_prompt = _generate_prompts(feedbacks, context, emotions, technical_lines)
    payload = _create_payload(system_prompt, user_prompt, max_tokens)

    try:
        # Increased timeout for reliability, reduced temperature for consistency
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{DEEPSEEK_BASE_URL}/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
                },
                json=payload
            )

            if response.status_code == 200:
                data = response.json()
                message = data["choices"][0]["message"]
                content = (message.get("content") or "").strip()
                if not content:
                    # Reasoning models may return only reasoning_content when truncated
                    content = (message.get("reasoning_content") or "").strip()
                return content or None
            else:
                print(f"DeepSeek API error: {response.status_code} - {response.text}")
                return None

    except Exception as e:
        print(f"Error calling DeepSeek API: {e}")
        return None

