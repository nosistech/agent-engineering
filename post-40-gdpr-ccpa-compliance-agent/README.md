# GDPR and CCPA Compliance Agent

Pattern #41 in the NosisTech Agent Engineering Series.

## What this agent does

This agent demonstrates a small privacy compliance screening pattern. It reviews a fictional data processing activity and asks the model to flag possible GDPR and CCPA concerns.

This is an educational demo only. It does not provide legal advice, certify compliance, or replace review by qualified privacy counsel.

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

1. Load LiteLLM settings from `.env`.
2. Send a fictional data processing activity to the model.
3. Apply a compact GDPR and CCPA screening checklist.
4. Extract the JSON object if a provider wraps it in extra formatting.
5. Print the returned JSON.

The important pattern is:

```text
data activity description
privacy screening checklist
GDPR flags
CCPA flags
human review questions
```

## Demo cases

The script runs three fictional examples:

- `Basic newsletter`: a lower-risk opt-in newsletter scenario.
- `Health analytics`: a higher-risk EU health data scenario.
- `Ad sharing`: a California shopper tracking and advertising-sharing scenario.

## Verification

This build was tested through LiteLLM with `deepseek-v4-pro` and `gemini-flash`.

Both providers identified the health analytics and ad sharing scenarios as `HIGH` risk. DeepSeek rated the basic newsletter case `LOW`, while Gemini rated it `MEDIUM` because it wanted more information about data subject rights, storage location, and CCPA applicability. That difference is acceptable for this educational screening demo because both providers separated the lower-risk newsletter scenario from the higher-risk health data and ad sharing scenarios.

## License

## What NosisTech Changed from the Original

This is an independent educational rebuild inspired by the architecture of the referenced framework or source project. It is not affiliated with, endorsed by, or presented as a replacement for the original project.

- Removed production infrastructure, provider-specific wiring, and framework-specific complexity not needed for this learning build.
- Replaced the original system with a small LiteLLM-compatible educational pattern that can be inspected locally.
- Kept only the architecture needed to demonstrate the specific agent pattern in this post.

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.
