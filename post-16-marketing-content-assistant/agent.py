# MIT License, Copyright 2025 Packt
import os
import sys
import json
import time
from typing import Any, Dict, List

import openai
from dotenv import load_dotenv

load_dotenv()

REQUIRED_VARS = [
    "LITELLM_BASE_URL",
    "MODEL_NAME",
    "LITELLM_API_KEY",
    "PRODUCT_NAME",
    "PRODUCT_DESCRIPTION",
    "TARGET_AUDIENCE",
    "FORBIDDEN_WORDS",
    "BRAND_TONE",
    "MAX_EDITOR_RETRIES",
]


def validate_env_vars() -> None:
    """Check that all required environment variables are set, exit if not."""
    missing = [v for v in REQUIRED_VARS if not os.getenv(v)]
    if missing:
        print("Missing required environment variables:")
        for m in missing:
            print(f"  - {m}")
        sys.exit(1)


def call_llm(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 2048,
) -> str:
    """Send a completion to the configured endpoint, with exponential backoff on rate limits."""
    client = openai.OpenAI(
        base_url=os.getenv("LITELLM_BASE_URL"),
        api_key=os.getenv("LITELLM_API_KEY"),
        timeout=120.0,
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    attempt = 0
    while True:
        try:
            response = client.chat.completions.create(
                model=os.getenv("MODEL_NAME"),
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=120,
            )
            return response.choices[0].message.content
        except Exception as e:
            if "rate limit" in str(e).lower():
                attempt += 1
                if attempt >= 3:
                    raise RuntimeError("Rate limit exceeded after 3 retries. Please wait and try again.") from e
                wait = 2**attempt
                print(f"Rate limit hit. Retrying in {wait}s (attempt {attempt}/3)...")
                time.sleep(wait)
            else:
                raise


def campaign_planner(
    product_name: str, product_description: str, target_audience: str
) -> str:
    """Produce a structured campaign brief from product and audience inputs."""
    system = """You are a senior marketing strategist. Based on the product details and target audience,
create a concise campaign brief. The brief must have exactly three sections with clear labels:

1. Email angle
2. Blog angle
3. Ad copy angle"""
    user = (
        f"Product: {product_name}\n"
        f"Description: {product_description}\n"
        f"Audience: {target_audience}\n\n"
        "Write the brief now."
    )
    return call_llm(system, user, temperature=0.8)


def researcher(campaign_brief: str) -> str:
    """Return background context on the audience and product angle using the LLM's knowledge."""
    system = (
        "You are a senior market researcher. Given a campaign brief, provide relevant "
        "audience insights, pain points, and positioning context that would help a copywriter."
    )
    user = f"Campaign brief:\n{campaign_brief}\n\nProvide the research context."
    return call_llm(system, user, temperature=0.5)


def writer(
    content_type: str, campaign_brief: str, research_context: str
) -> str:
    """Draft marketing content for the given content type (email, blog, or ad)."""
    prompts = {
        "email": "You are an expert email copywriter. Write a persuasive marketing email that converts.",
        "blog": "You are an SEO blog writer. Write an engaging, keyword-optimised blog post that educates and entices.",
        "ad": "You are an ad copy specialist. Write short, punchy advertising copy for social media.",
    }
    system = prompts.get(
        content_type,
        "You are a skilled marketing copywriter. Draft compelling content.",
    )
    user = (
        f"Campaign brief:\n{campaign_brief}\n\n"
        f"Research context:\n{research_context}\n\n"
        f"Now write the {content_type} content. Only output the draft, nothing else."
    )
    return call_llm(system, user, temperature=0.8, max_tokens=1024)


def editor(draft: str, forbidden_words: List[str], brand_tone: str) -> Dict[str, Any]:
    """Score a draft for brand compliance. Returns dict with passed, score, reason."""
    system = (
        "You are a brand compliance editor. Respond ONLY with a JSON object. "
        "No markdown. No explanation. No code fences. Raw JSON only. "
        'Example: {"passed": true, "score": 85, "reason": "Tone matches."} '
        '"passed" is boolean, "score" is integer 0-100, "reason" is a short string.'
    )
    user = (
        f"Draft:\n{draft}\n\n"
        f"Forbidden words: {json.dumps(forbidden_words)}\n"
        f"Required tone: {brand_tone}\n\n"
        "Score this draft now. Output raw JSON only. No markdown. No code fences."
    )
    try:
        raw = call_llm(system, user, temperature=0.0, max_tokens=200)
        raw = raw.strip()
        if "```" in raw:
            raw = raw.split("```")[-2] if raw.count("```") >= 2 else raw.replace("```", "")
            raw = raw.replace("json", "", 1).strip()
        result = json.loads(raw)
        passed = bool(result.get("passed", False))
        score = int(result.get("score", 0))
        reason = str(result.get("reason", "No reason provided"))
        return {"passed": passed, "score": score, "reason": reason}
    except Exception as ex:
        return {
            "passed": False,
            "score": 0,
            "reason": f"Parse error: {str(ex)[:80]}",
        }


def run_campaign() -> None:
    """Orchestrate the full marketing pipeline for email, blog, and ad."""
    validate_env_vars()

    product_name = os.getenv("PRODUCT_NAME", "").strip()
    product_desc = os.getenv("PRODUCT_DESCRIPTION", "").strip()
    target_audience = os.getenv("TARGET_AUDIENCE", "").strip()
    forbidden_raw = os.getenv("FORBIDDEN_WORDS", "")
    forbidden_words = [w.strip() for w in forbidden_raw.split(",") if w.strip()]
    brand_tone = os.getenv("BRAND_TONE", "").strip()
    max_retries = int(os.getenv("MAX_EDITOR_RETRIES", "3"))

    if not all([product_name, product_desc, target_audience]):
        print("Error: PRODUCT_NAME, PRODUCT_DESCRIPTION, and TARGET_AUDIENCE must all be non-empty.")
        sys.exit(1)

    print(f"Active model: {os.getenv('MODEL_NAME')}")
    print("--- Campaign Planner ---")

    brief = campaign_planner(product_name, product_desc, target_audience)
    print(brief)

    print("--- Researcher ---")
    context = researcher(brief)
    summary = context[:200].replace("\n", " ") + "..." if len(context) > 200 else context
    print(f"Research context summary: {summary}")

    content_types = ["email", "blog", "ad"]
    for ct in content_types:
        print(f"\n=== {ct.upper()} ===")
        passed = False
        for attempt in range(1, max_retries + 1):
            draft = writer(ct, brief, context)
            evaluation = editor(draft, forbidden_words, brand_tone)
            print(
                f"Attempt {attempt}: score={evaluation['score']}, "
                f"passed={evaluation['passed']}, reason='{evaluation['reason']}'"
            )
            if evaluation["passed"]:
                passed = True
                print("Draft accepted:\n", draft)
                break
            else:
                print(f"Rejected: {evaluation['reason']}")
        if not passed:
            print(
                f"Draft did not pass brand compliance after {max_retries} attempts. "
                "Review brand constraints or adjust the product description."
            )
    print("\nCampaign complete.")


if __name__ == "__main__":
    try:
        run_campaign()
    except ConnectionError:
        print(
            "Cannot reach the configured endpoint. Verify LITELLM_BASE_URL is correct and accessible."
        )
        sys.exit(1)
    except Exception as exc:
        if "rate limit" in str(exc).lower() or "rate_limit" in str(exc).lower():
            print("The service is temporarily rate-limited. Please try again in a few minutes.")
        else:
            print(f"An unexpected error occurred: {exc}")
        sys.exit(1)