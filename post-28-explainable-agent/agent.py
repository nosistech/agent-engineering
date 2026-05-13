# MIT License, Copyright 2025 Packt

import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

DEMO_APPLICATION = {
    "application_id": "APP-DEMO",
    "revenue_growth": 18.5,
    "debt_ratio": 0.72,
    "months_in_business": 14.0,
    "credit_score": 610.0,
}

FEATURES = {
    "revenue_growth": {"label": "Revenue growth", "weight": 25, "target": 25.0, "higher_is_better": True},
    "debt_ratio": {"label": "Debt ratio", "weight": 25, "target": 0.35, "higher_is_better": False},
    "months_in_business": {"label": "Months in business", "weight": 20, "target": 24.0, "higher_is_better": True},
    "credit_score": {"label": "Credit score", "weight": 30, "target": 680.0, "higher_is_better": True},
}


def load_env_file(path: str = ".env") -> None:
    if not os.path.exists(path):
        return

    with open(path, encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


load_env_file(os.path.join(PROJECT_DIR, ".env"))


def safe_print(text: str) -> None:
    print(text.encode("ascii", errors="replace").decode("ascii"))


def env_value(primary: str, fallback: str | None = None) -> str | None:
    return os.getenv(primary) or (os.getenv(fallback) if fallback else None)


def check_environment() -> None:
    required = {
        "LITELLM_BASE_URL": env_value("LITELLM_BASE_URL", "API_BASE"),
        "MODEL_NAME": env_value("MODEL_NAME", "MODEL"),
        "LITELLM_API_KEY": env_value("LITELLM_API_KEY", "LITELLM_MASTER_KEY"),
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        safe_print(f"[ERROR] Missing environment variables: {', '.join(missing)}")
        sys.exit(1)
    safe_print(f"[INFO] Active model: {required['MODEL_NAME']}")


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def feature_score(name: str, value: float) -> float:
    spec = FEATURES[name]
    target = spec["target"]
    if spec["higher_is_better"]:
        return clamp(value / target)
    return clamp(target / max(value, 0.01))


def evaluate_application(application: dict[str, float]) -> dict:
    contributions = {}
    total_score = 0.0

    for name, spec in FEATURES.items():
        score = feature_score(name, float(application[name]))
        points = round(score * spec["weight"], 2)
        contributions[name] = {
            "label": spec["label"],
            "value": application[name],
            "points": points,
            "max_points": spec["weight"],
        }
        total_score += points

    decision = "approve" if total_score >= 70 else "decline"
    confidence = round(abs(total_score - 70) / 30, 2)
    confidence = clamp(confidence, 0.1, 0.99)

    return {
        "application_id": application["application_id"],
        "decision": decision,
        "score": round(total_score, 2),
        "confidence": confidence,
        "attributions": contributions,
    }


def counterfactual(evaluation: dict) -> str:
    if evaluation["decision"] == "approve":
        return "The application already qualifies under this synthetic scoring model."

    weakest = min(
        evaluation["attributions"].items(),
        key=lambda item: item[1]["points"] / item[1]["max_points"],
    )
    name, details = weakest
    target = FEATURES[name]["target"]
    return f"Improving {details['label']} toward {target} would most improve the result."


def call_llm(messages: list[dict[str, str]]) -> str:
    base_url = env_value("LITELLM_BASE_URL", "API_BASE").rstrip("/")
    payload = json.dumps(
        {
            "model": env_value("MODEL_NAME", "MODEL"),
            "messages": messages,
            "temperature": 0.2,
        }
    ).encode("utf-8")

    request = Request(
        f"{base_url}/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {env_value('LITELLM_API_KEY', 'LITELLM_MASTER_KEY')}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=60) as response:
            body = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"LiteLLM returned HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Could not reach LiteLLM at {base_url}: {exc}") from exc

    return body["choices"][0]["message"]["content"].strip()


def summarize_for_audience(evaluation: dict, improvement: str, audience: str) -> str:
    attributions = evaluation["attributions"]
    strongest = max(attributions.values(), key=lambda item: item["points"] / item["max_points"])
    weakest = min(attributions.values(), key=lambda item: item["points"] / item["max_points"])

    if audience == "applicant":
        plain_outcome = "did not meet the example approval threshold"
        if evaluation["decision"] == "approve":
            plain_outcome = "met the example approval threshold"
        plain_improvement = f"Improving {weakest['label'].lower()} would most improve the result."
        user_prompt = (
            "Audience: applicant\n"
            f"Synthetic outcome: {plain_outcome}\n"
            f"Positive factor: {strongest['label']}\n"
            f"Main improvement area: {weakest['label']}\n"
            f"Suggested improvement: {plain_improvement}\n\n"
            "Write in plain language. Do not include scores, point values, probabilities, "
            "confidence values, target numbers, JSON, or technical model terms. Do not use "
            "the word declined. Say this is an educational example, not a final lending "
            "decision or financial advice."
        )
    else:
        user_prompt = (
            "Audience: analyst\n"
            f"Evaluation JSON:\n{json.dumps(evaluation, indent=2)}\n"
            f"Computed strongest factor: {strongest['label']}\n"
            f"Computed weakest factor: {weakest['label']}\n"
            f"Counterfactual: {improvement}\n\n"
            "Mention score, confidence, strongest factor, weakest factor, and the counterfactual. "
            "Say this is an educational synthetic example."
        )

    messages = [
        {
            "role": "system",
            "content": (
                "You summarize synthetic loan-model explanations. "
                "This is educational only, not a real lending decision or financial advice. "
                "Keep the response under 120 words."
            ),
        },
        {"role": "user", "content": user_prompt},
    ]
    return call_llm(messages)


def run_demo() -> None:
    evaluation = evaluate_application(DEMO_APPLICATION)
    improvement = counterfactual(evaluation)

    safe_print("=== MODEL OUTPUT ===")
    safe_print(f"Application: {evaluation['application_id']}")
    safe_print(f"Decision: {evaluation['decision']}")
    safe_print(f"Score: {evaluation['score']}")
    safe_print(f"Confidence: {evaluation['confidence']}")
    safe_print(f"Attributions: {json.dumps(evaluation['attributions'], indent=2)}")
    safe_print(f"Counterfactual: {improvement}\n")

    safe_print("=== ANALYST SUMMARY ===")
    safe_print(summarize_for_audience(evaluation, improvement, "analyst"))

    safe_print("\n=== APPLICANT SUMMARY ===")
    safe_print(summarize_for_audience(evaluation, improvement, "applicant"))


if __name__ == "__main__":
    check_environment()
    run_demo()
