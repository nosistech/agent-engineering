# (c) 2026 NosisTech LLC. Original implementation.

import json
import os
import sys
import time

from dotenv import load_dotenv
from openai import APIConnectionError, OpenAI, RateLimitError

POLICIES = [
    (["export", "customer", "financial"], "Ardent Harbor Finance: customer financial exports require steward review and CISO sign-off."),
    (["patient", "medical", "phi"], "Luma Ridge Health: patient health information requires Privacy Officer approval."),
    (["vendor", "supplier", "third-party", "access"], "Northstar Parts: vendor system access requires manager and IT Security approval."),
]

SCENARIOS = [
    ("Safe summary", "Summarize internal team productivity notes for engineering leads."),
    ("Vendor access", "Grant a third-party supplier temporary access to the parts ordering system."),
    ("Customer export", "Export customer financial records from the past five years."),
]

def require_env():
    """Stop early if required LiteLLM settings are missing."""
    missing = [name for name in ["LITELLM_BASE_URL", "MODEL_NAME", "LITELLM_API_KEY"] if not os.getenv(name)]
    if missing:
        print("Missing required environment variables: " + ", ".join(missing))
        sys.exit(1)

def validate_request(state):
    """Validate the request before model use."""
    request = state["request"].strip()
    if not request or len(request) > 2000:
        print("Invalid request: empty or too long.")
        sys.exit(1)
    state["request"] = request
    return state

def retrieve_policy_context(state):
    """Match local policy context and store the full text off-prompt."""
    request_lower = state["request"].lower()
    matches = [text for keys, text in POLICIES if any(key in request_lower for key in keys)]
    context = "\n".join(matches) or "No matching policy found."
    memory_key = "mem-" + str(len(state["memory"]) + 1)
    state["memory"][memory_key] = context
    state.update(policy_excerpt=context.split("\n")[0], policy_refs=[memory_key])
    state["risk"] = score_risk(state["request"], bool(matches))
    return state

def score_risk(request, matched_policy):
    """Score risk with simple transparent rules."""
    request_lower = request.lower()
    if matched_policy and any(word in request_lower for word in ["export", "patient", "financial", "phi"]):
        return "HIGH"
    if matched_policy:
        return "MEDIUM"
    return "LOW"

def assess_request_with_model(state):
    """Ask the LiteLLM-routed model for a structured decision."""
    prompt = (
        "Return one JSON object only. Keys: decision, reason, required_human_checkpoint. "
        "decision must be APPROVE, REVIEW, or BLOCK. required_human_checkpoint must be a boolean.\n\n"
        "Request: " + state["request"] + "\nPolicy excerpt: " + state["policy_excerpt"] + "\nLocal risk: " + state["risk"] + "\n"
        "Memory reference: " + ", ".join(state["policy_refs"])
    )
    decision = call_model(state["client"], prompt)
    state["decision"] = clean_decision(decision, state["risk"])
    return state

def call_model(client, prompt):
    """Call the configured model with three rate-limit retries."""
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=os.environ["MODEL_NAME"],
                messages=[{"role": "system", "content": "Return valid JSON only."}, {"role": "user", "content": prompt}],
                temperature=0,
            )
            return parse_json_object(response.choices[0].message.content)
        except RateLimitError:
            if attempt == 2:
                print("Rate limit reached after three attempts. Please retry later.")
                sys.exit(1)
            time.sleep(2**attempt)
        except APIConnectionError:
            print("Could not reach the LiteLLM endpoint. Check that the proxy is running.")
            sys.exit(1)
        except json.JSONDecodeError:
            return review_decision("The model did not return valid JSON.")

def parse_json_object(raw_content):
    """Parse a JSON object even when a provider wraps it in extra text."""
    content = raw_content.strip()
    if content.startswith("```"):
        content = content.replace("```json", "").replace("```", "").strip()
    start_index = content.find("{")
    end_index = content.rfind("}")
    if start_index == -1 or end_index == -1:
        raise json.JSONDecodeError("No JSON object found.", content, 0)
    return json.loads(content[start_index : end_index + 1])

def clean_decision(decision, risk):
    """Validate model JSON and enforce human review for higher risk."""
    if not isinstance(decision, dict):
        return review_decision("The model response was not a JSON object.")
    if decision.get("required_human_checkpoint") in {"true", "True"}:
        decision["required_human_checkpoint"] = True
    if decision.get("required_human_checkpoint") in {"false", "False"}:
        decision["required_human_checkpoint"] = False
    if (
        decision.get("decision") not in {"APPROVE", "REVIEW", "BLOCK"}
        or not isinstance(decision.get("reason"), str)
        or not isinstance(decision.get("required_human_checkpoint"), bool)
    ):
        return review_decision("The model response did not match the decision schema.")
    if risk in {"MEDIUM", "HIGH"}:
        decision["required_human_checkpoint"] = True
    return decision

def review_decision(reason):
    """Return a safe manual review decision."""
    return {"decision": "REVIEW", "reason": reason, "required_human_checkpoint": True}

def print_decision_packet(state):
    """Print the final governance decision packet."""
    decision = state["decision"]
    print("\nScenario: " + state["scenario"])
    print("Risk: " + state["risk"])
    print("Decision: " + decision["decision"])
    print("Human checkpoint: " + str(decision["required_human_checkpoint"]))
    print("Reason: " + decision["reason"])
    print("Policy memory refs: " + ", ".join(state["policy_refs"]))
    return state

def run_pipeline(client, scenario, request):
    """Run the fixed task pipeline for one request."""
    state = {"client": client, "scenario": scenario, "request": request, "memory": {}}
    pipeline = [validate_request, retrieve_policy_context, assess_request_with_model, print_decision_packet]
    for task in pipeline:
        state = task(state)

def main():
    """Load config and run the demo scenarios."""
    load_dotenv()
    require_env()
    print("Active model: " + os.environ["MODEL_NAME"])
    client = OpenAI(base_url=os.environ["LITELLM_BASE_URL"], api_key=os.environ["LITELLM_API_KEY"])
    for scenario, request in SCENARIOS:
        run_pipeline(client, scenario, request)

if __name__ == "__main__":
    main()
