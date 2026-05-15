# Marketing Content Assistant

## What This Agent Does

This project demonstrates a small multi-role marketing content pipeline:

1. A campaign planner creates a short campaign brief.
2. A researcher adds audience and positioning context.
3. A writer drafts an email, a short blog post, and social ad options.
4. A brand editor scores each draft against the configured tone and forbidden words.

The model does the creative work, but the Python script controls the workflow, retries,
environment validation, and printed output.

## Prerequisites

- Python 3.11 or later
- A running LiteLLM-compatible endpoint
- A populated `.env` file

## Setup

1. Copy `.env.template` to `.env`.
2. Fill in the LiteLLM URL, model, API key, product details, audience, and brand rules.
3. Run the agent:

```bash
python agent.py
```

No package install is required. The agent uses only the Python standard library.

## How to Switch AI Providers

Edit `MODEL_NAME` in `.env`. Because the agent calls a LiteLLM-compatible endpoint,
the code does not need to change when you switch between supported providers.

## Configuration

- `LITELLM_BASE_URL`: LiteLLM-compatible endpoint, usually `http://localhost:4000`
- `MODEL_NAME`: model name configured in LiteLLM
- `LITELLM_API_KEY`: API key for the endpoint
- `PRODUCT_NAME`: product being marketed
- `PRODUCT_DESCRIPTION`: short product description
- `TARGET_AUDIENCE`: intended customer
- `FORBIDDEN_WORDS`: comma-separated words the editor should reject
- `BRAND_TONE`: tone the editor should enforce
- `MAX_EDITOR_RETRIES`: number of writer/editor attempts per content type

## What NosisTech Changed from the Original

This is an independent educational rebuild inspired by the architecture of the referenced framework or source project. It is not affiliated with, endorsed by, or presented as a replacement for the original project.

- Reduced the project to the core planner/researcher/writer/editor architecture.
- Removed LangChain, provider-specific clients, the OpenAI SDK, dotenv, and retry scaffolding.
- Replaced package dependencies with a standard-library HTTP call.
- Kept brand constraints and product details in `.env`.
- Kept the editor retry loop, but made it small enough to inspect in one file.

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.
