# Memory-Augmented Agent

## What This Agent Does

This agent demonstrates an autonomous business assistant that remembers past interactions, plans and executes multi-step workflows, and makes risk-aware decisions about when to handle a request itself, guide the user, or escalate to a human manager. It is designed for NosisTech LLC, a boutique AI governance and cloud security consultancy, to show how an enterprise AI system can retain client context, manage project workflows, and safely handle day-to-day operations without requiring constant human intervention.

The agent uses a file-based memory to recall previous conversations, a planning module that breaks a high-level goal into ordered subtasks, and a decision engine that scores incoming requests based on priority, complexity, and familiarity. Depending on the score, the agent responds autonomously, provides step-by-step guidance, or logs an escalation for a human manager while still delivering a helpful message to the user.

## Prerequisites

- Python 3.14 or higher
- pip (Python package manager)
- A running LiteLLM proxy (https://docs.litellm.ai/docs/proxy/quick_start) with access to an LLM provider of your choice (OpenAI, Anthropic, DeepSeek, etc.)

## Setup

1. Clone this folder to your machine.
2. Copy `.env.template` to `.env` and edit the values:
   - `LITELLM_BASE_URL`: the URL of your LiteLLM proxy (default http://localhost:4000)
   - `MODEL_NAME`: any model available through your proxy (e.g., gpt-4o, claude-3-opus)
   - `LITELLM_API_KEY`: the API key configured in your proxy
   - `MEMORY_FILE_PATH`: (optional) path to the memory JSON file, defaults to memory.json
   - `PRIORITY_KEYWORDS`: (optional) comma-separated words that signal urgency, defaults to urgent,critical,emergency
3. Install dependencies: `pip install -r requirements.txt`
4. Run the agent: `python agent.py`

The agent will execute a built-in demonstration showing planning and two decision scenarios.

## How to Switch AI Providers

To change the language model, update `MODEL_NAME` in your `.env` file. No code changes are required. Replace `gpt-4o` with `claude-3-opus-20240229` and restart the agent. The LiteLLM proxy routes the request to the correct provider automatically.

## What NosisTech Changed from the Original

- Replaced direct provider SDKs with the OpenAI SDK pointed at a LiteLLM proxy for universal provider support.
- Moved model selection and API key into environment variables so no provider details are hardcoded.
- Swapped the in-memory dictionary for a persistent, atomic-write file-based memory store.
- Removed Jupyter notebook format, IPython display, SVG rendering, LangChain, LangGraph, and hardcoded sample data. All examples reference NosisTech LLC.
- Added environment variable validation on startup, rate-limit handling with exponential backoff, input validation, retrieval logging, and configurable priority keywords via environment variable.
- Converted all output to Python's standard logging module. No bare print statements except the startup model announcement and the missing variable list.
- Replaced proprietary mock and color logger modules with standard library tools.

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.
