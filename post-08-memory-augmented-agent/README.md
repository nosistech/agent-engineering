# Memory-Augmented Agent

## What This Agent Does

This project shows the smallest useful version of memory augmentation:

1. The user says something.
2. The agent stores the interaction in `memory.json`.
3. On the next request, the agent searches past interactions.
4. The most relevant memory is injected into the prompt.
5. The model responds with that prior context available.

The lesson is memory, not planning, scoring, or escalation. Those patterns are demonstrated in other posts.

## Prerequisites

- Python 3.11 or later
- A running LiteLLM endpoint

## Setup

1. Copy `.env.template` to `.env`.
2. Fill in your LiteLLM base URL, model name, and API key.
3. Run the built-in two-turn memory demo:

```bash
python agent.py
```

You can also send one request at a time:

```bash
python agent.py "Remember that Apex Dynamics prefers Friday status updates."
python agent.py "How should I schedule Apex Dynamics updates?"
```

No package install is required. The agent uses only the Python standard library.

## How to Switch AI Providers

Edit `MODEL_NAME` in `.env`. Because the agent calls LiteLLM, the code does not need to change when you switch between supported providers.

## What NosisTech Changed from the Original

- Reduced the project to the core memory-augmented pattern.
- Removed the planning agent.
- Removed priority scoring and escalation logic.
- Removed logging, retry layers, and atomic file writes.
- Removed third-party Python dependencies.
- Kept LiteLLM-compatible configuration through its OpenAI-compatible HTTP endpoint.

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.
