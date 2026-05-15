# Chain-of-Agents Orchestrator

## What this agent does

This project demonstrates the smallest useful chain-of-agents pattern:

1. Three specialist agents each inspect the same target from a different angle.
2. Each specialist returns one focused finding.
3. A manager agent receives all findings.
4. The manager synthesizes one final report.
5. The run is appended to a JSONL journal for audit history.

The key architecture rule: the manager only uses findings from the current run. The journal is a permanent audit trail, not the manager's working memory.

## Prerequisites

- Python 3.11 or later
- A running LiteLLM endpoint

## Setup

1. Copy `.env.template` to `.env`.
2. Fill in your LiteLLM base URL, model name, API key, optional default target, and optional journal path.
3. Run the demo:

```bash
python agent.py "NosisTech LLC"
```

No package install is required. The agent uses only the Python standard library.

## How to switch AI providers

Edit `MODEL_NAME` in `.env`. Because the agent calls LiteLLM, the code does not need to change when you switch between supported providers.

## What NosisTech changed from the original

This is an independent educational rebuild inspired by the architecture of the referenced framework or source project. It is not affiliated with, endorsed by, or presented as a replacement for the original project.

- Reduced the project to the core specialist-to-manager handoff.
- Kept the JSONL journal as an audit trail.
- Separated current-run working notes from historical journal records.
- Removed LLM-based conflict scoring.
- Removed retry and dependency layers that distracted from the chain pattern.
- Removed third-party Python dependencies.
- Kept LiteLLM-compatible configuration through its OpenAI-compatible HTTP endpoint.

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.
