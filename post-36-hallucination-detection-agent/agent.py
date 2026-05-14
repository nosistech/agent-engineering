# (c) 2026 NosisTech LLC. Original implementation.
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI, OpenAIError


SYSTEM_PROMPT = """
You compare an AI response against its source context.
Return only JSON:
{
  "score": 0.0,
  "verdict": "GROUNDED | MIXED | HIGH_RISK",
  "claims": [
    {
      "claim": "claim from the response",
      "status": "SUPPORTED | UNSUPPORTED | CONTRADICTED",
      "reason": "short reason"
    }
  ]
}
Score 0.0 means mostly supported. Score 1.0 means mostly unsupported or contradicted.
"""

DEMOS = [
    {
        "label": "Grounded",
        "source": "Marble Ridge Clinics is a fictional healthcare group with 12 clinics. Its 2026 plan focuses on appointment reminders and patient portal training.",
        "response": "Marble Ridge Clinics has 12 clinics and is focusing on appointment reminders and patient portal training.",
    },
    {
        "label": "Unsupported",
        "source": "Harbor & Finch Logistics is a fictional freight company. It operates 42 refrigerated trucks across three states.",
        "response": "Harbor & Finch Logistics operates refrigerated trucks across three states. It also runs cargo flights, owns warehouses in Brazil, and reported 80 million USD in revenue.",
    },
    {
        "label": "Contradicted",
        "source": "Northstar Ledger is a fictional bookkeeping firm. It serves small retailers and does not provide tax filing services.",
        "response": "Northstar Ledger provides tax filing services for enterprise manufacturers.",
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


def detect_hallucinations(client, model, source, response):
    """Ask the model to check response claims against the source."""
    prompt = f"Source context:\n{source}\n\nAI response:\n{response}"
    result = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
    )
    return parse_json(result.choices[0].message.content)


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


def main():
    """Run the hallucination detection demo cases."""
    base_url, model, api_key = settings()
    client = OpenAI(base_url=base_url, api_key=api_key)
    print(f"Using model: {model}")

    for demo in DEMOS:
        try:
            result = detect_hallucinations(client, model, demo["source"], demo["response"])
        except json.JSONDecodeError:
            print("The model did not return valid JSON.")
            sys.exit(1)
        except OpenAIError:
            print("The LiteLLM-compatible endpoint could not complete the request.")
            sys.exit(1)

        print(f"\nCase: {demo['label']}")
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
