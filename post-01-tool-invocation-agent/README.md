# Tool Invocation Agent -- Data Visualization Assistant

## What this agent does

The Tool Invocation Agent is a plain-English data visualization assistant. Business users can ask questions like "Show me spend by campaign" or "What was the trend of clicks over time?" and the agent will automatically load a CSV file, aggregate the relevant metric, and generate a professional chart (bar or line) -- all without writing a single line of code.

The agent uses a lightweight, framework-free Python implementation. It leverages LiteLLM as a model proxy so you can switch between any LLM provider simply by changing one environment variable. No code changes required.

## Prerequisites

- Python 3.11 or later
- pip
- A running instance of LiteLLM on your VPS or local machine
- A CSV data file with the following columns: date, campaign_name, spend, clicks, conversions, impressions

## Setup

1. Clone this repository.
2. Copy .env.template to .env and fill in your LiteLLM base URL, model name, API key, path to your CSV file, and output directory.
3. Install dependencies: pip install -r requirements.txt
4. Run the agent: python agent.py

The program will run three demo queries and print a summary of results. Output charts are saved to your OUTPUT_DIR folder.

## How to switch AI providers

Edit the MODEL_NAME value in your .env file. The agent uses LiteLLM as a universal router so no other changes are required. Set MODEL_NAME to whatever model your LiteLLM instance is configured to serve. The code never changes. Only the .env changes.

## What NosisTech changed from the original

- Removed all hardcoded model names and replaced them with environment variables.
- Stripped deprecated provider-specific SDK calls and replaced with the OpenAI SDK pointed at a LiteLLM proxy.
- Replaced hardcoded file paths with DATA_FILE_PATH and OUTPUT_DIR environment variables.
- Eliminated the helper package and replaced its utilities with inline try/except blocks and clear print prefixes.
- Removed mock-LLM and simulation modes. All execution routes through the real LLM.
- Added startup environment validation to catch missing configuration before any API call.
- Enhanced the query parser with an LLM-based fallback for natural language queries the keyword parser cannot handle.
- Added rate-limit retry logic with exponential backoff, maximum three attempts.
- Added a run summary showing which queries succeeded and where output files were saved.

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.