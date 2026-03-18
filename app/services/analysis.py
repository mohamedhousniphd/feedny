import asyncio
from typing import List, Dict, Any, Tuple, Optional

from app.services.wordcloud import create_wordcloud
from app.services.deepseek import analyze_feedbacks

async def generate_analysis_content(
    feedbacks: List[Dict[str, Any]],
    context: Optional[str] = None
) -> Tuple[str, str]:
    """
    Core feedback analysis and processing logic.
    Extracts text, generates wordcloud and AI analysis concurrently.

    Args:
        feedbacks: List of feedback dictionaries containing 'content' and 'emotion'
        context: Context provided by the teacher

    Returns:
        Tuple of (summary, wordcloud_base64)
    """
    feedback_contents = [fb["content"] for fb in feedbacks]
    feedback_emotions = [fb.get("emotion") for fb in feedbacks]
    feedbacks_text = " ".join(feedback_contents)

    async def get_wordcloud() -> str:
        try:
            # Wordcloud is synchronous and CPU-intensive, offload to threadpool
            result = await asyncio.to_thread(create_wordcloud, feedbacks_text)
            if result and result[0]:
                return result[0]
        except Exception as e:
            print(f"Wordcloud error (non-fatal): {e}")
        return ""

    async def get_ai_summary() -> str:
        try:
            summary = await analyze_feedbacks(
                feedbacks=feedback_contents,
                context=context or "",
                emotions=feedback_emotions
            )
            if summary:
                return summary
        except Exception as e:
            print(f"DeepSeek error (non-fatal): {e}")
        return "L'analyse IA n'est pas disponible actuellement. Le nuage de mots a été généré."

    # Run both tasks concurrently
    wordcloud_base64, summary = await asyncio.gather(
        get_wordcloud(),
        get_ai_summary()
    )

    return summary, wordcloud_base64
