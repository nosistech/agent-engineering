# LLM Guard

Framework post for Protect AI LLM Guard in the NosisTech Agent Engineering Series.

## What this agent does

This agent demonstrates a small LLM safety gateway pattern. It scans user input before the model sees it, redacts sensitive data, blocks unsafe input, sends safe prompts through LiteLLM, and scans model output before showing it to the user.

The full LLM Guard framework contains many production scanners and model-based checks. This rebuild keeps only the smallest version needed to teach the architecture.

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

The agent has five steps:

1. Scan the incoming prompt for blocked phrases.
2. Redact emails and simple API-key patterns.
3. Send only the sanitized prompt to the model.
4. Scan the model output for restricted names and unsafe claims.
5. Return `SAFE`, `BLOCKED_INPUT`, or `BLOCKED_OUTPUT`.

The important pattern is:

```text
user prompt
input scanner
redaction
model call
output scanner
final verdict
```

## Demo cases

The script runs four fictional examples:

- `Safe request`: a normal support summary.
- `Sensitive data redaction`: an email and test API key are redacted before the model call.
- `Prompt injection block`: an instruction override attempt is blocked before the model call.
- `Output policy block`: a model response containing a restricted fictional name is blocked after the model call.

## Verification

This build was tested through LiteLLM with `deepseek-v4-pro` and `gemini-flash`.

Both providers returned `SAFE` for the safe request and sensitive data redaction cases. Both providers returned `BLOCKED_INPUT` for the prompt injection case and `BLOCKED_OUTPUT` for the restricted output case.

The exact model wording differed slightly by provider. Gemini said "The fictional help desk resolved 14 tickets today." DeepSeek returned the same meaning. The important result is that both providers preserved the gateway behavior: safe input passed, sensitive data was redacted, prompt injection was blocked before the model call, and restricted output was blocked after the model call.

## License

MIT License, Copyright 2025 Protect AI.

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.
