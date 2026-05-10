# Data Analysis Agent — NosisTech LLC

## What This Agent Does

The Data Analysis Agent takes a CSV dataset and a plain-English business
question, runs statistical analysis entirely in Python, and returns a
structured business insight interpreted by an AI model. The mathematics
run in code: anomaly detection uses Z-score analysis to flag unusual data
points, and trend analysis uses OLS regression to surface correlations with
a confidence rating. The AI model only interprets what the math already found.

This agent is part of the NosisTech AI Agent Engineering series. It is built
for reliability and safety: secrets never leave the environment file, inputs
are validated before any processing begins, and all errors produce plain-English
messages rather than raw stack traces.

## Prerequisites

- Python 3.11 or higher
- pip
- A running LiteLLM proxy instance
- A CSV file with numeric columns for analysis

## Setup

1. Clone the repository or copy the files into your working directory.
2. Create your .env file from the template:

   cp .env.template .env

3. Edit .env and fill in your values for LITELLM_BASE_URL, MODEL_NAME,
   LITELLM_API_KEY, and DATA_FILE_PATH.
4. Install dependencies:

   pip install -r requirements.txt

5. Run the agent:

   python agent.py

The agent will print the columns found in your dataset, then prompt you for
a business question, the column to scan for anomalies, and the two columns
for regression analysis.

## How to Switch AI Providers

Change MODEL_NAME in your .env file to any LiteLLM-supported model identifier.
No other changes are required. The agent routes all calls through the LiteLLM
proxy, which handles provider translation automatically.

## What NosisTech Changed from the Original

- Removed all hardcoded credentials, model names, and file paths.
  Everything is environment-driven via .env.
- Replaced the Jupyter notebook structure with a clean single-file Python script.
- Stripped all provider-specific SDKs and replaced with the openai SDK
  pointed at the LiteLLM proxy.
- Removed mock_llm.py, color_logger.py, and all offline scaffolding.
- Removed transformers and torch dependencies, which belong to the
  Verification Agent, not this agent.
- Added startup environment variable validation, graceful connection failure
  handling, and exponential backoff on rate limit errors.
- Added a pre-LLM statistical summary so the operator sees the raw math
  output independent of AI interpretation.
- Made the anomaly Z-score threshold configurable via ANOMALY_Z_THRESHOLD
  in .env so operators can tune sensitivity without touching code.

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.