# Marketing Content Assistant

## What this agent does

This agent automates a multi-role marketing content pipeline. It takes a product name, description, and target audience, then runs them through an assembly line of AI specialists: a Campaign Planner produces a structured brief, a Researcher gathers background context, and a Writer drafts three pieces of marketing content: an email, a blog post, and ad copy. An Editor enforces brand compliance by checking every draft against a configurable list of forbidden words and a required tone descriptor. If a draft fails, the Editor explains why and the Writer attempts a new version until the draft passes or the retry cap is reached.

The system is built in Python using the OpenAI-compatible SDK interface. It works with any major model provider by changing the base URL and model name in the settings file. No code changes required.

## Prerequisites

- Python 3.10 or later (tested with 3.14)
- Access to an OpenAI-compatible endpoint (LiteLLM proxy or direct provider URL)
- An API key for that endpoint
- A .env file populated from .env.template

## Setup

1. Clone the repository and navigate to the project folder.
2. Install dependencies:
   pip install -r requirements.txt
3. Copy .env.template to .env and fill in all values.
4. Run the pipeline:
   python agent.py

## How to switch AI providers

Update LITELLM_BASE_URL, MODEL_NAME, and LITELLM_API_KEY in your .env file. No other change is needed. The agent works with any OpenAI-compatible endpoint.

## Routing modes

This agent supports two routing configurations:

Mode 1 (proxy): Set LITELLM_BASE_URL to your LiteLLM proxy address. The proxy handles provider routing. MODEL_NAME must match a model_name entry in your proxy config.

Mode 2 (direct): Set LITELLM_BASE_URL to the provider's API base URL directly. Set LITELLM_API_KEY to the provider's API key. MODEL_NAME must match the provider's model identifier.

Mode 2 was used during testing when the proxy returned infrastructure errors. Both modes produce identical output from the agent's perspective.

## Known limitations

The Editor call uses max_tokens=200. On some providers and for longer drafts, this can cause the JSON response to be truncated, resulting in a parse error. If ad copy drafts consistently fail with parse errors, increase max_tokens on the editor call to 400.

## What NosisTech changed from the original

The original implementation relied on LangChain, provider-specific client libraries, and hardcoded model names. NosisTech removed all LangChain dependencies, replaced provider SDKs with the OpenAI-compatible SDK interface, and moved every configurable value to environment variables. Added: automatic input validation, graceful failure handling, exponential backoff on rate limits, a JSON-based brand compliance editor with a retry loop, and brand constraints loaded entirely from .env. Two routing modes are documented to reflect what actually worked during testing.

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.