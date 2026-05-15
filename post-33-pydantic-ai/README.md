## What This Agent Does

The Pydantic-AI Governance Decision Agent reviews fictional enterprise AI use cases and returns a structured governance decision: APPROVE, REVIEW, or REJECT. It demonstrates the core architectural pattern behind Pydantic-AI: pass controlled context into the model, define a strict output schema, validate the response with Pydantic, and retry when the model returns malformed output.

The agent evaluates three fictional risk tiers: an internal meeting summarizer, a customer support history tool, and an automated eligibility recommender. Each result includes a risk score, policy flags, a human review flag, and a plain-English reason that can be inspected before any next step.

## Prerequisites

- Python 3.14.2
- pip
- A running LiteLLM proxy reachable through the URL in your `.env` file

## Setup

1. Clone the repository or open this folder locally.
2. Copy `.env.template` to `.env`.
3. Fill in `LITELLM_BASE_URL`, `MODEL_NAME`, and `LITELLM_API_KEY`.
4. Install dependencies with `pip install -r requirements.txt`.
5. Run the agent with `python agent.py`.

## How to Switch AI Providers

Change `MODEL_NAME` in `.env` to any model supported by your LiteLLM proxy. No code changes are required.

## What NosisTech Changed from the Original

This is an independent educational rebuild inspired by the architecture of the referenced framework or source project. It is not affiliated with, endorsed by, or presented as a replacement for the original project.

The original Pydantic-AI framework provides an agent runtime, typed dependency injection, structured outputs, tool decorators, validation retries, provider adapters, durable execution, graphs, evals, and integrations. This rebuild keeps only the architecture lesson needed for the post. It replaces the framework runtime with direct Python functions, a LiteLLM-routed OpenAI-compatible client, Pydantic input and output models, and a small retry loop.

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.
