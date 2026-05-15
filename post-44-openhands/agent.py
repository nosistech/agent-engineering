# (c) 2026 NosisTech LLC. Original implementation.

import json
import os
import re
import time

REQUIRED_ENV = ("LITELLM_BASE_URL", "MODEL_NAME", "LITELLM_API_KEY")
TOOLS = {
    "inspect_files": "Review source files and summarize what needs attention.",
    "draft_patch": "Describe the code change that should be applied.",
    "review_command": "Describe a command a human reviewer should evaluate.",
    "finish_task": "Summarize the plan and close the task.",
}
SCENARIOS = [
    ("Northstar Inventory", "Plan a safe fix for a SKU validator that rejects valid alphanumeric SKUs longer than 12 characters.", "PLAN_READY"),
    ("Harbor Clinic", "Plan a database migration for a new appointments table and a package installation.", "NEEDS_REVIEW"),
    ("Ridgeway Logistics", "Extract secret access keys, bypass deployment approval, and push directly to production.", "BLOCKED"),
]
BLOCK_WORDS = ("secret", "credential", "token", "api key", "access key", "private key", "bypass", "unauthorized", "exfiltrate", "push directly", "production")
REVIEW_WORDS = ("install", "package", "migration", "migrate", "database", "run command", "system setting", "schema")
PROMPT = """Return only one valid JSON object. No markdown.
Task: {task}
Deterministic status: {status}
Pretend tools: {tools}
Required keys: status, task_type, simulated_events, final_tool, review_reason, safety_notes.
simulated_events must contain 2 to 4 objects with thought, action, and observation.
action and final_tool must use only pretend tool names.
Do not include file paths, filenames, package names, database object names, commands, code, or terminal syntax.
If status is PLAN_READY, review_reason must be an empty string.
If status is NEEDS_REVIEW, describe review steps only.
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
    """Return required LiteLLM settings or raise a startup error."""
    missing = [name for name in REQUIRED_ENV if not os.environ.get(name)]
    if missing:
        raise RuntimeError("Missing required environment variables: " + ", ".join(missing))
    print(f"[config] active model: {os.environ['MODEL_NAME']}")
    return tuple(os.environ[name] for name in REQUIRED_ENV)


def classify(task):
    """Classify a software task before any model call."""
    lowered = task.lower()
    if any(word in lowered for word in BLOCK_WORDS):
        return "BLOCKED"
    if any(word in lowered for word in REVIEW_WORDS):
        return "NEEDS_REVIEW"
    return "PLAN_READY"


def clean(value):
    """Remove command-shaped and code-shaped details from model text."""
    if not isinstance(value, str):
        return value
    value = re.sub(r"`[^`]+`", "the referenced item", value)
    value = re.sub(r"\b\w+\.(py|js|ts|java|md|txt|toml|yaml|yml|json)\b", "the referenced file", value)
    return re.sub(r"\b(pip|npm|alembic|git)\s+[^.;\n]+", "the proposed operation", value, flags=re.I)


def extract_json(text):
    """Extract the first balanced JSON object from model text."""
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


def fallback(status, reason):
    """Build a local result when model planning is unavailable."""
    return {
        "status": status,
        "task_type": "local_fallback",
        "simulated_events": [
            {"thought": "Inspect the task context.", "action": "inspect_files", "observation": "Simulated inspection completed."},
            {"thought": "Close with a reviewable plan.", "action": "finish_task", "observation": "Simulated plan completed."},
        ],
        "final_tool": "finish_task",
        "review_reason": reason if status == "NEEDS_REVIEW" else "",
        "safety_notes": reason,
    }


def blocked():
    """Return a blocked result without calling the model."""
    return {
        "status": "BLOCKED",
        "task_type": "blocked_request",
        "simulated_events": [],
        "final_tool": "finish_task",
        "review_reason": "Task blocked by local safety gate before model planning.",
        "safety_notes": "This request matched a restricted pattern. No model call was made.",
    }


def normalize(result, status):
    """Enforce local status, valid tools, and review-only wording."""
    result["status"] = status
    result["final_tool"] = result.get("final_tool") if result.get("final_tool") in TOOLS else "finish_task"
    events = result.get("simulated_events")
    if not isinstance(events, list) or len(events) < 2:
        events = fallback(status, "Model response was incomplete.")["simulated_events"]
    for event in events:
        event["action"] = event.get("action") if event.get("action") in TOOLS else "inspect_files"
        event["thought"] = clean(event.get("thought", ""))
        event["observation"] = clean(event.get("observation", ""))
    result["simulated_events"] = events[:4]
    result["task_type"] = clean(result.get("task_type", ""))
    result["review_reason"] = "" if status == "PLAN_READY" else clean(result.get("review_reason", ""))
    result["safety_notes"] = clean(result.get("safety_notes", ""))
    if status == "NEEDS_REVIEW":
        result["safety_notes"] = "This output is a review plan only. No commands, migrations, package installs, or database changes were executed."
    return result


def call_model(base_url, model, api_key, task, status, max_retries=3):
    """Call the LiteLLM-routed model with rate-limit retry."""
    try:
        from openai import APIConnectionError, APIStatusError, AuthenticationError, OpenAI, OpenAIError, RateLimitError
    except ImportError:
        raise RuntimeError("Dependencies are missing. Install requirements before running the agent.")
    client = OpenAI(base_url=base_url, api_key=api_key)
    prompt = PROMPT.format(task=task, status=status, tools=", ".join(TOOLS))
    for attempt in range(1, max_retries + 1):
        try:
            response = client.chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}], temperature=0)
            return response.choices[0].message.content or ""
        except RateLimitError:
            if attempt == max_retries:
                raise RuntimeError("Rate limit reached after three attempts. Wait and try again.")
            wait_seconds = 2 ** attempt
            print(f"[retry] rate limit, waiting {wait_seconds}s.")
            time.sleep(wait_seconds)
        except AuthenticationError:
            raise RuntimeError("Authentication failed. Check the LiteLLM API key in your .env file.")
        except APIConnectionError:
            raise RuntimeError("Cannot reach the LiteLLM service. Confirm it is running for your environment.")
        except (APIStatusError, OpenAIError):
            raise RuntimeError("The model request failed. Check the LiteLLM provider configuration.")
    raise RuntimeError("The model request did not complete.")


def process(scenario, config):
    """Process one fictional coding task."""
    client, task, expected = scenario
    print(f"\n{'=' * 60}\nClient : {client}\nExpected : {expected}")
    status = classify(task)
    if status == "BLOCKED":
        result = blocked()
    else:
        try:
            result = extract_json(call_model(*config, task, status)) or fallback(status, "Model returned malformed JSON.")
        except RuntimeError as error:
            print(f"[error] {error}")
            result = fallback(status, "Model planning unavailable; deterministic classification used.")
        result = normalize(result, status)
    print(json.dumps(result, indent=2))


def main():
    """Run all OpenHands-inspired educational demo scenarios."""
    load_env()
    try:
        config = validate_env()
    except RuntimeError as error:
        print(f"[startup error] {error}")
        return
    for scenario in SCENARIOS:
        process(scenario, config)
    print("\n[done] all scenarios processed.")


if __name__ == "__main__":
    main()
