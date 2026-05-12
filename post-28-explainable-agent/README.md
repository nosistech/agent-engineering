# Explainable Agent

## What this agent does

This example combines a small synthetic classifier with explanation patterns
often used around high-stakes AI systems:

- feature-level attributions inspired by SHAP
- local perturbation weights inspired by LIME
- a simple counterfactual search
- confidence-aware routing guidance
- audience-specific summaries for analysts and applicants

The model is synthetic and educational. It is not a lending system and should
not be used for financial decisions.

## Prerequisites

- Python 3.11 or newer
- pip
- A LiteLLM-compatible endpoint for the generated explanations

## Setup

```bash
cp .env.template .env
pip install -r requirements.txt
```

Edit `.env` with your model, LiteLLM base URL, and API key.

## Run

```bash
python agent.py
```

The script evaluates a built-in demo application and prints analyst-facing,
applicant-facing, and reasoning-trace outputs.
