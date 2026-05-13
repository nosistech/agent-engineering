# (c) 2026 NosisTech LLC. Original implementation.

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
os.environ.setdefault("DSPY_CACHEDIR", str(ROOT / ".cache" / "dspy"))

import dspy


REQUIRED_ENV = ("LITELLM_BASE_URL", "MODEL_NAME", "LITELLM_API_KEY")

SAMPLE_EMAILS = [
    (
        "Billing dispute",
        "Subject: Overcharge on invoice #2341\n\n"
        "I found a charge I did not authorize. Please investigate and remove it.",
    ),
    (
        "Onboarding help",
        "Subject: Need setup assistance\n\n"
        "We signed up yesterday and need guidance setting up our first cloud assessment.",
    ),
    (
        "Security alert",
        "Subject: Urgent suspicious login\n\n"
        "I received an alert about a login from another country. Please block the account.",
    ),
]


def load_env():
    env_file = ROOT / ".env"
    if not env_file.exists():
        return

    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


class TicketRouter(dspy.Signature):
    """Classify a support ticket for a SaaS operations team."""

    email_text = dspy.InputField(desc="Full client support email")
    category = dspy.OutputField(desc="One of: Billing, Technical, Onboarding, Security")
    priority = dspy.OutputField(desc="One of: High, Medium, Low")
    requires_human = dspy.OutputField(desc="True or False")


def configure_dspy():
    model_name = os.getenv("MODEL_NAME")
    lm = dspy.LM(
        model=f"openai/{model_name}",
        api_base=os.getenv("LITELLM_BASE_URL"),
        api_key=os.getenv("LITELLM_API_KEY"),
    )
    dspy.configure(lm=lm)
    print(f"MODEL: {model_name}")


def print_result(label, result):
    print(f"{label}:")
    print(f"  category: {result.category}")
    print(f"  priority: {result.priority}")
    print(f"  requires_human: {result.requires_human}")


def run_router(name, router):
    print(f"\n=== {name} ===")
    for title, email in SAMPLE_EMAILS:
        print(f"\nTicket: {title}")
        print_result("Result", router(email_text=email))


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    load_env()

    missing = [key for key in REQUIRED_ENV if not os.getenv(key)]
    if missing:
        raise SystemExit(f"Missing environment variables: {', '.join(missing)}")

    configure_dspy()
    run_router("DSPy Predict", dspy.Predict(TicketRouter))
    run_router("DSPy ChainOfThought", dspy.ChainOfThought(TicketRouter))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        raise SystemExit(f"DSPy run failed: {error}") from error
