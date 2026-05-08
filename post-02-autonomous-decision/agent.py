import os
import sys
import time
import math
from typing import Dict, List

from dotenv import load_dotenv
import openai

# ------------------------------------------------------------------------------
# Constants for escalation scoring (can be moved to .env if desired)
# ------------------------------------------------------------------------------
TIER_MULTIPLIER = {
    "standard": 0.3,
    "premium": 0.6,
    "enterprise": 0.9
}
ALERT_WEIGHT = 0.2          # per active alert
ALERT_MAX_CONTRIBUTION = 0.4

# ------------------------------------------------------------------------------
# Environment validation
# ------------------------------------------------------------------------------
def validate_environment():
    """Check that all required environment variables are set; exit if not."""
    required_vars = [
        "LITELLM_BASE_URL",
        "MODEL_NAME",
        "LITELLM_API_KEY",
        "ESCALATION_THRESHOLD",
    ]  
    missing = [v for v in required_vars if os.getenv(v) is None]
    if missing:
            print("ERROR: Missing required environment variables: " + ", ".join(missing))
            sys.exit(1)
# ------------------------------------------------------------------------------
# Customer context
# ------------------------------------------------------------------------------
def build_customer_context(tier: str, active_system_alerts: List[str], urgency_score: float) -> Dict:
    """Return a dictionary with customer tier, system alerts, and urgency."""
    return {
        "customer_tier": tier,
        "active_system_alerts": active_system_alerts,
        "urgency_score": urgency_score
    }

# ------------------------------------------------------------------------------
# Escalation scoring
# ------------------------------------------------------------------------------
def calculate_escalation_score(context: Dict) -> float:
    """
    Compute a weighted escalation score from urgency, tier multiplier, and alerts.
    Score = urgency_score + tier_multiplier + min(number_of_alerts * alert_weight, max_alert_contribution)
    """
    tier = context.get("customer_tier", "standard").lower()
    tier_mult = TIER_MULTIPLIER.get(tier, 0.0)
    alerts = context.get("active_system_alerts", [])
    alert_contrib = min(len(alerts) * ALERT_WEIGHT, ALERT_MAX_CONTRIBUTION)
    score = context["urgency_score"] + tier_mult + alert_contrib
    return score

# ------------------------------------------------------------------------------
# LLM resolution call (only used when autonomous)
# ------------------------------------------------------------------------------
def resolve_issue_with_llm(issue_text: str, context: Dict) -> str:
    """Send the customer issue to the LLM via LiteLLM and return the response text."""
    # Input validation
    if not issue_text or not issue_text.strip():
        return "ERROR: Issue text cannot be empty."
    if len(issue_text) > 2000:
        return "ERROR: Issue text exceeds 2000 character limit."

    # Build system prompt
    system_prompt = (
        "You are a customer support specialist at NosisTech LLC, a boutique AI governance "
        "and cloud security consultancy. You are helping a customer with their issue. "
        "Respond helpfully and professionally."
    )
    user_message = (
        f"Customer tier: {context.get('customer_tier', 'standard').capitalize()}\n"
        f"Active system alerts: {', '.join(context.get('active_system_alerts', [])) or 'None'}\n"
        f"Urgency: {context.get('urgency_score', 0.0)}\n"
        f"Customer issue: {issue_text}"
    )

    # Retry loop with exponential backoff for rate limits
    max_attempts = 3
    base_delay = 1.0
    for attempt in range(1, max_attempts + 1):
        try:
            client = openai.OpenAI(
                base_url=os.getenv("LITELLM_BASE_URL"),
                api_key=os.getenv("LITELLM_API_KEY")
            )
            completion = client.chat.completions.create(
                model=os.getenv("MODEL_NAME"),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7,
                max_tokens=500
            )
            return completion.choices[0].message.content

        except openai.RateLimitError:
            if attempt == max_attempts:
                return "ERROR: Rate limit exceeded after maximum retries. Please try again later."
            wait = base_delay * (2 ** (attempt - 1))
            print(f"Rate limit hit. Retrying in {wait:.1f}s (attempt {attempt}/{max_attempts})...")
            time.sleep(wait)
        except (openai.APIConnectionError, openai.APITimeoutError) as e:
            # Graceful failure: connection is unreachable
            print("ERROR: Unable to reach the AI model endpoint. Please check your network and LiteLLM proxy.")
            sys.exit(1)
        except Exception as e:
            # Catch any other unexpected error and exit cleanly
            print(f"ERROR: An unexpected error occurred: {str(e)}")
            sys.exit(1)

    return "ERROR: Unexpected failure in LLM resolution."

# ------------------------------------------------------------------------------
# Decision engine
# ------------------------------------------------------------------------------
def triage_and_decide(issue_text: str, context: Dict) -> str:
    """
    Main decision pipeline:
    1. Validate inputs
    2. Calculate escalation score
    3. Compare with threshold and either escalate or resolve autonomously via LLM
    4. Print audit trail
    """
    # Input validation (reject early if invalid)
    if not issue_text or not issue_text.strip():
        return "Invalid issue: text is empty."
    if len(issue_text) > 2000:
        return "Invalid issue: exceeds 2000 characters."

    threshold = float(os.getenv("ESCALATION_THRESHOLD", "0.7"))
    score = calculate_escalation_score(context)
    escalate = score >= threshold

    # Audit trail
    print("=== Escalation Audit ===")
    print(f"Customer tier: {context.get('customer_tier', 'N/A')}")
    print(f"Urgency score: {context.get('urgency_score', 0.0):.2f}")
    print(f"Active alerts: {len(context.get('active_system_alerts', []))}")
    print(f"Escalation score: {score:.2f}")
    print(f"Threshold: {threshold}")
    print(f"Decision: {'ESCALATE to human' if escalate else 'AUTONOMOUS resolution'}")
    print("========================")

    if escalate:
        return "ISSUE ESCALATED: This issue requires human attention due to its priority."
    else:
        llm_response = resolve_issue_with_llm(issue_text, context)
        return f"AUTONOMOUS RESOLUTION:\n{llm_response}"


# ------------------------------------------------------------------------------
# Main demonstration
# ------------------------------------------------------------------------------
def main():
    """Demonstrate the agent with three NosisTech scenarios."""
    load_dotenv()
    validate_environment()

    print(f"Active model: {os.getenv('MODEL_NAME')}")

    # Scenario 1: Standard tier, low urgency, no alerts -> autonomous
    print("\n--- Scenario 1: Standard tier, low urgency, no alerts ---")
    ctx1 = build_customer_context("standard", [], 0.2)
    result1 = triage_and_decide("I'm having trouble accessing my dashboard.", ctx1)
    print(result1)

    # Scenario 2: Enterprise tier, low urgency, no alerts -> escalates
    print("\n--- Scenario 2: Enterprise tier, low urgency, no alerts ---")
    ctx2 = build_customer_context("enterprise", [], 0.2)
    result2 = triage_and_decide("Our API keys seem to have expired.", ctx2)
    print(result2)

    # Scenario 3: Premium tier, moderate urgency, one system alert -> escalates
    print("\n--- Scenario 3: Premium tier, moderate urgency, one alert ---")
    ctx3 = build_customer_context("premium", ["PaymentsGatewayDown"], 0.2)
    result3 = triage_and_decide("Cannot process any payments.", ctx3)
    print(result3)

if __name__ == "__main__":
    main()