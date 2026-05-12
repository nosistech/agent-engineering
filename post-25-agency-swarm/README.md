# Agency Swarm Orchestration

## What this agent does

This example demonstrates an Agency Swarm workflow with three roles:

- `CEOAgent` coordinates the handoff.
- `ResearcherAgent` creates a three-point research brief.
- `WriterAgent` turns the brief into a 150-word summary.

The goal is to show the handoff pattern in a compact content pipeline.

## Prerequisites

- Python 3.11 or newer
- pip
- An OpenAI API key

## Setup

```bash
cp .env.template .env
pip install -r requirements.txt
```

Edit `.env`:

- `OPENAI_API_KEY`: your API key
- `MODEL`: model name used by Agency Swarm

## Run

```bash
python agent.py
```

The script runs a demo topic: `AI governance trends in 2025`.
