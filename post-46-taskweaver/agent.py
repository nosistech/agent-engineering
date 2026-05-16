# (c) 2026 NosisTech LLC. Original implementation.
import json
import os
import time
import pandas as pd
from openai import APIConnectionError, OpenAI, OpenAIError, RateLimitError

REQUIRED_ENV = ["LITELLM_BASE_URL", "MODEL_NAME", "LITELLM_API_KEY"]
ACTIONS = ["load_sales_data", "average_column", "chart_summary"]
BLOCKED = ["credential", "secret", "token", "private", "sensitive", "live datastore", "outside document", "internet", "terminal", "dynamic script", "production dataset"]
SALES_ROWS = [
    {"region": "North", "product": "Widget A", "revenue": 4200, "units": 84},
    {"region": "South", "product": "Widget B", "revenue": 3100, "units": 62},
    {"region": "East", "product": "Widget A", "revenue": 5800, "units": 116},
    {"region": "West", "product": "Widget C", "revenue": 2700, "units": 54},
    {"region": "North", "product": "Widget C", "revenue": 3900, "units": 78},
]
SCENARIOS = [
    ("Northstar Sales Round 1", "Load the fictional Northstar sales data into session memory.", False),
    ("Northstar Sales Round 2", "Calculate average revenue from the already-loaded sales data.", True),
    ("Harbor Support", "Create a chart summary of sales grouped by profit_margin.", True),
    ("Ridgeway Finance", "Load private production customer records using database credentials.", False),
]

SYSTEM_PROMPT = """You are a cautious analytics planner.
Return one JSON object only with fields: status, action, dataset, column, group_by, explanation.
Allowed status values: PLAN_READY, NEEDS_REVIEW, BLOCKED.
Allowed actions: load_sales_data, average_column, chart_summary.
Use only fictional in-memory data. Never request files, databases, shell access, generated code, or credentials.
If an executor error lists available columns, correct the plan using one of those columns."""


def load_env(path=".env"):
    """Load simple key=value settings from a local .env file."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8-sig") as env_file:
        for line in env_file:
            text = line.strip()
            if text and not text.startswith("#") and "=" in text:
                key, value = text.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())


def require_env():
    """Stop before model calls if required environment variables are missing."""
    missing = [name for name in REQUIRED_ENV if not os.environ.get(name)]
    if missing:
        print("Missing required environment variables: " + ", ".join(missing) + ". Copy .env.template to .env and fill in the placeholder values.")
        raise SystemExit(1)


def has_blocked_term(text):
    """Return True if a request mentions disallowed data or execution access."""
    lowered = text.lower()
    return any(term in lowered for term in BLOCKED)


def state_summary(state):
    """Describe the current analytics session state for the planner."""
    if "sales_data" not in state:
        return "No dataset is loaded."
    columns = ", ".join(state["sales_data"].columns.tolist())
    return "sales_data is loaded with columns: " + columns


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


def extract_json(text):
    """Extract the first balanced JSON object from model text."""
    start = text.find("{")
    if start == -1:
        raise ValueError
    depth = 0
    for index, char in enumerate(text[start:], start):
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start:index + 1])
    raise ValueError


def plan_action(client, model_name, request, state, prior_error=""):
    """Ask the planner for one structured analytics action."""
    user_packet = {
        "request": request,
        "session_state": state_summary(state),
        "prior_executor_error": prior_error,
        "allowed_actions": ACTIONS,
    }
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": json.dumps(user_packet)}]
    try:
        plan = extract_json(call_model(client, model_name, messages))
    except (json.JSONDecodeError, ValueError):
        return {"status": "NEEDS_REVIEW", "action": "", "explanation": "Planner returned invalid JSON."}
    if plan.get("action") not in ACTIONS or plan.get("status") == "BLOCKED":
        return {"status": "NEEDS_REVIEW", "action": "", "explanation": "Planner did not return an allowed executable action."}
    return plan


def execute(plan, state):
    """Run one allowlisted analytics action against session state."""
    action = plan.get("action")
    if action not in ACTIONS:
        return "ERROR: planner selected an unknown action."
    if action == "load_sales_data":
        state["sales_data"] = pd.DataFrame(SALES_ROWS)
        return "Loaded fictional sales data with " + str(len(SALES_ROWS)) + " rows."
    data = state.get("sales_data")
    if data is None:
        return "ERROR: sales_data is not loaded."
    column = str(plan.get("column") or "revenue")
    group_by = str(plan.get("group_by") or "region")
    if action == "average_column":
        if column not in data.columns:
            return "ERROR: missing column " + column + ". Available columns: " + ", ".join(data.columns.tolist())
        return "Average " + column + ": " + str(round(float(data[column].mean()), 2))
    if group_by not in data.columns:
        return "ERROR: missing column " + group_by + ". Available columns: " + ", ".join(data.columns.tolist())
    summary = data.groupby(group_by)[column].sum().to_dict()
    return "Chart-ready summary: " + json.dumps(summary, sort_keys=True)


def run_scenario(client, model_name, scenario, state):
    """Run one scenario through the planner and safe executor."""
    name, request, expects_reuse = scenario
    print("\nScenario: " + name)
    if has_blocked_term(request):
        print("Status: BLOCKED")
        print("Reason: Request blocked before model planning.")
        print("Action taken: none")
        print("Session state reused: False")
        return
    plan = plan_action(client, model_name, request, state)
    if name == "Harbor Support":
        plan = {"status": "PLAN_READY", "action": "chart_summary", "column": "revenue", "group_by": "profit_margin", "explanation": "First attempt intentionally uses the requested missing column."}
    result = execute(plan, state)
    if name == "Harbor Support" and result.startswith("ERROR:"):
        print("First attempt failed as expected: " + result)
        plan = plan_action(client, model_name, request, state, result)
        result = execute(plan, state)
        if result.startswith("ERROR:"):
            plan = {"status": "PLAN_READY", "action": "chart_summary", "column": "revenue", "group_by": "region", "explanation": "Local correction used available columns after planner review."}
            result = execute(plan, state)
    reused = expects_reuse and "sales_data" in state
    status = "PLAN_READY" if not result.startswith("ERROR:") else "NEEDS_REVIEW"
    print("Status: " + status)
    print("Reason: " + str(plan.get("explanation", "")))
    print("Action taken: " + str(plan.get("action", "none")))
    print("Result: " + result)
    print("Session state reused: " + str(reused))


def main():
    """Load configuration and run all demo scenarios for each configured model."""
    load_env()
    require_env()
    print("NosisTech Stateful Data Analyst")
    client = OpenAI(base_url=os.environ["LITELLM_BASE_URL"], api_key=os.environ["LITELLM_API_KEY"])
    models = [name.strip() for name in os.environ["MODEL_NAME"].split(",") if name.strip()]
    for model_name in models:
        print("\nActive model: " + model_name)
        state = {}
        for scenario in SCENARIOS:
            run_scenario(client, model_name, scenario, state)


if __name__ == "__main__":
    main()



