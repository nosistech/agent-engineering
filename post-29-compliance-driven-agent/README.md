# Compliance-Driven Software Engineering Agent

## 1. What this agent does

This single-file agent receives a plain-English software requirement and emulates a small AI-powered software delivery team. It creates an engineering plan, generates pytest-style tests, writes a minimal Python implementation, and then statically reviews the generated code for syntax and compliance issues.

The rebuild uses LiteLLM with provider settings loaded from environment variables. It does not use LangChain, LangGraph, or LlamaIndex. Compliance policy rules stay visible in `rules.yaml`.

## 2. Prerequisites

- Python 3.14.2
- pip for package installation
- Access to a LiteLLM-compatible model route
- Environment variables set through a local `.env` file

## 3. Setup

1. Copy `.env.template` to `.env`.
2. Fill in `LITELLM_BASE_URL`, `MODEL_NAME`, and `LITELLM_API_KEY` with your environment-specific values.
3. Install dependencies:
   pip install -r requirements.txt
4. Run the agent:
   python agent.py

The agent uses a safe demo requirement and prints its review summary to the console.

## 4. How to switch AI providers

Change `MODEL_NAME` in `.env` to another model route configured in your LiteLLM environment. If your route also needs a different base URL or key, update `LITELLM_BASE_URL` and `LITELLM_API_KEY` in `.env`. The Python code does not need to change.

## 5. What NosisTech changed from the original

This is an independent educational rebuild inspired by the architecture of the referenced framework or source project. It is not affiliated with, endorsed by, or presented as a replacement for the original project.

- Replaced LangGraph orchestration with a plain Python loop and ordinary functions.
- Replaced LangChain model wrappers with direct HTTP calls to the LiteLLM proxy.
- Removed hardcoded model identifiers, URLs, and policy strings from the code.
- Moved compliance rules to `rules.yaml` for transparent review.
- Added environment validation, input validation, rate-limit handling, and graceful failure messages.
- Kept generated code as console output only. The agent does not execute generated code or write it to disk.

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.
