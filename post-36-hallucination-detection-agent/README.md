# Hallucination Detection Agent

Pattern #70 in the NosisTech Agent Engineering Series.

## What this agent does

This agent demonstrates a small hallucination review pattern. It compares an AI response against the source context that was supposed to support that response.

The demo asks the model to break the response into factual claims, label each claim as `SUPPORTED`, `UNSUPPORTED`, or `CONTRADICTED`, and return a cautious score from `0.0` to `1.0`.

## Prerequisites

- Python 3.14.2 was used for this local test environment.
- A LiteLLM-compatible endpoint.
- A model available through that endpoint.

## Setup

Install dependencies:

```bash
pip install -r requirements.txt
```

Copy the environment template:

```bash
cp .env.template .env
```

Edit `.env` for your own LiteLLM-compatible endpoint:

```bash
LITELLM_BASE_URL=YOUR_LITELLM_BASE_URL
MODEL_NAME=YOUR_MODEL_NAME
LITELLM_API_KEY=YOUR_LITELLM_API_KEY
```

Run:

```bash
python agent.py
```

## How to switch AI providers

Change `MODEL_NAME` in `.env`. The Python code stays the same because the agent talks to a LiteLLM-compatible endpoint instead of a provider-specific SDK.

## Architecture

The agent has four steps:

1. Load LiteLLM settings from `.env`.
2. Send the built-in source context and AI response to the model.
3. Ask for JSON with claim-level labels and a hallucination score.
4. Extract the JSON object if a provider wraps it in extra formatting.
5. Print the returned JSON.

The important pattern is:

```text
source context
AI response
claim-level review
SUPPORTED, UNSUPPORTED, or CONTRADICTED labels
hallucination score
```

## Demo cases

The script runs three fictional examples:

- `Grounded`: the response is supported by the source.
- `Unsupported`: the response mixes source-backed facts with invented details.
- `Contradicted`: the response conflicts with the source.

## Verification

This build was tested through LiteLLM with `deepseek-v4-pro` and `gemini-flash`.

Both providers returned `GROUNDED` for the grounded case, `HIGH_RISK` for the unsupported case, and `HIGH_RISK` for the contradicted case. The exact claim wording differed slightly by provider, which is expected. The important result is that both providers identified grounded material, flagged unsupported material, and caught direct contradictions.

## License

## What NosisTech Changed from the Original

This is an independent educational rebuild inspired by the architecture of the referenced framework or source project. It is not affiliated with, endorsed by, or presented as a replacement for the original project.

- Removed production infrastructure, provider-specific wiring, and framework-specific complexity not needed for this learning build.
- Replaced the original system with a small LiteLLM-compatible educational pattern that can be inspected locally.
- Kept only the architecture needed to demonstrate the specific agent pattern in this post.

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.
