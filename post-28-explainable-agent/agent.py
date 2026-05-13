# MIT License, Copyright 2025 Packt

import json
import os
import sys
from urllib.request import Request, urlopen


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

APPLICATION = {
    "application_id": "APP-DEMO",
    "revenue_growth": 18.5,
    "debt_ratio": 0.72,
    "months_in_business": 14.0,
    "credit_score": 610.0,
}

# field, label, max points, target value, higher value is better
FEATURES = [
    ("revenue_growth", "Revenue growth", 25, 25.0, True),
    ("debt_ratio", "Debt ratio", 25, 0.35, False),
    ("months_in_business", "Months in business", 20, 24.0, True),
    ("credit_score", "Credit score", 30, 680.0, True),
]


def load_env() -> None:
    path = os.path.join(PROJECT_DIR, ".env")
    if not os.path.exists(path):
        return
    for line in open(path, encoding="utf-8"):
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.strip().split("=", 1)
            os.environ.setdefault(key, value)


def require_env() -> None:
    missing = [key for key in ("LITELLM_BASE_URL", "MODEL_NAME", "LITELLM_API_KEY") if not os.getenv(key)]
    if missing:
        raise SystemExit(f"Missing environment variables: {', '.join(missing)}")
    print(f"[INFO] Active model: {os.getenv('MODEL_NAME')}")


def call_llm(prompt: str) -> str:
    payload = json.dumps(
        {
            "model": os.getenv("MODEL_NAME"),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
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


def score_feature(value: float, target: float, higher_is_better: bool) -> float:
    ratio = value / target if higher_is_better else target / max(value, 0.01)
    return max(0.0, min(1.0, ratio))


def explain(application: dict) -> dict:
    factors = []
    total = 0.0

    for field, label, max_points, target, higher_is_better in FEATURES:
        earned = round(score_feature(application[field], target, higher_is_better) * max_points, 2)
        total += earned
        factors.append({"field": field, "label": label, "earned": earned, "max": max_points, "target": target})

    strongest = max(factors, key=lambda item: item["earned"] / item["max"])
    weakest = min(factors, key=lambda item: item["earned"] / item["max"])
    return {
        "application_id": application["application_id"],
        "decision": "approve" if total >= 70 else "decline",
        "score": round(total, 2),
        "confidence": round(max(0.1, min(0.99, abs(total - 70) / 30)), 2),
        "factors": factors,
        "strongest": strongest,
        "weakest": weakest,
        "counterfactual": f"Improving {weakest['label']} toward {weakest['target']} would most improve the result.",
    }


def summarize(report: dict, audience: str) -> str:
    if audience == "applicant":
        result = "met" if report["decision"] == "approve" else "did not meet"
        prompt = (
            "Write an applicant-friendly explanation for this educational example. "
            "Do not include scores, point values, probabilities, target numbers, JSON, "
            "or the words declined, approve, approved, or financing. Say it is not a "
            "final lending decision or financial advice. Keep it under 100 words.\n\n"
            f"Example result: {result} the example threshold\n"
            f"Positive factor: {report['strongest']['label']}\n"
            f"Main improvement area: {report['weakest']['label']}"
        )
    else:
        prompt = (
            "Write an analyst explanation for this educational synthetic example. "
            "Mention score, confidence, strongest factor, weakest factor, and counterfactual. "
            "Keep it under 120 words.\n\n"
            + json.dumps(report, indent=2)
        )
    return call_llm(prompt)


def main() -> None:
    load_env()
    require_env()
    report = explain(APPLICATION)

    print("=== MODEL OUTPUT ===")
    print(json.dumps(report, indent=2))
    print("\n=== ANALYST SUMMARY ===")
    print(summarize(report, "analyst"))
    print("\n=== APPLICANT SUMMARY ===")
    print(summarize(report, "applicant"))


if __name__ == "__main__":
    main()
