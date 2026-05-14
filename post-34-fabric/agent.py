# (c) 2026 NosisTech LLC. Original implementation.

import os
import sys
import time

from openai import APIConnectionError, OpenAI, OpenAIError, RateLimitError

PATTERNS = {
    "summarize_briefing": {
        "name": "summarize_briefing",
        "purpose": "Turn a business note into a concise executive summary.",
        "system_prompt": "You are an executive communications specialist. Summarize the business note in plain language using three to five sentences. Do not use headers or bullets.",
    },
    "extract_risks": {
        "name": "extract_risks",
        "purpose": "Identify operational, compliance, or customer risks in a note.",
        "system_prompt": "You are a risk analyst. Identify operational, compliance, or customer risks in the note. List each risk as a short statement. Do not speculate beyond the note.",
    },
    "draft_action_plan": {
        "name": "draft_action_plan",
        "purpose": "Convert a status note into specific next actions.",
        "system_prompt": "You are a project manager. Convert the status note into a numbered list of concrete next actions achievable within one week. Assign a role where possible.",
    },
}

DEMO_INPUTS = [
    {
        "title": "Vendor Policy Update",
        "pattern": "summarize_briefing",
        "text": "Harborlight Analytics received notice that its cloud storage vendor will reduce the default data retention window from 90 days to 30 days next quarter. Legacy contracts are grandfathered for 12 months. New ingestion pipelines need cold storage archiving before the cutoff. Legal flagged three active client agreements that reference the 90-day standard.",
    },
    {
        "title": "Customer Support Incident",
        "pattern": "extract_risks",
        "text": "Northstar Retail Group had a 48-hour delay on a Tier 1 support ticket after routing sent the ticket to an unmanned queue. The affected customer represents 12 percent of quarterly platform revenue. The SLA is four hours. No automatic escalation fired. The customer mentioned the delay on a renewal call.",
    },
    {
        "title": "Project Status Note",
        "pattern": "draft_action_plan",
        "text": "Meridian Civic Systems is six weeks into a 12-week compliance automation project. Policy ingestion is complete. The reporting dashboard is 70 percent complete. The blocker is an unsigned e-signature vendor contract required before document workflow work can begin. A two-week slip is likely if it is not signed this week.",
    },
]


def load_env_file() -> None:
    """Read local .env values into environment variables."""
    env_path = os.path.join(os.getcwd(), ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, encoding="utf-8") as env_file:
        for line in env_file:
            clean = line.strip().lstrip("\ufeff")
            if clean and not clean.startswith("#") and "=" in clean:
                name, value = clean.split("=", 1)
                os.environ.setdefault(name.strip(), value.strip().strip('"').strip("'"))


def load_settings() -> dict[str, str | bool]:
    """Validate configuration and return runtime settings."""
    load_env_file()
    required = ["LITELLM_BASE_URL", "MODEL_NAME", "LITELLM_API_KEY"]
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        print("Missing required environment variables: " + ", ".join(missing))
        print("Copy .env.template to .env and fill in all values.")
        sys.exit(1)
    return {
        "base_url": os.environ["LITELLM_BASE_URL"],
        "model_name": os.environ["MODEL_NAME"],
        "api_key": os.environ["LITELLM_API_KEY"],
        "dry_run": os.getenv("DRY_RUN", "false").strip().lower() == "true",
    }


def build_client(settings: dict[str, str | bool]) -> OpenAI:
    """Create an OpenAI-compatible client pointed at LiteLLM."""
    return OpenAI(base_url=str(settings["base_url"]), api_key=str(settings["api_key"]))


def get_pattern(pattern_name: str) -> dict[str, str]:
    """Return a known pattern by name."""
    if pattern_name not in PATTERNS:
        print("Unknown pattern: " + pattern_name)
        print("Available patterns: " + ", ".join(PATTERNS))
        sys.exit(1)
    return PATTERNS[pattern_name]


def validate_input(user_text: str) -> None:
    """Check that input is present and small enough for this demo."""
    if not user_text.strip():
        print("Input text cannot be blank.")
        sys.exit(1)
    if len(user_text) > 4000:
        print("Input text exceeds the 4000-character limit.")
        sys.exit(1)


def build_messages(pattern: dict[str, str], user_text: str) -> list[dict[str, str]]:
    """Combine the selected pattern and user input."""
    return [
        {"role": "system", "content": pattern["system_prompt"]},
        {"role": "user", "content": user_text},
    ]


def call_model_with_retries(client: OpenAI, model_name: str, messages: list[dict[str, str]]) -> str:
    """Call the model with rate-limit backoff."""
    for attempt in range(3):
        try:
            response = client.chat.completions.create(model=model_name, messages=messages, temperature=0.2)
            content = response.choices[0].message.content
            if not content:
                raise ValueError("empty model response")
            return content
        except RateLimitError:
            if attempt < 2:
                time.sleep(2**attempt * 5)
                continue
            print("Rate limit reached after three attempts. Try again later.")
        except APIConnectionError:
            print("Cannot reach LiteLLM. Check that the proxy is running.")
        except (OpenAIError, ValueError):
            print("The model call failed. Check your LiteLLM settings and model name.")
        sys.exit(1)
    sys.exit(1)


def run_pattern(client: OpenAI, settings: dict[str, str | bool], demo_input: dict[str, str]) -> str | None:
    """Validate a pattern run and either preview or execute it."""
    pattern = get_pattern(demo_input["pattern"])
    validate_input(demo_input["text"])
    if settings["dry_run"]:
        print("--- DRY RUN: " + demo_input["title"] + " ---")
        print("Pattern: " + pattern["name"])
        print("System: " + pattern["system_prompt"])
        print("Input: " + demo_input["text"] + "\n")
        return None
    return call_model_with_retries(
        client, str(settings["model_name"]), build_messages(pattern, demo_input["text"])
    )


def print_result(demo_input: dict[str, str], response_text: str) -> None:
    """Print the completed pattern result."""
    print("=== " + demo_input["title"] + " ===")
    print("Pattern: " + demo_input["pattern"] + "\n")
    print(response_text + "\n")


def main() -> None:
    """Load settings and run the demo patterns."""
    settings = load_settings()
    print("Active model: " + str(settings["model_name"]) + "\n")
    client = build_client(settings)
    for demo_input in DEMO_INPUTS:
        result = run_pattern(client, settings, demo_input)
        if result is not None:
            print_result(demo_input, result)


if __name__ == "__main__":
    main()


