# Conflict Resolution Agent — NosisTech LLC (Post 21, Block 4)

## What this agent does

A multi-agent system that processes business requests (insurance claims) by
routing each claim through two independent reviewer agents with different
perspectives. A conflict detector compares their confidence scores. If they
agree within a configurable threshold and confidence is high enough, the
decision is made automatically. If they disagree, the agent halts and asks a
human to type APPROVE or REJECT before proceeding. Every decision is written
to a decisions.jsonl audit log.

## Prerequisites

- Python 3.11 or higher
- A LiteLLM proxy running and accessible
- A .env file with all required variables filled in

## Setup

1. Copy the four files into your project folder.
2. Install dependencies:

   pip install -r requirements.txt

3. Copy .env.template to .env and fill in your values:

   LITELLM_BASE_URL=http://localhost:4000
   MODEL_NAME=your-model-name
   LITELLM_API_KEY=your-api-key

4. Run the agent:

   python agent.py

## How to switch providers

Change MODEL_NAME in your .env file to any model your LiteLLM proxy supports.
No code changes needed.

## What NosisTech changed from the original

- Removed the custom LiveLLM wrapper and all provider-specific SDK imports.
- Replaced hardcoded model strings and thresholds with environment variables.
- Added startup validation, claim field validation, safe JSON parsing,
  rate-limit retry logic, and a JSONL audit log.
- Removed the bare raise in the retry helper to prevent raw exceptions
  surfacing to the user.
- All sample data uses NosisTech LLC as the example organization.

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.