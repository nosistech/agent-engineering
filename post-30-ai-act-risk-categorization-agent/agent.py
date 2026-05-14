import os
import sys

from dotenv import load_dotenv
from openai import OpenAI


DISCLAIMER = (
    "Educational demo only. This uses a hypothetical AI system description. "
    "It is not legal advice, regulatory advice, compliance certification, or "
    "a legal status determination. For certainty, consult qualified legal "
    "counsel in the relevant jurisdiction. The May 7, 2026 Digital Omnibus "
    "on AI is treated here as provisional pending formal adoption, not final law."
)

DEMO_SYSTEM = {
    "name": "Hiring Screen Assist",
    "purpose": "Scores job applications and recommends which candidates should be interviewed.",
    "data_used": "CVs, employment history, education history, and recruiter feedback.",
    "deployment_context": "Used by an HR team before human hiring managers review applicants.",
}

RULES = [
    (
        "Unacceptable Risk",
        ["social scoring", "real-time biometric", "subliminal", "child sexual abuse", "nudifier"],
    ),
    (
        "High Risk",
        ["hiring", "job application", "cv", "employment", "credit scoring", "education", "medical device", "law enforcement", "border control"],
    ),
    (
        "Limited Risk",
        ["chatbot", "deepfake", "ai-generated content", "synthetic media"],
    ),
]

TIER_DETAILS = {
    "Unacceptable Risk": {
        "obligations": ["Potential prohibited AI practice if the facts match Article 5."],
        "actions": ["Do not deploy based on this demo.", "Escalate to qualified legal counsel."],
        "review": True,
    },
    "High Risk": {
        "obligations": ["Risk management", "Data governance", "Technical documentation", "Human oversight", "Logging"],
        "actions": ["Prepare legal review.", "Document intended use and affected people.", "Check Annex III or Annex I scope."],
        "review": True,
    },
    "Limited Risk": {
        "obligations": ["Transparency duties may apply."],
        "actions": ["Tell users when they interact with AI or receive AI-generated content."],
        "review": False,
    },
    "Minimal Risk": {
        "obligations": ["No special EU AI Act duty found by this demo."],
        "actions": ["Keep normal privacy, security, and product controls."],
        "review": False,
    },
}


def load_client():
    load_dotenv()
    missing = [name for name in ["LITELLM_BASE_URL", "MODEL_NAME", "LITELLM_API_KEY"] if not os.getenv(name)]
    if missing:
        print("Missing environment variables: " + ", ".join(missing))
        sys.exit(1)

    base_url = os.environ["LITELLM_BASE_URL"].rstrip("/")
    if not base_url.endswith("/v1"):
        base_url += "/v1"

    return OpenAI(base_url=base_url, api_key=os.environ["LITELLM_API_KEY"]), os.environ["MODEL_NAME"]


def describe(system):
    return (
        f"Name: {system['name']}\n"
        f"Purpose: {system['purpose']}\n"
        f"Data used: {system['data_used']}\n"
        f"Deployment context: {system['deployment_context']}"
    )


def classify_with_rules(system):
    text = describe(system).lower()
    for tier, keywords in RULES:
        matches = [word for word in keywords if word in text]
        if matches:
            return tier, matches
    return "Minimal Risk", []


def ask_model_to_explain(client, model, system, tier, matches):
    prompt = f"""
Explain this educational EU AI Act demo result in three short sentences.
Do not give legal advice. Mention that qualified legal review is needed for real decisions.
Use cautious language such as "may", "could", and "would require review".
Do not state legal obligations as final conclusions.
If you mention the May 7, 2026 Digital Omnibus, call it provisional pending formal adoption.

AI system:
{describe(system)}

Rule tier: {tier}
Rule matches: {matches or ["none"]}
"""
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    return response.choices[0].message.content.strip()


def print_report(system, tier, matches, explanation):
    details = TIER_DETAILS[tier]
    print("\nAI Act Risk Categorization Demo")
    print("=" * 33)
    print(describe(system))
    print(f"\nTier assigned by rules: {tier}")
    print(f"Rule matches: {', '.join(matches) or 'none'}")
    print(f"Human or legal review required: {details['review']}")
    print(f"\nExplanation:\n{explanation}")
    print("\nObligations flagged by this demo:")
    for item in details["obligations"]:
        print(f"- {item}")
    print("\nRecommended actions:")
    for item in details["actions"]:
        print(f"- {item}")
    print(f"\nDisclaimer: {DISCLAIMER}")


def main():
    client, model = load_client()
    tier, matches = classify_with_rules(DEMO_SYSTEM)
    explanation = ask_model_to_explain(client, model, DEMO_SYSTEM, tier, matches)
    print_report(DEMO_SYSTEM, tier, matches, explanation)


if __name__ == "__main__":
    main()
