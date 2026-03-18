import asyncio
from typing import Optional, Dict, Any, Tuple
from app.services.wordcloud import create_wordcloud
from app.services.deepseek import analyze_feedbacks

async def process_feedback_analysis(
    feedbacks: list[Dict[str, Any]],
    context: str
) -> Tuple[str, str]:
    """
    Process feedback analysis by generating a wordcloud and an AI summary concurrently.

    Args:
        feedbacks: A list of dictionaries representing feedbacks, containing 'content' and 'emotion'.
        context: The context string provided by the teacher.

    Returns:
        A tuple of (wordcloud_base64, summary)
    """
    # Extract content and emotions
    feedbacks_text = " ".join([fb["content"] for fb in feedbacks])
    feedback_contents = [fb["content"] for fb in feedbacks]
    feedback_emotions = [fb.get("emotion") for fb in feedbacks]

    # Run wordcloud generation in a separate thread since it's a CPU-bound/blocking task
    async def get_wordcloud():
        try:
            # create_wordcloud is synchronous, so we offload it
            result = await asyncio.to_thread(create_wordcloud, feedbacks_text)
            if result and result[0]:
                return result[0]
            return ""
        except Exception as e:
            print(f"Wordcloud error (non-fatal): {e}")
            return ""

    # Run DeepSeek analysis
    async def get_summary():
        try:
            summary = await analyze_feedbacks(
                feedbacks=feedback_contents,
                context=context,
                emotions=feedback_emotions
            )
            if summary:
                return summary
            return "L'analyse IA n'est pas disponible actuellement. Le nuage de mots a été généré."
        except Exception as e:
            print(f"DeepSeek error (non-fatal): {e}")
            return "L'analyse IA n'est pas disponible actuellement. Le nuage de mots a été généré."

    # Execute both tasks concurrently
    wordcloud_task = asyncio.create_task(get_wordcloud())
    summary_task = asyncio.create_task(get_summary())

    wordcloud_base64, summary = await asyncio.gather(wordcloud_task, summary_task)

    return wordcloud_base64, summary
