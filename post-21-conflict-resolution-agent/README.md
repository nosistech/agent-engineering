# Conflict Resolution Agent

## What this agent does

This project demonstrates a small multi-agent human-checkpoint pattern:

1. Two independent reviewer agents evaluate the same claim.
2. Their recommendations and confidence scores are compared.
3. Aligned, high-confidence reviews can be auto-decided.
4. Conflicts or low-confidence reviews become `HUMAN_REVIEW_REQUIRED`.
5. Every decision is appended to a JSONL audit log.

The core lesson is not claims processing. The lesson is how independent agent reviews create a checkpoint before a risky decision moves forward.

## Prerequisites

- Python 3.11 or later
- A running LiteLLM endpoint

## Setup

1. Copy `.env.template` to `.env`.
2. Fill in your LiteLLM base URL, model name, API key, thresholds, and optional audit log path.
3. Run the agent:

```bash
python agent.py
```

No package install is required. The agent uses only the Python standard library.

## Human review

By default, escalated claims are marked `HUMAN_REVIEW_REQUIRED` so the demo never blocks waiting for terminal input. To simulate a human override, set:

```bash
HUMAN_REVIEW_DECISION=APPROVE
```

or:

```bash
HUMAN_REVIEW_DECISION=REJECT
```

## How to switch providers

Edit `MODEL_NAME` in `.env`. Because the agent calls LiteLLM, the code does not need to change when you switch between supported providers.

## What NosisTech changed from the original

This is an independent educational rebuild inspired by the architecture of the referenced framework or source project. It is not affiliated with, endorsed by, or presented as a replacement for the original project.

- Reduced duplicate reviewer functions to one parameterized reviewer.
- Removed OpenAI SDK, dotenv, retry scaffolding, and interactive terminal blocking.
- Kept the independent reviews, conflict check, human checkpoint, and audit log.
- Kept LiteLLM-compatible configuration through its OpenAI-compatible HTTP endpoint.

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.
