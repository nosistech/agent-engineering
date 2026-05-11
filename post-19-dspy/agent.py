# (c) 2026 NosisTech LLC. Original implementation.

import os
import sys
import time
from dotenv import load_dotenv
import dspy

load_dotenv()

def validate_env():
    """Check that all required environment variables are present."""
    missing = []
    for var in ("LITELLM_BASE_URL", "MODEL_NAME", "LITELLM_API_KEY"):
        if not os.getenv(var):
            missing.append(var)
    if missing:
        print(f"Missing environment variables: {', '.join(missing)}")
        print("Please set them in your .env file or environment.")
        sys.exit(1)

def configure_dspy():
    """Configure DSPy to use LiteLLM proxy with model from environment."""
    base_url = os.getenv("LITELLM_BASE_URL")
    model_name = os.getenv("MODEL_NAME")
    api_key = os.getenv("LITELLM_API_KEY")
    model_string = f"openai/{model_name}"
    print(f"Using model: {model_name}")
    lm = dspy.LM(model=model_string, api_base=base_url, api_key=api_key)
    dspy.configure(lm=lm)

class TicketRouter(dspy.Signature):
    """Classify support ticket category, priority, and human escalation need."""
    email_text = dspy.InputField(desc="Full email text from client")
    category = dspy.OutputField(desc="One of: Billing, Technical, Onboarding, Security")
    priority = dspy.OutputField(desc="One of: High, Medium, Low")
    requires_human = dspy.OutputField(desc="Boolean: True if human escalation is needed, False otherwise")

sample_emails = [
    ("Subject: Billing Inquiry - Overcharge on invoice #2341\n\n"
     "Dear NosisTech Support,\n\n"
     "I have found a charge on my invoice that I did not authorize. "
     "Please investigate and remove it.\n\nRegards,\nJamie"),
    ("Subject: Need assistance with onboarding setup\n\n"
     "Hi,\n\n"
     "We signed up yesterday and need guidance on setting up our first cloud assessment. "
     "Can someone call me?\n\nThanks,\nPat"),
    ("Subject: Urgent: Suspicious login from foreign IP\n\n"
     "To whom it may concern,\n\n"
     "I just received an alert about a login from Russia. I did not do that. "
     "Please block the account and let me know.\n\nSincerely,\nAlex"),
]

def attempt_lm_call(predictor, email, max_retries=3):
    """Call predictor with exponential backoff on rate limits; exit on connection errors."""
    delay = 1
    for attempt in range(max_retries):
        try:
            return predictor(email_text=email)
        except Exception as e:
            error_msg = str(e).lower()
            if "connection" in error_msg or "connect" in error_msg:
                print(f"Cannot reach LiteLLM endpoint. Check that your proxy is running.")
                sys.exit(1)
            if "rate limit" in error_msg or "429" in error_msg:
                if attempt < max_retries - 1:
                    time.sleep(delay)
                    delay *= 2
                    continue
                else:
                    print("Rate limit repeated after retries. Exiting.")
                    raise
            raise

def run_stage1():
    """Stage 1: Basic Predict on three sample emails."""
    print("\n=== Stage 1: Basic Predict ===")
    predictor = dspy.Predict(TicketRouter)
    for i, email in enumerate(sample_emails, 1):
        result = attempt_lm_call(predictor, email)
        print(f"Email {i}:")
        print(f"  category: {result.category}")
        print(f"  priority: {result.priority}")
        print(f"  requires_human: {result.requires_human}")

def run_stage2():
    """Stage 2: ChainOfThought on the same three sample emails."""
    print("\n=== Stage 2: ChainOfThought ===")
    cot = dspy.ChainOfThought(TicketRouter)
    for i, email in enumerate(sample_emails, 1):
        result = attempt_lm_call(cot, email)
        print(f"Email {i}:")
        print(f"  category: {result.category}")
        print(f"  priority: {result.priority}")
        print(f"  requires_human: {result.requires_human}")

def run_stage3():
    """Stage 3: BootstrapFewShot optimization and comparison."""
    print("\n=== Stage 3: BootstrapFewShot Optimization ===")

    trainset = [
        dspy.Example(
            email_text="Subject: Invoice #4567 double charge\n\nI see two charges for February. Please correct.",
            category="Billing", priority="High", requires_human=True
        ).with_inputs("email_text"),
        dspy.Example(
            email_text="Subject: Request for account deletion\n\nI want to delete my account due to inactivity.",
            category="Billing", priority="Low", requires_human=False
        ).with_inputs("email_text"),
        dspy.Example(
            email_text="Subject: Technical issue - Data upload failing\n\nHi, when I try to upload our security logs, the tool crashes with error 500. Please fix.",
            category="Technical", priority="High", requires_human=True
        ).with_inputs("email_text"),
        dspy.Example(
            email_text="Subject: Need clarification on compliance report\n\nHello, could you explain the compliance score in last month's report?",
            category="Technical", priority="Medium", requires_human=False
        ).with_inputs("email_text"),
        dspy.Example(
            email_text="Subject: Setup assistance for new team member\n\nWe added a new user but they cannot see the dashboard. Can you help?",
            category="Onboarding", priority="Medium", requires_human=True
        ).with_inputs("email_text"),
        dspy.Example(
            email_text="Subject: Payment method update\n\nI need to update my credit card on file.",
            category="Billing", priority="Low", requires_human=False
        ).with_inputs("email_text"),
        dspy.Example(
            email_text="Subject: Urgent security breach\n\nOur admin account was compromised. Please lock it immediately.",
            category="Security", priority="High", requires_human=True
        ).with_inputs("email_text"),
        dspy.Example(
            email_text="Subject: General question about service plans\n\nInterested in upgrading to enterprise. Can someone explain pricing?",
            category="Billing", priority="Low", requires_human=False
        ).with_inputs("email_text"),
        dspy.Example(
            email_text="Subject: Integration help - API authentication\n\nWe are trying to integrate your API using OAuth2 but keep getting 401 errors. Need help.",
            category="Technical", priority="Medium", requires_human=True
        ).with_inputs("email_text"),
        dspy.Example(
            email_text="Subject: Onboarding documentation request\n\nWhere can I find the getting started guide? The link in the email does not work.",
            category="Onboarding", priority="Low", requires_human=False
        ).with_inputs("email_text"),
    ]

    def ticket_accuracy(example, pred, trace=None):
        """Return 1.0 if all three outputs match the labels, else 0.0."""
        cat_ok = example.category == pred.category
        pri_ok = example.priority == pred.priority
        human_ok = example.requires_human == pred.requires_human
        return 1.0 if (cat_ok and pri_ok and human_ok) else 0.0

    optimizer = dspy.BootstrapFewShot(metric=ticket_accuracy, max_bootstrapped_demos=3)
    student = dspy.Predict(TicketRouter)
    print("Compiling BootstrapFewShot... this may take a moment.")
    try:
        compiled_program = optimizer.compile(student=student, trainset=trainset)
    except Exception as e:
        print(f"Compilation failed: {e}")
        sys.exit(1)

    test_email = (
        "Subject: Critical: login repeated failures\n\n"
        "We observed multiple failed login attempts from several IPs. "
        "Please investigate and advise."
    )

    baseline = dspy.Predict(TicketRouter)
    print("Running baseline and optimized comparison...")
    base_result = attempt_lm_call(baseline, test_email)
    opt_result = attempt_lm_call(compiled_program, test_email)

    print(f"\nTest email: {test_email}")
    print(f"\nBaseline (Predict)      -> category: {base_result.category}, priority: {base_result.priority}, requires_human: {base_result.requires_human}")
    print(f"Optimized (BSFewShot)   -> category: {opt_result.category}, priority: {opt_result.priority}, requires_human: {opt_result.requires_human}")

if __name__ == "__main__":
    validate_env()
    configure_dspy()
    try:
        run_stage1()
        run_stage2()
        run_stage3()
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)