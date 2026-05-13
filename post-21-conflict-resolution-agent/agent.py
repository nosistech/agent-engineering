# MIT License, Copyright 2025 Packt

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


PROJECT_DIR = Path(__file__).resolve().parent

CLAIMS = [
    {
        "claim_id": "NOS-2025-001",
        "description": "Forensic analysis and system restoration after a verified phishing attack.",
        "amount": 15000,
        "claimant": "NosisTech LLC",
    },
    {
        "claim_id": "NOS-2025-002",
        "description": "Lost revenue from an alleged server outage with no logs or third-party evidence.",
        "amount": 75000,
        "claimant": "NosisTech LLC",
    },
]

REVIEWERS = [
    ("Coverage Reviewer", "Evaluate whether the claim appears valid and covered."),
    ("Risk Reviewer", "Scrutinize the claim for weak evidence or unjustified payout risk."),
]


def load_env() -> None:
    path = PROJECT_DIR / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def require_env() -> None:
    needed = ["LITELLM_BASE_URL", "MODEL_NAME", "LITELLM_API_KEY", "CONFLICT_THRESHOLD"]
    missing = [key for key in needed if not os.getenv(key)]
    if missing:
        raise SystemExit(f"Missing environment variables: {', '.join(missing)}")
    print(f"[INFO] Active model: {os.getenv('MODEL_NAME')}")


def call_llm(prompt: str) -> str:
    payload = json.dumps(
        {
            "model": os.getenv("MODEL_NAME"),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
        }
    ).encode("utf-8")
    request = Request(
        os.getenv("LITELLM_BASE_URL").rstrip("/") + "/chat/completions",
        data=payload,
        headers={
            "Authorization": "Bearer " + os.getenv("LITELLM_API_KEY"),
            "Content-Type": "application/json",
        },
    )
    with urlopen(request, timeout=60) as response:
        data = json.loads(response.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"].strip()


def parse_review(raw: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.IGNORECASE)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        data = {}
    recommendation = data.get("recommendation", "REJECT")
    confidence = float(data.get("confidence", 0))
    if recommendation not in {"APPROVE", "REJECT"}:
        recommendation = "REJECT"
    return {"recommendation": recommendation, "confidence": max(0.0, min(1.0, confidence))}


def review_claim(claim: dict, reviewer_name: str, perspective: str) -> dict:
    prompt = (
        f"You are {reviewer_name}. {perspective}\n"
        "Return only JSON with keys recommendation and confidence. "
        "recommendation must be APPROVE or REJECT. confidence must be 0.0 to 1.0.\n\n"
        f"Claim:\n{json.dumps(claim, indent=2)}"
    )
    result = parse_review(call_llm(prompt))
    result["reviewer"] = reviewer_name
    return result


def decide(claim: dict, reviews: list[dict]) -> dict:
    threshold = float(os.getenv("CONFLICT_THRESHOLD", "0.25"))
    auto_confidence = float(os.getenv("AUTO_APPROVE_CONFIDENCE", "0.85"))
    recommendations = {review["recommendation"] for review in reviews}
    confidence_gap = abs(reviews[0]["confidence"] - reviews[1]["confidence"])
    conflict = len(recommendations) > 1 or confidence_gap > threshold

    if conflict:
        final = os.getenv("HUMAN_REVIEW_DECISION", "HUMAN_REVIEW_REQUIRED")
        decided_by = "HUMAN" if final in {"APPROVE", "REJECT"} else "CHECKPOINT"
    else:
        best = max(reviews, key=lambda item: item["confidence"])
        final = best["recommendation"] if best["confidence"] >= auto_confidence else "HUMAN_REVIEW_REQUIRED"
        decided_by = "AUTO" if final in {"APPROVE", "REJECT"} else "CHECKPOINT"

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "claim_id": claim["claim_id"],
        "final_decision": final,
        "decided_by": decided_by,
        "conflict_detected": conflict,
        "reviews": reviews,
    }


def audit_path() -> Path:
    path = Path(os.getenv("AUDIT_LOG_PATH", "decisions.jsonl"))
    return path if path.is_absolute() else PROJECT_DIR / path


def append_audit(decision: dict) -> None:
    with open(audit_path(), "a", encoding="utf-8") as file:
        file.write(json.dumps(decision) + "\n")


def process_claim(claim: dict) -> dict:
    print(f"\n[CLAIM] {claim['claim_id']}: ${claim['amount']:,}")
    reviews = [review_claim(claim, name, perspective) for name, perspective in REVIEWERS]
    for review in reviews:
        print(f"{review['reviewer']}: {review['recommendation']} ({review['confidence']:.2f})")
    decision = decide(claim, reviews)
    append_audit(decision)
    print(f"Final: {decision['final_decision']} via {decision['decided_by']}")
    return decision


def main() -> None:
    load_env()
    require_env()
    decisions = [process_claim(claim) for claim in CLAIMS]
    print("\nSUMMARY")
    for decision in decisions:
        print(f"{decision['claim_id']}: {decision['final_decision']} ({decision['decided_by']})")


if __name__ == "__main__":
    main()
