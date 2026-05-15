# Langflow RFP Analyzer

## What This Folder Shows

This example pairs an exported Langflow workflow with a small Python API client.
The flow analyzes RFP text for requirements, deadlines, compliance concerns, and
budget signals. The Python script demonstrates how to call a Langflow flow from
code after designing it visually.

## Prerequisites

- Python 3.11 or newer
- Langflow Desktop or Langflow server running locally
- A Langflow API key and flow ID

## Setup

1. Copy `.env.template` to `.env`.
2. Fill in your Langflow API key, flow ID, and base URL.
3. Run the client:

```bash
python api_client.py
```

- `LANGFLOW_API_KEY`: your Langflow API key
- `LANGFLOW_FLOW_ID`: the flow ID to run
- `LANGFLOW_BASE_URL`: Langflow base URL, default `http://localhost:7860`
- `LANGFLOW_MODEL_NAME`: model override for the exported OpenAI component
- `LANGFLOW_OPENAI_API_BASE`: OpenAI-compatible base URL override, usually `http://localhost:4000`

No package install is required. The client uses only the Python standard library.

## What NosisTech Changed from the Original

This is an independent educational rebuild inspired by the architecture of the referenced framework or source project. It is not affiliated with, endorsed by, or presented as a replacement for the original project.

- Kept the exported `rfp_analyzer_flow.json` as the visual workflow artifact.
- Reduced the Python side to a small dependency-free REST client.
- Removed `requests`, `python-dotenv`, and extra error scaffolding.
- Kept all credentials and endpoint settings in `.env`.
- Added runtime tweaks so the exported flow can use the local LiteLLM-compatible endpoint.
- Kept the built-in sample RFP so the client has a repeatable test input.
