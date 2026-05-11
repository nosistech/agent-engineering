# MIT License, Copyright 2025 Packt

"""
Conflict Resolution Agent — Multi-Agent HITL workflow for claims processing.
Uses LiteLLM as a proxy to any LLM; config via environment variables.
No frameworks: pure Python, OpenAI SDK pointed at LiteLLM.
"""

import os
import sys
import json
import time
import datetime
from dotenv import load_dotenv
import openai

# ---------------------------------------------------------------------------
# 1. Startup: environment and configuration
# ---------------------------------------------------------------------------
load_dotenv()

REQUIRED_VARS = [
    "LITELLM_BASE_URL",
    "MODEL_NAME",
    "LITELLM_API_KEY",
    "CONFLICT_THRESHOLD",
    "AUTO_APPROVE_CONFIDENCE",
]

missing = [v for v in REQUIRED_VARS if not os.getenv(v)]
if missing:
    print(f"Missing required environment variables: {', '.join(missing)}")
    sys.exit(1)

base_url = os.getenv("LITELLM_BASE_URL")
model_name = os.getenv("MODEL_NAME")
api_key = os.getenv("LITELLM_API_KEY")
conflict_threshold = float(os.getenv("CONFLICT_THRESHOLD"))
auto_approve_confidence = float(os.getenv("AUTO_APPROVE_CONFIDENCE"))

print(f"Active model: {model_name}")

client = openai.OpenAI(base_url=base_url, api_key=api_key)

# ---------------------------------------------------------------------------
# 2. Sample claims (NosisTech LLC)
# ---------------------------------------------------------------------------
SAMPLE_CLAIMS = [
    {
        "claim_id": "NOS-2025-001",
        "description": "Cybersecurity incident response after a phishing attack: forensic analysis, system restoration, and employee training.",
        "amount": 15000,
        "claimant": "NosisTech LLC"
    },
    {
        "claim_id": "NOS-2025-002",
        "description": "Office equipment theft: three laptops and a projector stolen from NosisTech main office.",
        "amount": 8500,
        "claimant": "NosisTech LLC"
    },
    {
        "claim_id": "NOS-2025-003",
        "description": "Claim for lost revenue due to an alleged server outage; no maintenance logs or third-party verification provided.",
        "amount": 75000,
        "claimant": "NosisTech LLC"
    },
]

# ---------------------------------------------------------------------------
# 3. Helper: safe LLM call with retry for rate limits
# ---------------------------------------------------------------------------
def call_llm_with_retry(messages, max_retries=3):
    """Call LiteLLM with exponential backoff on rate-limit errors."""
    for attempt in range(1, max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=0.0,
            )
            return response.choices[0].message.content.strip()
        except openai.RateLimitError:
            if attempt == max_retries:
                raise
            wait = 2 ** attempt
            print(f"Rate limited. Retrying in {wait} seconds ...")
            time.sleep(wait)

# ---------------------------------------------------------------------------
# 4. Reviewer functions
# ---------------------------------------------------------------------------
def _parse_reviewer_json(raw_text):
    """Attempt to parse JSON from the model output; returns a safe default on failure."""
    try:
        cleaned = raw_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        data = json.loads(cleaned)
        recommendation = data.get("recommendation", "REJECT")
        confidence = float(data.get("confidence", 0.0))
        if recommendation not in ("APPROVE", "REJECT"):
            recommendation = "REJECT"
        if not (0.0 <= confidence <= 1.0):
            confidence = 0.0
        return {"recommendation": recommendation, "confidence": confidence}
    except (json.JSONDecodeError, ValueError, TypeError):
        print(f"Malformed JSON from model. Defaulting to REJECT.")
        return {"recommendation": "REJECT", "confidence": 0.0}

def reviewer_one(claim):
    """Evaluate claim for validity and fraud risk; return recommendation and confidence."""
    system_prompt = (
        "You are an insurance claim reviewer. You evaluate claims for validity and fraud risk. "
        "Given the claim details, return ONLY a JSON object with 'recommendation' (APPROVE or REJECT) "
        "and 'confidence' (a float between 0.0 and 1.0). Consider the description, amount, and claimant. "
        "Do not include any other text."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(claim)},
    ]
    try:
        raw = call_llm_with_retry(messages)
        return _parse_reviewer_json(raw)
    except Exception as e:
        print("Reviewer One failed. Defaulting to REJECT with 0.0 confidence.")
        return {"recommendation": "REJECT", "confidence": 0.0}

def reviewer_two(claim):
    """Evaluate claim from a risk-minimisation perspective; return recommendation and confidence."""
    system_prompt = (
        "You are an insurance risk manager. Your primary goal is to minimise unjustified payouts. "
        "Given the claim details, return ONLY a JSON object with 'recommendation' (APPROVE or REJECT) "
        "and 'confidence' (a float between 0.0 and 1.0). Scrutinise the claim carefully. "
        "Do not include any other text."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(claim)},
    ]
    try:
        raw = call_llm_with_retry(messages)
        return _parse_reviewer_json(raw)
    except Exception as e:
        print(f"Reviewer Two failed. Defaulting to REJECT with 0.0 confidence.")
        return {"recommendation": "REJECT", "confidence": 0.0}

# ---------------------------------------------------------------------------
# 5. Conflict detection and human escalation
# ---------------------------------------------------------------------------
def detect_conflict(result_one, result_two):
    """Return True if the confidence difference exceeds the configured threshold."""
    return abs(result_one["confidence"] - result_two["confidence"]) > conflict_threshold

def escalate_to_human(claim, result_one, result_two):
    """Print a plain-English conflict summary and wait for APPROVE or REJECT."""
    delta = abs(result_one["confidence"] - result_two["confidence"])
    print("\n" + "=" * 70)
    print("ESCALATION REQUIRED — reviewers disagree.")
    print(f"Claim ID   : {claim['claim_id']}")
    print(f"Claimant   : {claim['claimant']}")
    print(f"Amount     : ${claim['amount']:,}")
    print(f"Description: {claim['description']}")
    print("-" * 70)
    print(f"Reviewer 1 : {result_one['recommendation']} (confidence {result_one['confidence']:.2f})")
    print(f"Reviewer 2 : {result_two['recommendation']} (confidence {result_two['confidence']:.2f})")
    print(f"Delta      : {delta:.2f} (threshold {conflict_threshold:.2f})")
    print("=" * 70)
    while True:
        decision = input("Your decision (APPROVE / REJECT): ").strip().upper()
        if decision in ("APPROVE", "REJECT"):
            return decision
        print("Please type APPROVE or REJECT.")

# ---------------------------------------------------------------------------
# 6. Claim validation and processing orchestrator
# ---------------------------------------------------------------------------
def validate_claim(claim):
    """Return True if the claim dict contains all required fields."""
    required_fields = {"claim_id", "description", "amount", "claimant"}
    missing_fields = required_fields - set(claim.keys())
    if missing_fields:
        print(f"Claim missing fields: {missing_fields}. Skipping.")
        return False
    return True

def process_claim(claim):
    """Run the complete HITL flow and return a decision dict."""
    if not validate_claim(claim):
        return None

    print(f"\nProcessing claim {claim['claim_id']} ...")

    result_one = reviewer_one(claim)
    result_two = reviewer_two(claim)

    conflict = detect_conflict(result_one, result_two)

    if not conflict:
        if result_one["confidence"] >= result_two["confidence"]:
            best = result_one
            source = "reviewer_one"
        else:
            best = result_two
            source = "reviewer_two"

        if best["confidence"] >= auto_approve_confidence:
            final_decision = best["recommendation"]
            decided_by = "AUTO"
            reason = (
                f"No conflict. {source} gave {final_decision} "
                f"with confidence {best['confidence']:.2f}."
            )
            print(f"AUTO decision: {final_decision}")
        else:
            print("No conflict but confidence too low. Escalating to human.")
            final_decision = escalate_to_human(claim, result_one, result_two)
            decided_by = "HUMAN"
            reason = "Agreement below auto-approve threshold. Human override."
    else:
        final_decision = escalate_to_human(claim, result_one, result_two)
        decided_by = "HUMAN"
        reason = "Conflict exceeded threshold. Human override."

    return {
        "claim_id": claim["claim_id"],
        "final_decision": final_decision,
        "decided_by": decided_by,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "reviewer_one": result_one,
        "reviewer_two": result_two,
        "conflict_detected": conflict,
        "reason": reason,
    }

# ---------------------------------------------------------------------------
# 7. Audit log writer
# ---------------------------------------------------------------------------
def write_audit_log(decisions, filename="decisions.jsonl"):
    """Append one decision per line to a JSONL audit file."""
    with open(filename, "a", encoding="utf-8") as fh:
        for d in decisions:
            fh.write(json.dumps(d) + "\n")

# ---------------------------------------------------------------------------
# 8. Main entry point
# ---------------------------------------------------------------------------
def main():
    """Process all sample claims and display a summary table."""
    decisions = []
    for claim in SAMPLE_CLAIMS:
        decision = process_claim(claim)
        if decision:
            decisions.append(decision)

    write_audit_log(decisions)

    print("\n\n" + "=" * 70)
    print("CLAIM PROCESSING SUMMARY")
    print(f"{'Claim ID':<18} {'Decision':<10} {'Decided By':<12} {'Time'}")
    print("-" * 70)
    for d in decisions:
        time_str = d["timestamp"][:19].replace("T", " ")
        print(f"{d['claim_id']:<18} {d['final_decision']:<10} {d['decided_by']:<12} {time_str}")
    print("=" * 70)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)