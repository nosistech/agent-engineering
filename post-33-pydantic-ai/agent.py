# (c) 2026 NosisTech LLC. Original implementation.

import json
import os
import re
import sys
import time
from typing import Literal

from openai import APIConnectionError, OpenAI, OpenAIError, RateLimitError
from pydantic import BaseModel, Field, ValidationError



class UseCase(BaseModel):
    """Structured input model for an enterprise AI use case."""

    title: str
    business_unit: str
    data_sensitivity: Literal["LOW", "MEDIUM", "HIGH"]
    automated_decisioning: bool
    external_user_impact: bool
    description: str


class GovernanceDecision(BaseModel):
    """Structured output model for a governance review decision."""

    decision: Literal["APPROVE", "REVIEW", "REJECT"]
    risk_score: int = Field(ge=0, le=10)
    reason: str
    required_human_review: bool
    policy_flags: list[str]


POLICY_CONTEXT = """
Governance policy:
- HIGH data sensitivity requires REVIEW or REJECT.
- Automated decisioning with external user impact requires human review.
- LOW sensitivity internal summarization can be APPROVE.
- Compliance, eligibility, denial, credit, hiring, housing, insurance, or medical decisions require REVIEW or REJECT.
""".strip()

DEMO_USE_CASES = [
    UseCase(title="Internal Meeting Summarizer", business_unit="Operations", data_sensitivity="LOW", automated_decisioning=False, external_user_impact=False, description="Harborlight Analytics summarizes internal meetings into action items. No customer data is involved."),
    UseCase(title="Customer Support History Summarizer", business_unit="Customer Experience", data_sensitivity="MEDIUM", automated_decisioning=False, external_user_impact=True, description="Northstar Retail Group summarizes support tickets so agents can respond faster. Tickets may contain customer PII."),
    UseCase(title="Automated Service Eligibility Recommendation", business_unit="Civic Services", data_sensitivity="HIGH", automated_decisioning=True, external_user_impact=True, description="Meridian Civic Systems uses AI to recommend eligibility decisions for municipal benefit applications."),
]


def load_env_file() -> None:
    """Load local .env values without an extra dependency."""
    env_path = os.path.join(os.getcwd(), ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, encoding="utf-8") as env_file:
        for line in env_file:
            clean = line.strip()
            if clean and not clean.startswith("#") and "=" in clean:
                name, value = clean.split("=", 1)
                os.environ.setdefault(name.strip(), value.strip())


def load_settings() -> dict[str, str]:
    """Load and validate required environment variables."""
    load_env_file()
    required = ["LITELLM_BASE_URL", "MODEL_NAME", "LITELLM_API_KEY"]
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        print("Missing required environment variables: " + ", ".join(missing))
        print("Copy .env.template to .env and fill in all values.")
        sys.exit(1)
    return {name: os.environ[name] for name in required}


def build_client(settings: dict[str, str]) -> OpenAI:
    """Create an OpenAI-compatible client pointed at LiteLLM."""
    return OpenAI(base_url=settings["LITELLM_BASE_URL"], api_key=settings["LITELLM_API_KEY"])


def build_prompt(use_case: UseCase, policy_context: str, correction: str = "") -> list[dict[str, str]]:
    """Build model messages for one governance classification."""
    schema = '{"decision":"APPROVE|REVIEW|REJECT","risk_score":0-10,"reason":"string","required_human_review":true|false,"policy_flags":["string"]}'
    prompt = "\n".join(["Return only valid JSON matching this schema:", schema, policy_context, "Use case:", use_case.model_dump_json()])
    if correction:
        prompt += "\nCorrect this validation problem: " + correction
    return [
        {"role": "system", "content": "You are a careful AI governance reviewer."},
        {"role": "user", "content": prompt},
    ]


def extract_json_object(raw_text: str) -> dict:
    """Extract the first JSON object from model text."""
    cleaned = re.sub(r"```(?:json)?", "", raw_text).replace("```", "").strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in the model response.")
    return json.loads(match.group())


def call_model_with_retries(client: OpenAI, model: str, messages: list[dict[str, str]]) -> str:
    """Call the model with rate-limit backoff."""
    for attempt in range(3):
        try:
            response = client.chat.completions.create(model=model, messages=messages, temperature=0.1)
            content = response.choices[0].message.content
            if not content:
                raise ValueError("The model returned an empty response.")
            return content
        except RateLimitError:
            if attempt < 2:
                time.sleep(2**attempt * 5)
                continue
            print("The model provider is still rate-limiting requests. Try again later.")
        except APIConnectionError:
            print("Cannot reach LiteLLM. Check that the proxy is running.")
        except (OpenAIError, ValueError):
            print("The model call failed. Check your LiteLLM settings and model name.")
        sys.exit(1)


def enforce_policy_floor(use_case: UseCase, decision: GovernanceDecision) -> GovernanceDecision:
    """Raise decisions that violate the local governance policy."""
    sensitive_external = use_case.data_sensitivity in ("MEDIUM", "HIGH") and use_case.external_user_impact
    automated_external = use_case.automated_decisioning and use_case.external_user_impact
    restricted_terms = ("compliance", "eligibility", "denial", "credit", "hiring", "housing", "insurance", "medical")
    restricted_decision = any(term in use_case.description.lower() for term in restricted_terms)
    if decision.decision == "APPROVE" and (sensitive_external or automated_external or restricted_decision):
        flags = list(dict.fromkeys([*decision.policy_flags, "LOCAL_POLICY_REVIEW_REQUIRED"]))
        score = max(decision.risk_score, 5 if use_case.data_sensitivity == "MEDIUM" else 7)
        return decision.model_copy(update={"decision": "REVIEW", "risk_score": score, "required_human_review": True, "policy_flags": flags})
    if decision.decision in ("REVIEW", "REJECT"):
        return decision.model_copy(update={"required_human_review": True})
    return decision

def classify_use_case(client: OpenAI, model: str, use_case: UseCase, policy_context: str) -> GovernanceDecision:
    """Classify one use case with validation retries."""
    correction = ""
    for _ in range(3):
        raw_text = call_model_with_retries(client, model, build_prompt(use_case, policy_context, correction))
        try:
            decision = GovernanceDecision(**extract_json_object(raw_text))
            return enforce_policy_floor(use_case, decision)
        except (json.JSONDecodeError, ValidationError, ValueError) as error:
            correction = str(error)
    print("Could not validate the model's governance decision after three attempts.")
    sys.exit(1)


def print_decision(use_case: UseCase, decision: GovernanceDecision) -> None:
    """Print one governance decision."""
    print("\nUse Case: " + use_case.title)
    print("Decision: " + decision.decision)
    print("Risk Score: " + str(decision.risk_score) + "/10")
    print("Human Review: " + str(decision.required_human_review))
    print("Policy Flags: " + (", ".join(decision.policy_flags) or "None"))
    print("Reason: " + decision.reason)


def main() -> None:
    """Load configuration and classify the demo use cases."""
    settings = load_settings()
    print("Active model: " + settings["MODEL_NAME"])
    client = build_client(settings); started = time.perf_counter()
    for use_case in DEMO_USE_CASES:
        decision = classify_use_case(client, settings["MODEL_NAME"], use_case, POLICY_CONTEXT)
        print_decision(use_case, decision)
    print("\nTotal Runtime: " + str(round(time.perf_counter() - started, 2)) + " seconds")


if __name__ == "__main__":
    main()





