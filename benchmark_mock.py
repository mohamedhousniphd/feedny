import time
import asyncio
import sys

def mock_create_wordcloud(text):
    time.sleep(1.0) # Simulate 1s CPU bound task
    return ("base64", {})

async def mock_analyze_feedbacks(*args, **kwargs):
    await asyncio.sleep(1.0) # Simulate 1s network latency
    return "Mock summary"

async def original_code():
    feedbacks_text = "test " * 100
    feedback_contents = ["test"] * 100
    feedback_emotions = ["happy"] * 100
    context = "test context"

    # Step 1: Generate wordcloud (synchronous)
    wordcloud_base64 = ""
    try:
        result = mock_create_wordcloud(feedbacks_text)
        if result and result[0]:
            wordcloud_base64 = result[0]
    except Exception as e:
        print(f"Wordcloud error (non-fatal): {e}")

    # Step 2: AI Analysis via DeepSeek
    summary = ""
    try:
        summary = await mock_analyze_feedbacks(
            feedbacks=feedback_contents,
            context=context,
            emotions=feedback_emotions
        )
    except Exception as e:
        print(f"DeepSeek error (non-fatal): {e}")

    return wordcloud_base64, summary

async def optimized_code():
    feedbacks_text = "test " * 100
    feedback_contents = ["test"] * 100
    feedback_emotions = ["happy"] * 100
    context = "test context"

    wordcloud_task = asyncio.to_thread(mock_create_wordcloud, feedbacks_text)
    analyze_task = asyncio.create_task(mock_analyze_feedbacks(
        feedbacks=feedback_contents,
        context=context,
        emotions=feedback_emotions
    ))

    # Run concurrently
    wordcloud_result, summary = await asyncio.gather(wordcloud_task, analyze_task)

    wordcloud_base64 = ""
    if wordcloud_result and wordcloud_result[0]:
        wordcloud_base64 = wordcloud_result[0]

    return wordcloud_base64, summary

async def main():
    print("Testing original...")
    start = time.time()
    await original_code()
    original_duration = time.time() - start
    print(f"Original duration: {original_duration:.3f}s")

    print("Testing optimized...")
    start = time.time()
    await optimized_code()
    optimized_duration = time.time() - start
    print(f"Optimized duration: {optimized_duration:.3f}s")
    print(f"Improvement: {original_duration - optimized_duration:.3f}s ({(original_duration - optimized_duration) / original_duration * 100:.1f}%)")

if __name__ == "__main__":
    asyncio.run(main())
