# Agency Swarm Orchestration

## What this agent does

This example demonstrates an Agency Swarm workflow with three roles:

- `CEOAgent` coordinates the handoff.
- `ResearcherAgent` creates a three-point research brief.
- `WriterAgent` turns the brief into a 150-word summary.

The goal is to show the handoff pattern in a compact content pipeline.

The current Agency Swarm API wires those handoffs with `communication_flows`:

```python
agency = Agency(
    ceo,
    communication_flows=[
        ceo > researcher,
        ceo > writer,
    ],
)
```

Agency Swarm may create a local `settings.json` file while running. That file is generated runtime state and is intentionally ignored by git.

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

## What NosisTech Changed from the Original

This is an independent educational rebuild inspired by the architecture of the referenced framework or source project. It is not affiliated with, endorsed by, or presented as a replacement for the original project.

- Removed production infrastructure, provider-specific wiring, and framework-specific complexity not needed for this learning build.
- Replaced the original system with a small LiteLLM-compatible educational pattern that can be inspected locally.
- Kept only the architecture needed to demonstrate the specific agent pattern in this post.
