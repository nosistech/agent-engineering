# Document Intelligence Agent

## What this agent does

This project demonstrates a small OCR confidence-routing pattern:

1. Read an invoice image with OCR.
2. Calculate the OCR confidence score.
3. If confidence is high enough, ask the model to extract invoice fields as JSON.
4. If confidence is too low, route the document to a human review queue.

The lesson is confidence-based routing. The agent does not try to repair weak OCR with another model call; low-quality input is sent to review instead.

## Prerequisites

- Python 3.11 or later
- Tesseract OCR installed separately
- A running LiteLLM endpoint
- Python packages from `requirements.txt`

## Setup

1. Copy `.env.template` to `.env`.
2. Fill in your LiteLLM base URL, model name, API key, threshold, and file paths.
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Run the agent:

```bash
python agent.py
```

## How to switch AI providers

Edit `MODEL_NAME` in `.env`. Because the agent calls LiteLLM, the code does not need to change when you switch between supported providers.

## What NosisTech changed from the original

This is an independent educational rebuild inspired by the architecture of the referenced framework or source project. It is not affiliated with, endorsed by, or presented as a replacement for the original project.

- Reduced the project to OCR, confidence routing, extraction, and review.
- Removed PDF support to keep the teaching version image-only.
- Removed the AI correction pass and second confidence threshold.
- Hardcoded the three demo invoice fields in code.
- Removed OpenAI SDK and dotenv dependencies.
- Kept LiteLLM-compatible configuration through its OpenAI-compatible HTTP endpoint.

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.
