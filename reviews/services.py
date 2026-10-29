import json
import logging
import os

logger = logging.getLogger(__name__)


def _fallback(reviews):
    """Rating-based summary, used when no API key is set or the LLM call fails."""
    avg = sum(r.rating for r in reviews) / len(reviews)
    sentiment = "positive" if avg >= 4 else "negative" if avg <= 2 else "mixed"
    return {
        "sentiment": sentiment,
        "average_rating": round(avg, 2),
        "summary": f"{len(reviews)} reviews with an average rating of {avg:.1f}/5.",
        "pros": [],
        "cons": [],
        "source": "fallback",
    }


def summarize_reviews(product, reviews):
    reviews = list(reviews)[:50]
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return _fallback(reviews)

    review_lines = "\n".join(f"- ({r.rating}/5) {r.text}" for r in reviews)
    prompt = (
        f"Product: {product.brand} {product.name}\n"
        f"Customer reviews:\n{review_lines}\n\n"
        "Summarize these reviews. Respond ONLY with JSON in this exact shape:\n"
        '{"sentiment": "positive|mixed|negative", "summary": "2 sentences", '
        '"pros": ["..."], "cons": ["..."]}'
    )

    try:
        from google import genai

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            contents=prompt,
            config={"response_mime_type": "application/json"},
        )
        data = json.loads(response.text)
        data["average_rating"] = round(sum(r.rating for r in reviews) / len(reviews), 2)
        data["source"] = "llm"
        return data
    except Exception:
        logger.exception("LLM summary failed, using fallback")
        return _fallback(reviews)