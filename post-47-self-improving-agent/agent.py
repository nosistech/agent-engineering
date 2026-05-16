# MIT License, Copyright 2025 Packt
import json
import os
import time
from openai import APIConnectionError, OpenAI, OpenAIError, RateLimitError

REQUIRED_ENV = ["LITELLM_BASE_URL", "MODEL_NAME", "LITELLM_API_KEY"]
ALLOWED_TYPES = {"prompt_update", "threshold_adjustment", "retrieval_strategy", "tool_reordering"}
THRESHOLDS = {
    "task_completion_rate": ("min", 0.80),
    "error_recovery_ratio": ("min", 0.85),
    "latency_p95": ("max", 3.0),
    "user_satisfaction_index": ("min", 4.0),
}
SCENARIOS = [
    ("Northstar Support", "standard", ["Users rephrase refund questions.", "Benchmark misses async setup answers."], {"task_completion_rate": 0.62, "error_recovery_ratio": 0.71, "latency_p95": 4.1, "user_satisfaction_index": 3.2}),
    ("Harbor Helpdesk", "standard", ["Users rate answers as clear.", "Synthetic checks pass."], {"task_completion_rate": 0.93, "error_recovery_ratio": 0.91, "latency_p95": 1.8, "user_satisfaction_index": 4.6}),
    ("Ridgeway Support", "restricted", ["Agent suggests steps outside its authority.", "High-stakes query remains uncertain."], {"task_completion_rate": 0.74, "error_recovery_ratio": 0.68, "latency_p95": 3.8, "user_satisfaction_index": 3.5}),
]
SYSTEM_PROMPT = """Return one JSON object only with exactly one item in a hypotheses list.
Do not use Markdown fences. The first character must be { and the last character must be }.
Each hypothesis needs source_signal, adaptation_type, proposed_change, confidence, evidence_count, rollback_safe.
The adaptation_type must be prompt_update.
The confidence must be a number such as 0.82.
The evidence_count must be an integer.
The rollback_safe value must be true.
The proposed_change must start with: Update the support prompt to
Propose only a text-level prompt change.
Never include executable code, file writes, cache changes, threshold changes, shell commands, deployment steps, background jobs, or real customer data."""


def load_env(path=".env"):
    """Load simple key=value settings from a local .env file."""
    if os.path.exists(path):
        with open(path, encoding="utf-8-sig") as env_file:
            for line in env_file:
                text = line.strip()
                if text and not text.startswith("#") and "=" in text:
                    key, value = text.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())


def require_env():
    """Stop before model calls if required settings are missing."""
    missing = [name for name in REQUIRED_ENV if not os.environ.get(name)]
    if missing:
        print("Missing required environment variables: " + ", ".join(missing) + ". Copy .env.template to .env and fill in the placeholders.")
        raise SystemExit(1)


def collect_feedback(scenario):
    """Convert one fictional scenario into feedback and metric fields."""
    name, risk, signals, metrics = scenario
    if not name or risk not in {"standard", "restricted"} or set(metrics) != set(THRESHOLDS):
        raise ValueError("Invalid scenario.")
    return {"name": name, "risk": risk, "explicit": signals[:1], "implicit": signals[1:], "synthetic": ["Fictional benchmark check completed."], "metrics": metrics}


def evaluate_metrics(metrics):
    """Compare observed metrics against the local KPI thresholds."""
    scores, below = {}, []
    for metric, value in metrics.items():
        direction, target = THRESHOLDS[metric]
        passed = value >= target if direction == "min" else value <= target
        scores[metric] = {"observed": value, "target": target, "passed": passed}
        if not passed:
            below.append(metric)
    return {"scores": scores, "below_target": below, "overall_health": "HEALTHY" if not below else "NEEDS_IMPROVEMENT"}


def call_model(client, model_name, messages):
    """Call the configured LiteLLM model with short rate-limit retries."""
    for attempt in range(3):
        try:
            response = client.chat.completions.create(model=model_name, messages=messages, temperature=0)
            return response.choices[0].message.content or ""
        except RateLimitError:
            if attempt == 2:
                print("Rate limit persisted after three attempts.")
                return ""
            wait_seconds = 2 ** attempt
            print("Rate limit reached. Retrying in " + str(wait_seconds) + " seconds.")
            time.sleep(wait_seconds)
        except APIConnectionError:
            print("Cannot reach the LiteLLM endpoint. Confirm the proxy is running and the .env values are correct.")
            raise SystemExit(1)
        except OpenAIError:
            print("The model request failed. Check the configured provider and try again.")
            return ""
    return ""


def request_hypothesis(client, model_name, scenario, evaluation, feedback_summary):
    """Ask the model for safe improvement hypotheses as strict JSON."""
    packet = {
        "scenario": scenario["name"],
        "risk_level": scenario["risk"],
        "feedback": feedback_summary,
        "below_target": evaluation["below_target"],
        "scores": evaluation["scores"],
        "instruction": "Return exactly one safe prompt_update hypothesis for this fictional support agent.",
    }
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": json.dumps(packet)}]
    return call_model(client, model_name, messages)


def parse_planner_response(text):
    """Parse and validate planner JSON into usable hypotheses."""
    try:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError
        hypotheses = json.loads(text[start:end + 1]).get("hypotheses", [])
    except (json.JSONDecodeError, AttributeError, ValueError):
        return [], "Planner returned invalid JSON."
    valid = []
    for item in hypotheses if isinstance(hypotheses, list) else []:
        needed = {"source_signal", "adaptation_type", "proposed_change", "confidence", "evidence_count", "rollback_safe"}
        if not isinstance(item, dict) or not needed.issubset(item):
            continue
        item["adaptation_type"] = str(item["adaptation_type"]).strip().lower().replace(" ", "_")
        try:
            item["confidence"] = float(item["confidence"])
            item["evidence_count"] = int(item["evidence_count"])
        except (TypeError, ValueError):
            continue
        risky_words = ["cache", "background", "threshold", "deploy", "database", "file", "shell", "execute", "api call"]
        change = str(item["proposed_change"]).lower()
        if item["adaptation_type"] not in ALLOWED_TYPES or any(word in change for word in risky_words):
            continue
        if 0 <= item["confidence"] <= 1 and isinstance(item["rollback_safe"], bool):
            valid.append(item)
    return (valid, "") if valid else ([], "No hypothesis passed validation.")


def review_hypotheses(hypotheses, risk):
    """Approve only rollback-safe hypotheses with enough confidence."""
    decisions = []
    for item in hypotheses:
        if risk == "restricted":
            approved, reason = False, "Rejected because restricted scenarios require manual review."
        elif not item["rollback_safe"]:
            approved, reason = False, "Rejected because rollback_safe is false."
        elif item["confidence"] < 0.70:
            approved, reason = False, "Rejected because confidence is below 0.70."
        else:
            approved, reason = True, "Approved because confidence and rollback checks passed."
        decisions.append({"hypothesis": item, "approved": approved, "reason": reason})
    return decisions


def apply_approved(decisions, current_version):
    """Record approved adaptations and advance the version counter."""
    applied = []
    for decision in decisions:
        if decision["approved"]:
            current_version += 1
            item = decision["hypothesis"]
            applied.append({"version": current_version, "type": item["adaptation_type"], "change": item["proposed_change"]})
    return current_version, applied


def run_scenario(client, model_name, raw_scenario):
    """Run one sense, critique, plan, approve, learn cycle."""
    scenario = collect_feedback(raw_scenario)
    evaluation = evaluate_metrics(scenario["metrics"])
    print("\nScenario: " + scenario["name"])
    print("Health: " + evaluation["overall_health"])
    if evaluation["overall_health"] == "HEALTHY":
        print("All KPIs meet thresholds. No adaptation needed.")
        return
    print("Below target: " + ", ".join(evaluation["below_target"]))
    feedback = scenario["explicit"] + scenario["implicit"] + scenario["synthetic"]
    if scenario["risk"] == "restricted":
        hypotheses = [{"source_signal": feedback[0], "adaptation_type": "prompt_update", "proposed_change": "Pause improvement and route this restricted scenario to manual review.", "confidence": 0.40, "evidence_count": len(feedback), "rollback_safe": False}]
    else:
        raw = request_hypothesis(client, model_name, scenario, evaluation, feedback)
        hypotheses, blocked = parse_planner_response(raw)
        if blocked:
            print("Planner repair: " + blocked + " Replaced with a safe prompt-only adaptation.")
            hypotheses = [{"source_signal": feedback[0], "adaptation_type": "prompt_update", "proposed_change": "Update the support prompt to ask one clarifying question before answering ambiguous support requests.", "confidence": 0.72, "evidence_count": len(feedback), "rollback_safe": True}]
    decisions = review_hypotheses(hypotheses, scenario["risk"])
    _, applied = apply_approved(decisions, 0)
    for decision in decisions:
        print(("APPROVED: " if decision["approved"] else "REJECTED: ") + decision["reason"])
    if not applied:
        print("No adaptations applied.")
    for item in applied:
        print("Version upgraded to v" + str(item["version"]) + ". Applied adaptation: " + item["change"])


def main():
    """Load configuration and run the fictional demo scenarios."""
    load_env()
    require_env()
    client = OpenAI(base_url=os.environ["LITELLM_BASE_URL"], api_key=os.environ["LITELLM_API_KEY"])
    for model_name in [name.strip() for name in os.environ["MODEL_NAME"].split(",") if name.strip()]:
        print("\nActive model: " + model_name)
        for scenario in SCENARIOS:
            run_scenario(client, model_name, scenario)


if __name__ == "__main__":
    main()
