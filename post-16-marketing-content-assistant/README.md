# Marketing Content Assistant

## What this agent does

This agent automates a multi-role marketing content pipeline for NosisTech LLC. It takes a product name, description, and target audience, then runs them through an assembly line of AI specialists: a Campaign Planner produces a structured brief, a Researcher gathers background context, and a Writer drafts three distinct pieces of marketing content -- an email, a blog post, and ad copy. An Editor enforces brand compliance by checking every draft against a list of forbidden words and a required tone descriptor. If a draft fails, the Editor explains why and the Writer attempts a new version until the draft passes or the retry cap is reached.

The system is built entirely in Python using only the LiteLLM library and the OpenAI-compatible proxy interface. It works with any major model provider (OpenAI, Anthropic, DeepSeek, Gemini, or locally hosted models via Ollama) by changing the MODEL_NAME environment variable. No code changes required.

## Prerequisites

- Python 3.10 or later (tested with 3.14)
- A running LiteLLM proxy (e.g., http://localhost:4000 via SSH tunnel)
- An API key for that proxy
- A .env file populated from .env.template

## Setup

1. Clone the repository and navigate to the project folder.
2. Install dependencies:
   pip install -r requirements.txt
3. Copy .env.template to .env and fill in all values.
4. Ensure your LiteLLM proxy is reachable.
5. Run the pipeline:
   python agent.py

## How to switch AI providers

Update MODEL_NAME in your .env file to any model identifier supported by your LiteLLM proxy. No other change is needed. The same code runs against OpenAI, Anthropic, Google, DeepSeek, open-source models, and any future LiteLLM-supported provider.

## What NosisTech changed from the original

The original implementation relied on LangChain, provider-specific client libraries, and hardcoded model names. NosisTech removed all LangChain and LangGraph dependencies, replaced provider SDKs with a single LiteLLM integration, and moved every configurable value to environment variables. Added: automatic input validation, graceful failure when the proxy is unreachable, exponential backoff on rate limits, a JSON-based brand compliance editor with a retry loop, and brand constraints loaded entirely from .env. The pipeline is stateless and portable across any LiteLLM-compatible backend.

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.