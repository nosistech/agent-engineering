# AutoGen Examples

## What this folder shows

This folder contains three small AutoGen patterns:

- `agent_v1.py`: a single assistant produces a competitive analysis.
- `agent_v2.py`: a group chat coordinates researcher, critic, and synthesizer
  agents.
- `agent_v3.py`: a coder/executor loop writes and runs a small Python script.

The examples route model calls through a LiteLLM-compatible endpoint so the
provider can be changed from `.env`.

## Prerequisites

- Python 3.11 or newer
- pip
- A running LiteLLM proxy

## Setup

```bash
cp .env.template .env
pip install -r requirements.txt
```

Edit `.env` with your LiteLLM base URL, API key, and model name.

## Run

```bash
python agent_v1.py
python agent_v2.py
python agent_v3.py
```

`agent_v3.py` creates a local `coding/` workspace for AutoGen code execution.
