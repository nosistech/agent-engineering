# MIT License, Copyright 2025 Packt
import json
import os
import time
from openai import APIConnectionError, OpenAI, OpenAIError, RateLimitError

REQUIRED_ENV = ["LITELLM_BASE_URL", "MODEL_NAME", "LITELLM_API_KEY"]
TOLERANCE = 0.5
GPS_FALLBACK = {
    "sub_problems": ["Check source timing.", "Check metric definition.", "Check reporting scope."], "analogy": "Like reconciling two inventory counts taken at different times.",
    "hypothesis": "The discrepancy may come from a timing or scope mismatch between the claim and the trusted record.", "confidence": 0.42,
    "test_plan": "Compare the raw report date, metric definition, and included business units.", "meta_lesson": "Escalated reasoning still needs deterministic checks before its output is trusted.",
}
SCENARIOS = [
    {"name": "Lumina Home Goods", "article_text": "Lumina Home Goods reported an 8.3 percent product return rate for Q1.", "fallback_claim": {"claim_text": "product return rate", "metric_key": "return_rate_pct", "claimed_value": 8.3, "unit": "percent"}, "trusted_facts": {"return_rate_pct": 8.1}},
    {"name": "Vector Freight", "article_text": "Vector Freight Solutions announced that only 4 percent of shipments arrived late last quarter.", "fallback_claim": {"claim_text": "late shipment rate", "metric_key": "late_shipment_pct", "claimed_value": 4.0, "unit": "percent"}, "trusted_facts": {"late_shipment_pct": 17.2}},
    {"name": "Cedar Desk Software", "article_text": "Cedar Desk Software stated that its assistant resolves 91 percent of support tickets without human intervention.", "fallback_claim": {"claim_text": "automation containment rate", "metric_key": "automation_containment_pct", "claimed_value": 91.0, "unit": "percent"}, "trusted_facts": {"automation_containment_pct": 54.0}},
]

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

def validate_text_input(text):
    """Reject empty or oversized text before sending it to a model."""
    if not isinstance(text, str) or not text.strip():
        print("Scenario text is empty. Review the demo scenario.")
        raise SystemExit(1)
    if len(text) > 8000:
        print("Scenario text is too long for this educational demo.")
        raise SystemExit(1)

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

def extract_json_object(text):
    """Extract and parse the outer JSON object from a model response."""
    try:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError
        return json.loads(text[start:end + 1])
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}

def to_text(value):
    """Convert provider-shaped JSON values into safe display text."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        name, description = value.get("name"), value.get("description")
        if name and description:
            return str(name) + ": " + str(description)
        if description or name:
            return str(description or name)
    return json.dumps(value, ensure_ascii=True)

def extract_claim(client, model_name, scenario):
    """Ask the model for one structured claim and fall back when needed."""
    validate_text_input(scenario["article_text"])
    metric_key = next(iter(scenario["trusted_facts"]))
    prompt = (
        "Return one JSON object only with claim_text, metric_key, claimed_value, and unit. "
        "The metric_key must be exactly " + metric_key + ". "
        "Extract the primary numeric business claim from this fictional text: "
        + scenario["article_text"]
    )
    raw = call_model(client, model_name, [{"role": "user", "content": prompt}])
    claim = extract_json_object(raw)
    needed = {"claim_text", "metric_key", "claimed_value", "unit"}
    try:
        claim["claimed_value"] = float(claim["claimed_value"])
    except (KeyError, TypeError, ValueError):
        claim = {}
    if needed.issubset(claim) and claim["metric_key"] in scenario["trusted_facts"]:
        return claim
    print("Claim extraction used the deterministic fallback.")
    return scenario["fallback_claim"]

def verify_claim(claim, trusted_facts):
    """Compare a claim to the trusted fictional reference value."""
    metric_key = claim["metric_key"]
    if metric_key not in trusted_facts:
        return {"status": "FAIL", "reason": "No trusted record exists for this metric.", "trusted_value": None, "drift": None}
    trusted_value = float(trusted_facts[metric_key])
    drift = abs(float(claim["claimed_value"]) - trusted_value)
    status = "PASS" if drift <= TOLERANCE else "FAIL"
    reason = "Drift is within tolerance." if status == "PASS" else "Drift exceeds tolerance."
    return {"status": status, "reason": reason, "trusted_value": trusted_value, "drift": drift}

def solve_problem(client, model_name, scenario, claim, verification):
    """Run the five-stage General Problem Solver cycle for failed claims."""
    packet = {"scenario": scenario["name"], "claim": claim, "verification": verification}
    prompt = (
        "A fictional business claim failed verification. Return one JSON object with sub_problems, "
        "analogy, hypothesis, confidence, test_plan, and meta_lesson. Follow this cycle: decompose "
        "the discrepancy, use one cross-domain analogy, generate one testable hypothesis, score "
        "confidence from 0.0 to 1.0, and state one meta-learning lesson. Context: "
        + json.dumps(packet)
    )
    gps = extract_json_object(call_model(client, model_name, [{"role": "user", "content": prompt}]))
    needed = {"sub_problems", "analogy", "hypothesis", "confidence", "test_plan", "meta_lesson"}
    try:
        gps["confidence"] = float(gps["confidence"])
    except (KeyError, TypeError, ValueError):
        gps = {}
    if needed.issubset(gps) and isinstance(gps["sub_problems"], list) and 0 <= gps["confidence"] <= 1:
        gps["sub_problems"] = [to_text(item) for item in gps["sub_problems"]]
        for field in ("analogy", "hypothesis", "test_plan", "meta_lesson"):
            gps[field] = to_text(gps[field])
        return gps
    print("GPS used the deterministic fallback.")
    return GPS_FALLBACK

def route_scenario(client, model_name, scenario):
    """Route one fictional scenario through verification and optional GPS escalation."""
    print("\nScenario: " + scenario["name"])
    claim = extract_claim(client, model_name, scenario)
    verification = verify_claim(claim, scenario["trusted_facts"])
    print("Claim: " + claim["claim_text"] + " = " + str(claim["claimed_value"]) + " " + claim["unit"])
    print("Verification: " + verification["status"] + " - " + verification["reason"])
    if verification["status"] == "PASS":
        print("Route: ACCEPTED")
        return
    print("Route: ESCALATED_TO_GPS")
    gps = solve_problem(client, model_name, scenario, claim, verification)
    print("Sub-problems: " + "; ".join(str(item) for item in gps["sub_problems"]))
    print("Analogy: " + gps["analogy"])
    print("Hypothesis: " + gps["hypothesis"])
    print("Confidence: " + str(round(gps["confidence"], 2)))
    print("Meta-lesson: " + gps["meta_lesson"])

def main():
    """Load configuration and run the General Problem Solver demo."""
    load_env()
    require_env()
    client = OpenAI(base_url=os.environ["LITELLM_BASE_URL"], api_key=os.environ["LITELLM_API_KEY"])
    for model_name in [name.strip() for name in os.environ["MODEL_NAME"].split(",") if name.strip()]:
        print("\nActive model: " + model_name)
        for scenario in SCENARIOS:
            route_scenario(client, model_name, scenario)


if __name__ == "__main__":
    main()
