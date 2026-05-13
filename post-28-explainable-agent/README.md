# Explainable Agent

## What this agent does

This project shows a small explainable-agent pattern:

1. A synthetic scoring model evaluates an application.
2. The code prints feature attributions so the user can see what influenced the score.
3. The code prints one counterfactual improvement.
4. The model turns the same evidence into an analyst summary and an applicant summary.

The example is educational. It is not a lending system and must not be used for real financial decisions.

## Prerequisites

- Python 3.11 or newer
- A running LiteLLM endpoint

## Setup

1. Copy `.env.template` to `.env`.
2. Fill in your LiteLLM base URL, model name, and API key.
3. Run the demo:

```bash
python agent.py
```

No package install is required. The agent uses only the Python standard library.

## How to switch AI providers

Edit `MODEL_NAME` in `.env`. Because the agent calls LiteLLM, the code does not need to change when you switch between supported providers.

## What NosisTech changed from the original

- Reduced the project to one synthetic scoring model.
- Replaced custom SHAP/LIME-style classes with one simple attribution table.
- Kept one counterfactual improvement.
- Kept two audience-specific summaries.
- Standardized configuration on `MODEL_NAME` and `LITELLM_BASE_URL`.
- Removed third-party Python dependencies.

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.
