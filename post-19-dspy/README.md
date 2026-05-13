# DSPy Support Ticket Router

## What This Agent Does

This project demonstrates the smallest useful DSPy pattern:

1. Define a `Signature` for the task.
2. Configure DSPy to use a LiteLLM-compatible endpoint.
3. Run the same support tickets through `Predict` and `ChainOfThought`.
4. Compare the category, priority, and escalation decision.

The agent classifies NosisTech support emails as `Billing`, `Technical`,
`Onboarding`, or `Security`, assigns a priority, and decides whether a human
should review the ticket.

## Prerequisites

- Python 3.11 or later
- A running LiteLLM-compatible endpoint
- DSPy installed from `requirements.txt`

## Setup

1. Copy `.env.template` to `.env`.
2. Fill in the LiteLLM URL, model name, and API key.
3. Install requirements:

```bash
pip install -r requirements.txt
```

4. Run the agent:

```bash
python agent.py
```

## How To Switch AI Providers

Edit `MODEL_NAME` in `.env`. Because DSPy is configured through the local
LiteLLM-compatible endpoint, the routing can change without changing the agent code.

## What NosisTech Changed from the Original

- Reduced the demo to one signature and two DSPy modules.
- Removed the long BootstrapFewShot training set and optimizer stage.
- Removed `python-dotenv`; the script now loads `.env` directly.
- Kept DSPy as the core dependency because the point is the DSPy programming model.

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.
