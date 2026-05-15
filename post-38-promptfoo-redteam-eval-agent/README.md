# Promptfoo Redteam Eval Agent

## What This Agent Does

This agent is a small evaluation harness inspired by Promptfoo. It sends three fictional prompts into an AI model through a LiteLLM proxy, captures the model responses, and grades those responses with visible Python assertions.

This is an educational demonstration, not a production security system. The assertions are simple checks that show how evaluation pipelines work, and they should not be treated as complete protection for real applications.

## Prerequisites

- Python 3.14.2
- pip
- A running LiteLLM proxy with at least one configured model

## Setup

```powershell
git clone https://github.com/nosistech/agent-engineering.git
cd agent-engineering/post-38-promptfoo-redteam-eval-agent
Copy-Item .env.template .env
# Edit .env and fill in LITELLM_BASE_URL, MODEL_NAME, and LITELLM_API_KEY
pip install -r requirements.txt
python agent.py
```

## How to Switch AI Providers

Change `MODEL_NAME` in your `.env` file to any model configured in your LiteLLM proxy. No code changes are required.

## What NosisTech Changed from the Original

Promptfoo is a large TypeScript testing platform with a CLI, YAML configuration, provider integrations, red-team plugins, reports, tracing, and dashboard workflows.

NosisTech rebuilt only the core evaluation loop as a small Python agent: define test cases, call a model, run deterministic assertions, and print a compact report. This version removes the Promptfoo CLI, YAML parsing, plugin system, web dashboard, telemetry, tracing, LangChain examples, LangGraph examples, and provider-specific setup. LiteLLM handles provider routing through environment variables.

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.
