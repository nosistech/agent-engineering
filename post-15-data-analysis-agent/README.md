# Data Analysis Agent

## What This Agent Does

This project demonstrates a small data-analysis agent pattern:

1. Python loads a CSV file.
2. Python computes anomaly detection and a simple regression.
3. The model explains those computed findings in business language.

The model does not do the math. It only interprets the numbers that code already calculated.

## Prerequisites

- Python 3.11 or later
- A running LiteLLM endpoint
- A CSV file with numeric columns

## Setup

1. Copy `.env.template` to `.env`.
2. Fill in your LiteLLM base URL, model name, API key, CSV path, and optional analysis columns.
3. Run the agent:

```bash
python agent.py
```

No package install is required. The agent uses only the Python standard library.

## How to Switch AI Providers

Edit `MODEL_NAME` in `.env`. Because the agent calls LiteLLM, the code does not need to change when you switch between supported providers.

## What NosisTech Changed from the Original

- Reduced the project to the core code-computes/model-explains architecture.
- Removed pandas, numpy, OpenAI SDK, dotenv, and retry scaffolding.
- Removed interactive prompts so the demo runs every time.
- Removed p-value approximation and chart recommendation logic.
- Kept anomaly detection and regression as the two computed findings.

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.
