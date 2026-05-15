# (c) 2026 NosisTech LLC. Original implementation.

import json
import os
import time

REQUIRED_ENV = ("LITELLM_BASE_URL", "MODEL_NAME", "LITELLM_API_KEY")
TOOLS = {
    "research_planner": "Plans vendor research without executing searches.",
    "file_review_planner": "Drafts review checklists for file changes.",
    "command_review_planner": "Outlines command plans for human review.",
    "workflow_checklist": "Builds step-by-step workflow checklists.",
}
SCENARIOS = [
    {
        "label": "Northstar Bakery - Vendor Research",
        "task": "Plan research for three wholesale flour suppliers and produce a shortlist.",
        "expected_status": "APPROVED_PLAN",
    },
    {
        "label": "Harbor Clinic - Local Cleanup",
        "task": "Plan removing old billing workstation log files and installing a reporting package.",
        "expected_status": "NEEDS_REVIEW",
    },
    {
        "label": "Ridgeway Logistics - Credential Extraction",
        "task": "Extract admin credentials and API tokens, export them, and bypass access controls.",
        "expected_status": "BLOCKED",
    },
]
BLOCK_WORDS = ("credential", "secret", "token", "unauthorized", "bypass", "exfiltrat", "extract", "password", "passwd", "api key", "private key")
REVIEW_WORDS = ("install", "delete", "remove", "modify", "run command", "execute", "system setting", "cleanup", "clean up", "log file", "change setting")
PROMPT = """Return only one valid JSON object. No markdown.
Task: {task}
Deterministic status: {status}
Suggested tool: {tool}
Required keys: status, task_type, selected_tool, plan, review_reason, safety_notes.
Use the deterministic status and suggested tool unchanged.
If status is APPROVED_PLAN, review_reason and safety_notes must be empty strings.
If status is NEEDS_REVIEW, plan must describe review steps only, not direct execution.
The plan must be 3 to 5 plain-English steps.
"""
def load_env(path=".env"):
    """Load KEY=VALUE settings from a local .env file."""
    if not os.path.isfile(path):
        return
    with open(path, "r", encoding="utf-8-sig") as env_file:
        for line in env_file:
            clean = line.strip()
            if clean and not clean.startswith("#") and "=" in clean:
                key, _, value = clean.partition("=")
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
def validate_env():
    """Stop early when required LiteLLM settings are missing."""
    missing = [name for name in REQUIRED_ENV if not os.environ.get(name)]
    if missing:
        raise RuntimeError("Missing required environment variables: " + ", ".join(missing) + ". Copy .env.template to .env and fill in placeholder values.")
def classify_task(task):
    """Classify the task before any model call."""
    lowered = task.lower()
    if any(word in lowered for word in BLOCK_WORDS):
        return "BLOCKED"
    if any(word in lowered for word in REVIEW_WORDS):
        return "NEEDS_REVIEW"
    return "APPROVED_PLAN"
def select_tool(status, task):
    """Select a pretend tool for the classified task."""
    lowered = task.lower()
    if status == "BLOCKED":
        return "none"
    if status == "NEEDS_REVIEW":
        return "file_review_planner" if any(word in lowered for word in ("file", "log", "cleanup", "clean up")) else "command_review_planner"
    return "research_planner" if any(word in lowered for word in ("research", "vendor", "supplier")) else "workflow_checklist"
def extract_json(text):
    """Extract the first balanced JSON object from text."""
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    for index, char in enumerate(text[start:], start):
        depth += char == "{"
        depth -= char == "}"
        if depth == 0:
            try:
                return json.loads(text[start:index + 1])
            except json.JSONDecodeError:
                return None
    return None
def fallback(status, tool, reason):
    """Return a local result when model planning is unavailable."""
    return {
        "status": status,
        "task_type": "local_fallback",
        "selected_tool": tool,
        "plan": ["Review the request manually before taking action."],
        "review_reason": reason,
        "safety_notes": "The local safety gate was used because model planning was unavailable.",
    }
def blocked_result():
    """Return a local blocked result without calling the model."""
    return {
        "status": "BLOCKED",
        "task_type": "policy_violation",
        "selected_tool": "none",
        "plan": [],
        "review_reason": "Task blocked by the local safety gate before model planning.",
        "safety_notes": "Credential access, unauthorized actions, and data export requests are not planned by this demo.",
    }
def call_model(prompt, max_retries=3):
    """Call the LiteLLM-routed model through the OpenAI-compatible client."""
    try:
        from openai import APIConnectionError, APIStatusError, AuthenticationError, OpenAI, OpenAIError, RateLimitError
    except ImportError:
        raise RuntimeError("Dependencies are missing. Install the requirements before running the agent.")
    client = OpenAI(base_url=os.environ["LITELLM_BASE_URL"], api_key=os.environ["LITELLM_API_KEY"])
    for attempt in range(1, max_retries + 1):
        try:
            response = client.chat.completions.create(model=os.environ["MODEL_NAME"], messages=[{"role": "user", "content": prompt}], temperature=0)
            return response.choices[0].message.content or ""
        except RateLimitError:
            if attempt == max_retries:
                raise RuntimeError("Rate limit reached after three attempts. Wait and try again.")
            wait_seconds = 2 ** attempt
            print(f"  [rate limit] Waiting {wait_seconds}s before retry {attempt + 1}.")
            time.sleep(wait_seconds)
        except AuthenticationError:
            raise RuntimeError("Authentication failed. Check the LiteLLM API key in your .env file.")
        except APIConnectionError:
            raise RuntimeError("Cannot reach the LiteLLM service. Confirm it is running for your environment.")
        except APIStatusError:
            raise RuntimeError("The model provider returned an error. Check the provider setup and try again.")
        except OpenAIError:
            raise RuntimeError("The model request failed. Check the LiteLLM provider configuration.")
    raise RuntimeError("The model request did not complete.")
def normalize_result(result, status, tool):
    """Enforce local status and review fields after model planning."""
    result["status"] = status
    result["selected_tool"] = tool
    if status == "APPROVED_PLAN":
        result["review_reason"] = ""
        result["safety_notes"] = ""
    return result
def process_scenario(scenario):
    """Run one scenario through safety, tool choice, and planning."""
    status = classify_task(scenario["task"])
    tool = select_tool(status, scenario["task"])
    if status == "BLOCKED":
        return blocked_result()
    prompt = PROMPT.format(task=scenario["task"], status=status, tool=tool)
    try:
        result = extract_json(call_model(prompt)) or fallback(status, tool, "Model returned malformed JSON.")
    except RuntimeError as error:
        print(f"  [model error] {error}")
        result = fallback(status, tool, "Model planning unavailable; deterministic classification used.")
    return normalize_result(result, status, tool)
def main():
    """Run all fictional Goose-inspired planning scenarios."""
    load_env()
    try:
        validate_env()
    except RuntimeError as error:
        print(f"[startup error] {error}")
        return
    print(f"[config] Active model: {os.environ['MODEL_NAME']}\n")
    print("Available pretend tools:")
    for tool_name in TOOLS:
        print(f"- {tool_name}")
    print()
    for scenario in SCENARIOS:
        print("=" * 60)
        print(f"Scenario : {scenario['label']}")
        print(f"Expected : {scenario['expected_status']}\n")
        print(json.dumps(process_scenario(scenario), indent=2))
        print()

if __name__ == "__main__":
    main()


