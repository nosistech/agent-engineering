# Phidata-Pattern Agent

## What this agent does

This project demonstrates a small version of the Phidata-style source routing pattern:

1. Check internal knowledge first.
2. If internal knowledge does not answer the question, call a web search tool.
3. Give the selected context to the model.
4. Print the answer and the source used.

The lesson is source routing. Memory and embedding search are intentionally left out because earlier posts already teach those patterns.

## Prerequisites

- Python 3.11 or later
- A running LiteLLM endpoint
- Internet access for the optional web fallback

## Setup

1. Copy `.env.template` to `.env`.
2. Fill in your LiteLLM base URL, model name, API key, and knowledge file path.
3. Run the built-in demo:

```bash
python agent.py
```

You can also ask one question:

```bash
python agent.py "What services does NosisTech offer?"
```

No package install is required. The agent uses only the Python standard library.

## How to switch AI providers

Edit `MODEL_NAME` in `.env`. Because the agent calls LiteLLM, the code does not need to change when you switch between supported providers.

## What NosisTech changed from the original

- Reduced the project to the core internal-first, web-fallback routing pattern.
- Removed SQLite memory because memory is covered in Posts 8 and 11.
- Removed embeddings and cosine similarity because retrieval is covered in Post 9.
- Removed third-party Python dependencies.
- Kept source transparency so each answer prints whether it used internal knowledge or web search.
- Kept LiteLLM-compatible configuration through its OpenAI-compatible HTTP endpoint.

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.
