# Async Standup Summarizer

## What this agent does

The Async Standup Summarizer collects individual standup updates from team
members via a structured JSON file, then uses a large language model to
generate a concise three-line summary for each contributor. It then
synthesizes all individual summaries into a single consolidated team report
grouped by Completed This Period, In Progress, and Active Blockers.

This tool is built for distributed or asynchronous teams who want standup
discipline without requiring everyone online at the same time. It works with
any LLM provider reachable through a LiteLLM proxy. Changing the model
requires editing one line in the .env file and nothing else.

## Prerequisites

- Python 3.10 or newer (tested with Python 3.14.2)
- pip
- A running LiteLLM proxy server with your chosen model configured
- A standup_updates.json input file in the required format

## Setup

Copy the environment template and fill in your values:

```bash
cp .env.template .env
```

Edit `.env`:

- `LITELLM_BASE_URL`: URL of your LiteLLM proxy, for example `http://localhost:4000`
- `MODEL_NAME`: model identifier your LiteLLM instance expects
- `LITELLM_API_KEY`: API key your LiteLLM proxy requires
- `INPUT_FILE`: path to your JSON input file, default `standup_updates.json`
- `OUTPUT_DIR`: folder where reports are saved, default `reports`

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the agent:

```bash
python agent.py
```

## How to switch AI providers

Edit `MODEL_NAME` in your `.env` file. No other change is needed. The agent
routes all calls through LiteLLM, so any provider your proxy supports works the
same way.

## What NosisTech changed from the original

- Replaced framework-heavy orchestration with a small Python pipeline.
- Uses the OpenAI SDK pointed at a LiteLLM proxy instead of importing the LiteLLM Python package.
- Loads standup updates from a simple JSON file.
- Validates required environment variables before making any model calls.
- Skips malformed contributor entries while keeping valid updates moving.
- Adds simple rate-limit backoff around model calls.
- Saves each final team report to a timestamped file in the reports folder.

## What this agent does not handle

- Live integrations with Slack, Teams, or another chat platform
- Scheduled or automated execution
- Reading from shared workspaces or databases
- Real-time notifications or follow-up actions
- Multi-file input

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.
