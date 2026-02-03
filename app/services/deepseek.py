import os
import httpx
from typing import Optional


DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")


async def analyze_feedbacks(
    feedbacks: list[str],
    context: str,
    max_tokens: int = 1000
) -> Optional[str]:
    """
    Analyze feedbacks using DeepSeek API.

    Args:
        feedbacks: List of feedback texts
        context: Context provided by the teacher
        max_tokens: Maximum tokens for the response

    Returns:
        Generated summary or None if failed
    """
    if not DEEPSEEK_API_KEY:
        raise ValueError("DEEPSEEK_API_KEY is not configured")

    if not feedbacks:
        raise ValueError("No feedbacks to analyze")

    # Combine feedbacks
    feedbacks_text = "\n\n".join([f"- {fb}" for fb in feedbacks])

    # Create prompt
    system_prompt = """Tu es un assistant pédagogique expert qui analyse les feedbacks des étudiants.

Ta tâche:
- Analyser les feedbacks fournis
- Identifier les thèmes principaux et les points clés
- Générer un résumé concis et informatif (maximum une page)
- Mettre en évidence les forces et les domaines d'amélioration
- Maintenir un ton constructif et professionnel

Format de réponse:
1. Résumé général (2-3 phrases)
2. Points positifs principaux
3. Points à améliorer
4. Recommandations pour l'enseignant

Écris en français."""

    user_prompt = f"""Contexte: {context}

Feedbacks des étudiants:
{feedbacks_text}

Génère un résumé concis et informatif."""

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{DEEPSEEK_BASE_URL}/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "stream": False,
                    "max_tokens": max_tokens,
                    "temperature": 0.7
                }
            )

            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]
            else:
                print(f"DeepSeek API error: {response.status_code} - {response.text}")
                return None

    except Exception as e:
        print(f"Error calling DeepSeek API: {e}")
        return None
