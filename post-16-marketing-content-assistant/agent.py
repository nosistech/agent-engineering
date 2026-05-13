# MIT License, Copyright 2025 Packt

import json
import os
import sys
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
REQUIRED_ENV = (
    "LITELLM_BASE_URL",
    "MODEL_NAME",
    "LITELLM_API_KEY",
    "PRODUCT_NAME",
    "PRODUCT_DESCRIPTION",
    "TARGET_AUDIENCE",
)


def load_env():
    env_file = ROOT / ".env"
    if not env_file.exists():
        return

    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def chat(system, user, temperature=0.7):
    body = json.dumps(
        {
            "model": os.getenv("MODEL_NAME"),
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
        }
    ).encode("utf-8")

    request = Request(
        os.getenv("LITELLM_BASE_URL").rstrip("/") + "/chat/completions",
        data=body,
        headers={
            "Authorization": "Bearer " + os.getenv("LITELLM_API_KEY"),
            "Content-Type": "application/json",
        },
    )
    with urlopen(request, timeout=120) as response:
        data = json.loads(response.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"].strip()


def campaign_brief():
    return chat(
        "You are a senior marketing strategist. Create a concise campaign brief "
        "with exactly three labeled sections: Email angle, Blog angle, Ad copy angle.",
        f"Product: {os.getenv('PRODUCT_NAME')}\n"
        f"Description: {os.getenv('PRODUCT_DESCRIPTION')}\n"
        f"Audience: {os.getenv('TARGET_AUDIENCE')}",
    )


def research(brief):
    return chat(
        "You are a market researcher. Return concise audience pain points and "
        "positioning context for a copywriter.",
        f"Campaign brief:\n{brief}",
        temperature=0.4,
    )


def write_draft(content_type, brief, context):
    prompts = {
        "email": "Write one persuasive marketing email.",
        "blog": "Write one short educational blog post.",
        "ad": "Write three short social ad options.",
    }
    return chat(
        "You are a marketing copywriter. Only output the requested draft.",
        f"{prompts[content_type]}\n\nBrief:\n{brief}\n\nResearch:\n{context}",
        temperature=0.8,
    )


def edit(draft):
    raw = chat(
        "You are a brand editor. Return only JSON with passed, score, and reason. "
        "Set passed to true only when the score is 80 or higher and no forbidden "
        "words appear.",
        f"Forbidden words: {os.getenv('FORBIDDEN_WORDS', '')}\n"
        f"Required tone: {os.getenv('BRAND_TONE', 'friendly and authoritative')}\n\n"
        f"Draft:\n{draft}",
        temperature=0,
    )
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        result = json.loads(raw)
        score = int(result.get("score", 0))
        forbidden = [word.strip().lower() for word in os.getenv("FORBIDDEN_WORDS", "").split(",")]
        blocked = [word for word in forbidden if word and word in draft.lower()]
        return {
            "passed": bool(result.get("passed")) and score >= 80 and not blocked,
            "score": score,
            "reason": "Forbidden words found: " + ", ".join(blocked)
            if blocked
            else str(result.get("reason", "No reason provided")),
        }
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        return {"passed": False, "score": 0, "reason": f"Editor JSON error: {error}"}


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    load_env()

    missing = [key for key in REQUIRED_ENV if not os.getenv(key)]
    if missing:
        raise SystemExit(f"Missing environment variables: {', '.join(missing)}")

    brief = campaign_brief()
    context = research(brief)
    retries = int(os.getenv("MAX_EDITOR_RETRIES", "3"))

    print("CAMPAIGN BRIEF")
    print(brief)
    print("\nRESEARCH SUMMARY")
    print(context)

    for content_type in ("email", "blog", "ad"):
        print(f"\n{content_type.upper()} DRAFT")
        for attempt in range(1, retries + 1):
            draft = write_draft(content_type, brief, context)
            review = edit(draft)
            print(f"Attempt {attempt}: score={review['score']}, passed={review['passed']}")
            if review["passed"] or attempt == retries:
                print(draft)
                if not review["passed"]:
                    print(f"Editor note: {review['reason']}")
                break


if __name__ == "__main__":
    main()
