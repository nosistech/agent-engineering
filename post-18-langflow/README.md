# Langflow RFP Analyzer

## What this folder shows

This example pairs an exported Langflow workflow with a small Python API client.
The flow analyzes RFP text for requirements, deadlines, compliance concerns, and
budget signals. The Python script demonstrates how to call a Langflow flow from
code after designing it visually.

## Prerequisites

- Python 3.11 or newer
- pip
- Langflow Desktop or Langflow server running locally
- A Langflow API key and flow ID

## Setup

```bash
cp .env.template .env
pip install -r requirements.txt
```

Edit `.env`:

- `LANGFLOW_API_KEY`: your Langflow API key
- `LANGFLOW_FLOW_ID`: the flow ID to run
- `LANGFLOW_BASE_URL`: Langflow base URL, default `http://localhost:7860`

## Run

```bash
python api_client.py
```

The script sends a built-in sample RFP to the configured Langflow flow and
prints the returned analysis.
