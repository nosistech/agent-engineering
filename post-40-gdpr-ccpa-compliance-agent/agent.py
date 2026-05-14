# (c) 2026 NosisTech LLC. Original implementation.
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI, OpenAIError


SYSTEM_PROMPT = """
You are reviewing a fictional data processing activity for educational GDPR and CCPA screening.
This is not legal advice and does not certify compliance.

Use this simplified checklist:
- GDPR: flag unclear lawful basis, special category data, unclear retention, high-risk profiling or automated decisions, cross-border transfer concerns, and missing data subject rights process.
- CCPA: flag unclear applicability, sale or sharing of personal information, missing opt-out path, sensitive personal information, and missing consumer rights process.

Return only JSON:
{
  "risk_level": "LOW | MEDIUM | HIGH",
  "gdpr_flags": ["short flag"],
  "ccpa_flags": ["short flag"],
  "review_questions": ["question a human reviewer should ask next"],
  "summary": "short cautious summary"
}
"""

DEMOS = [
    {
        "label": "Basic newsletter",
        "activity": "Fictional company Alder Books collects email addresses for a monthly newsletter. Users opt in through a form, can unsubscribe, and data is deleted after two years of inactivity.",
    },
    {
        "label": "Health analytics",
        "activity": "Fictional company ValeFit analyzes wearable heart rate data and sleep records from EU users to create wellness scores. The activity uses consent, stores data in another region, and has not completed a DPIA.",
    },
    {
        "label": "Ad sharing",
        "activity": "Fictional company BrightCart tracks California shoppers across its site and shares purchase behavior with advertising partners for retargeting. It has no opt-out link and no process for deletion requests.",
    },
]


def settings():
    """Load LiteLLM settings from the local .env file."""
    load_dotenv(Path(__file__).with_name(".env"))
    missing = [key for key in ["LITELLM_BASE_URL", "MODEL_NAME", "LITELLM_API_KEY"] if not os.getenv(key)]
    if missing:
        print("Missing environment variables: " + ", ".join(missing))
        sys.exit(1)

    base_url = os.environ["LITELLM_BASE_URL"].rstrip("/")
    if not base_url.endswith("/v1"):
        base_url += "/v1"

    return base_url, os.environ["MODEL_NAME"], os.environ["LITELLM_API_KEY"]


def parse_json(text):
    """Parse JSON even when a model wraps it in extra formatting."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1:
        cleaned = cleaned[start : end + 1]

    return json.loads(cleaned)


def screen_activity(client, model, activity):
    """Ask the model to screen one data activity for GDPR and CCPA flags."""
    result = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": activity},
        ],
        temperature=0,
    )
    return parse_json(result.choices[0].message.content)


def main():
    """Run the GDPR and CCPA screening demo cases."""
    base_url, model, api_key = settings()
    client = OpenAI(base_url=base_url, api_key=api_key, timeout=60)
    print(f"Using model: {model}")

    for demo in DEMOS:
        print(f"\nCase: {demo['label']}")
        try:
            result = screen_activity(client, model, demo["activity"])
        except json.JSONDecodeError:
            print("The model did not return valid JSON.")
            sys.exit(1)
        except OpenAIError:
            print("The LiteLLM-compatible endpoint could not complete the request.")
            sys.exit(1)
        except Exception:
            print("The provider request stopped unexpectedly before returning a usable result.")
            sys.exit(1)

        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
