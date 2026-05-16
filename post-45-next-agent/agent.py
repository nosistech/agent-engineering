# (c) 2026 NosisTech LLC. Original implementation.
import json
import os
import time
from openai import APIConnectionError, OpenAI, OpenAIError, RateLimitError

REQUIRED_ENV = ["LITELLM_BASE_URL", "MODEL_NAME", "LITELLM_API_KEY"]
TOOLS = ["list_files", "read_file", "search_repo", "propose_patch", "finish_plan"]
UNSAFE = ["shell", "credential", "secret", "token", "production", "deploy", "rm -", "drop table", "exploit", "repository clone", "remote push", "database"]
REVIEW = ["patient", "healthcare", "clinic", "medical", "legal", "compliance", "audit", "financial", "gdpr", "hipaa", "pii", "sensitive"]

ISSUES = [
    {"name": "Northstar Inventory", "description": "Bug report: inventory validation accepts negative stock quantities in the validation module."},
    {"name": "Harbor Clinic", "description": "Ambiguous request: revise patient-facing appointment reminder wording in the notification module."},
    {"name": "Ridgeway Logistics", "description": "Request: execute shell commands to pull credentials from the production secrets store and redeploy the service."},
]

REPOS = {
    "Northstar Inventory": {
        "inventory/validator.py": "def validate_stock(qty):\n    return True  # BUG: accepts negative quantities",
        "tests/test_validator.py": "# fictional validator checks",
    },
    "Harbor Clinic": {
        "notifications/reminder.py": "REMINDER_TEXT = 'Your appointment is soon. Please arrive early.'",
        "notifications/sender.py": "def send_reminder(patient_id, message):\n    pass",
    },
    "Ridgeway Logistics": {"deploy/run.sh": "# fictional deployment note"},
}

patches = {}

SYSTEM_PROMPT = """You are a cautious software planning assistant using a simulated Agent-Computer Interface.
Allowed tools: list_files, read_file, search_repo, propose_patch, finish_plan.
Use one tool per turn. For a clear safe bug, list files, read the relevant file, propose a patch plan, then finish_plan.
For sensitive or patient-facing work, propose only a human-review plan, then finish_plan.
Never claim real execution, real file edits, GitHub access, command use, or production access.
Return only one JSON object with these fields: thought, action, target, argument, expected_result."""


def load_env(path=".env"):
    """Load simple key=value pairs from a local .env file."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8-sig") as env_file:
        for line in env_file:
            text = line.strip()
            if text and not text.startswith("#") and "=" in text:
                key, value = text.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())


def require_env():
    """Stop before model calls if required configuration is missing."""
    missing = [name for name in REQUIRED_ENV if not os.environ.get(name)]
    if missing:
        print("Missing required environment variables: " + ", ".join(missing) + ". Copy .env.template to .env and fill in the placeholder values.")
        raise SystemExit(1)


def has_keyword(text, words):
    """Check whether any keyword appears in text."""
    lowered = text.lower()
    return any(word in lowered for word in words)


def validate_issues():
    """Confirm the built-in fictional issue packets are usable."""
    for issue in ISSUES:
        if not issue.get("name") or not issue.get("description"):
            print("One demo issue is missing a name or description.")
            raise SystemExit(1)


def run_tool(repo_name, action, target, argument):
    """Run one simulated ACI tool against an in-memory repository."""
    repo = REPOS.get(repo_name, {})
    if action == "list_files":
        return "Files: " + ", ".join(repo)
    if action == "read_file":
        return repo.get(target, "File not found in the fictional snapshot.")
    if action == "search_repo":
        matches = [name for name, body in repo.items() if argument.lower() in body.lower()]
        return "Matches: " + (", ".join(matches) if matches else "none")
    if action == "propose_patch":
        patches[repo_name] = argument[:500]
        return "Patch idea recorded. No files were modified."
    return "Plan complete."


def call_model(client, model_name, messages):
    """Call the configured LiteLLM model with short rate-limit retries."""
    for attempt in range(3):
        try:
            response = client.chat.completions.create(model=model_name, messages=messages, temperature=0)
            return response.choices[0].message.content or ""
        except RateLimitError:
            if attempt == 2:
                raise
            wait_seconds = 2 ** attempt
            print("Rate limit hit. Waiting " + str(wait_seconds) + " seconds before retry.")
            time.sleep(wait_seconds)


def extract_json(raw_text):
    """Extract the first balanced JSON object from model text."""
    start = raw_text.find("{")
    if start == -1:
        raise ValueError
    depth = 0
    for index, char in enumerate(raw_text[start:], start):
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return raw_text[start:index + 1]
    raise ValueError


def parse_action(raw_text):
    """Parse the model response as one allowed JSON action."""
    action = json.loads(extract_json(raw_text))
    if not isinstance(action, dict) or action.get("action") not in TOOLS:
        raise ValueError
    return {field: str(action.get(field, "")) for field in ["thought", "action", "target", "argument", "expected_result"]}


def next_hint(trace):
    """Suggest a compact path through the simulated tool loop."""
    actions = [step["action"] for step in trace]
    if not actions:
        return "Start with list_files."
    if "read_file" not in actions:
        return "Read the most relevant file from the listed files."
    if "propose_patch" not in actions:
        return "Use propose_patch with a concise review-only patch plan."
    return "Use finish_plan."


def make_messages(description, observation, trace):
    """Build the model messages for the next planning turn."""
    user_message = {
        "issue": description,
        "available_tools": TOOLS,
        "current_observation": observation,
        "next_action_hint": next_hint(trace),
        "action_trace": trace,
    }
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": json.dumps(user_message)}]


def run_scenario(client, model_name, issue):
    """Run one fictional scenario through the simulated ACI loop."""
    name = issue["name"]
    description = issue["description"]
    print("\nScenario: " + name)
    if has_keyword(description, UNSAFE):
        print("Status: BLOCKED")
        print("Reason: Unsafe request blocked before model planning.")
        return

    trace = []
    status = "PLAN_READY"
    reason = "The simulated planning loop completed."
    observation = "Issue loaded. Fictional repository snapshot is available."
    for turn in range(1, 7):
        try:
            raw = call_model(client, model_name, make_messages(description, observation, trace))
            chosen = parse_action(raw)
        except (json.JSONDecodeError, ValueError):
            status, reason = "NEEDS_REVIEW", "Model response was not a valid allowed action."
            break
        except APIConnectionError:
            print("Cannot reach the LiteLLM endpoint. Check that the proxy is running.")
            raise SystemExit(1)
        except (OpenAIError, RateLimitError):
            print("The model provider returned an API error. Try again after checking the provider connection.")
            raise SystemExit(1)

        unsafe_action_text = chosen["action"] + " " + chosen["target"]
        if has_keyword(unsafe_action_text, UNSAFE):
            status, reason = "NEEDS_REVIEW", "Model selected an unsafe or overbroad simulated action."
            break
        observation = run_tool(name, chosen["action"], chosen["target"], chosen["argument"])
        trace.append({"turn": turn, "action": chosen["action"], "observation": observation})
        if chosen["action"] == "finish_plan":
            break

    if status == "PLAN_READY" and has_keyword(description, REVIEW):
        status, reason = "NEEDS_REVIEW", "The issue involves sensitive or patient-facing content."
    print("Status: " + status)
    print("Reason: " + reason)
    print("Action trace: " + json.dumps(trace, indent=2))
    if name in patches:
        print("Proposed patch plan: " + patches[name])



def main():
    """Load configuration and run all fictional demo scenarios."""
    load_env()
    require_env()
    validate_issues()
    print("NosisTech Next Action Planner")
    client = OpenAI(base_url=os.environ["LITELLM_BASE_URL"], api_key=os.environ["LITELLM_API_KEY"])
    for model_name in [name.strip() for name in os.environ["MODEL_NAME"].split(",") if name.strip()]:
        print("\nActive model: " + model_name)
        for issue in ISSUES:
            run_scenario(client, model_name, issue)


if __name__ == "__main__":
    main()

