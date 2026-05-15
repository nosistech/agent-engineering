# (c) 2026 NosisTech LLC. Original implementation.

import json
import os
import time
from openai import APIConnectionError, APIStatusError, OpenAI, RateLimitError

REQUIRED_ENV = ["LITELLM_BASE_URL", "MODEL_NAME", "LITELLM_API_KEY"]
BLOCKED_WORDS = ["credential", "password", "captcha", "proxy", "stealth", "scrape", "payment", "delete", "bot bypass"]


def load_env_file():
    """Load simple key=value settings from .env without printing secrets."""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding="utf-8-sig") as file:
        for raw_line in file:
            key, separator, value = raw_line.strip().partition("=")
            if key and separator and not key.startswith("#") and key not in os.environ:
                os.environ[key.strip()] = value.strip()


def require_environment():
    """Stop before any model call when required LiteLLM settings are missing."""
    missing = [name for name in REQUIRED_ENV if not os.environ.get(name)]
    if missing:
        print("Missing required environment variables:")
        for name in missing:
            print(f"  - {name}")
        print("Create .env from .env.template before running this educational demo.")
        raise SystemExit(1)


def create_client():
    """Create an OpenAI-compatible client for the configured LiteLLM gateway."""
    return OpenAI(base_url=os.environ["LITELLM_BASE_URL"], api_key=os.environ["LITELLM_API_KEY"])


def build_page_states():
    """Return three fictional static page states for educational scenario runs."""
    return [
        {
            "page_name": "Northstar Customer Portal Search",
            "task_goal": "find an internal customer record by account ID",
            "current_url_label": "fictional internal portal, no real URL",
            "visible_elements": ["search input", "search button", "help link"],
            "allowed_actions": ["TYPE", "CLICK", "EXTRACT", "DONE"],
            "blocked_actions": ["PAY", "DELETE", "SUBMIT_PAYMENT", "ENTER_CREDENTIALS"],
            "page_text": "Northstar Customer Portal. Fields: Account ID. Buttons: Search, Help.",
        },
        {
            "page_name": "Harbor Vendor Profile",
            "task_goal": "extract vendor name, renewal month, and account owner from visible text",
            "current_url_label": "fictional vendor profile, no real URL",
            "visible_elements": ["vendor details panel", "renewal field", "account owner field"],
            "allowed_actions": ["EXTRACT", "DONE"],
            "blocked_actions": ["CLICK", "TYPE", "PAY", "DELETE", "ENTER_CREDENTIALS"],
            "page_text": "Vendor: Meridian Supply Group. Renewal Month: September. Account Owner: J. Calloway.",
        },
        {
            "page_name": "Ridgeway Checkout Review",
            "task_goal": "review purchase screen without submitting payment",
            "current_url_label": "fictional checkout page, no real URL",
            "visible_elements": ["order summary", "pay button", "cancel button"],
            "allowed_actions": ["EXTRACT", "NEEDS_REVIEW", "BLOCKED"],
            "blocked_actions": ["PAY", "SUBMIT_PAYMENT", "CLICK", "TYPE", "ENTER_CREDENTIALS"],
            "page_text": "Order: Office Supplies Bundle x3. Total: fictional amount. Human approval required.",
        },
    ]


def build_messages(page_state):
    """Build strict prompts for one safe browser-style planning action."""
    system_prompt = (
        "You are an educational browser task planner. You do not control a real browser or access real websites. "
        "Do not request credentials, submit payments, delete data, bypass bot defenses, solve captchas, scrape, "
        "or interact with real systems. Choose one action from CLICK, TYPE, SCROLL, EXTRACT, DONE, NEEDS_REVIEW, "
        "or BLOCKED. Return JSON only with action, target, reason, human_readable_step, and evidence_to_record."
    )
    user_prompt = (
        "Choose exactly one next action for this fictional page state. Do not include real URLs, credentials, "
        "scraping instructions, captcha bypass, bot evasion, or operational automation steps.\n\n"
        f"Page state:\n{json.dumps(page_state, indent=2)}"
    )
    return [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]


def call_model(client, page_state):
    """Ask the configured model for one reviewable action with limited retries."""
    for attempt in range(1, 4):
        try:
            response = client.chat.completions.create(model=os.environ["MODEL_NAME"], messages=build_messages(page_state))
            return response.choices[0].message.content or ""
        except RateLimitError:
            if attempt == 3:
                print("Rate limit reached on all attempts. This scenario needs review later.")
                return ""
            wait_seconds = 2 ** attempt
            print(f"Rate limit reached. Waiting {wait_seconds} seconds before retry.")
            time.sleep(wait_seconds)
        except APIConnectionError:
            print("The LiteLLM gateway could not be reached. Check your local setup.")
            return ""
        except APIStatusError:
            print("The model request was rejected. Check MODEL_NAME and gateway credentials.")
            return ""


def fallback_result(reason):
    """Create a safe fallback result when model output needs review."""
    return {
        "action": "NEEDS_REVIEW",
        "target": "none",
        "reason": reason,
        "human_readable_step": "Manual review is needed before any action is accepted.",
        "evidence_to_record": "The model response was not accepted as a clean action plan.",
    }


def parse_json_response(text):
    """Parse model JSON output, including simple fenced JSON blocks."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        cleaned = "\n".join(lines[1:-1]) if len(lines) > 2 else ""
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return fallback_result("Model output was not structured enough for review.")


def validate_action(page_state, result):
    """Block any proposed action that violates the local page-state rules."""
    action = str(result.get("action", "NEEDS_REVIEW")).upper()
    text = " ".join(str(result.get(field, "")) for field in ["target", "reason", "human_readable_step"]).lower()
    if action not in page_state["allowed_actions"]:
        return fallback_result(f"Action {action} is not allowed for this fictional page state.")
    if action in page_state["blocked_actions"]:
        return fallback_result(f"Action {action} is explicitly blocked for this fictional page state.")
    if any(word in text for word in BLOCKED_WORDS):
        return fallback_result("The proposed action mentioned disallowed browser automation content.")
    result["action"] = action
    return result


def print_result(page_name, result):
    """Print a compact action review without exposing configuration values."""
    print("\n" + "=" * 60)
    print(f"Scenario : {page_name}")
    print(f"Action   : {result.get('action', 'NEEDS_REVIEW')}")
    print(f"Target   : {result.get('target', '')}")
    print(f"Reason   : {result.get('reason', '')}")
    print(f"Step     : {result.get('human_readable_step', '')}")
    print(f"Evidence : {result.get('evidence_to_record', '')}")
    print("=" * 60)


def main():
    """Run three fictional browser-planning scenarios."""
    load_env_file()
    require_environment()
    print("\nBrowser Use Web Task Planner, NosisTech LLC")
    print(f"Active model: {os.environ['MODEL_NAME']}")
    print("Notice: Educational planner only. No browser opened. No real website accessed.")
    client = create_client()
    for page_state in build_page_states():
        raw_output = call_model(client, page_state)
        result = validate_action(page_state, parse_json_response(raw_output))
        print_result(page_state["page_name"], result)
    print("\nRun complete. No browser was opened. No real website was accessed.")
    print("All scenarios used fictional page states for educational purposes only.")


if __name__ == "__main__":
    main()

