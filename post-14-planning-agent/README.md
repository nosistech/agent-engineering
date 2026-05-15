# Planning Agent - NosisTech LLC

## What this agent does

The Planning Agent turns a high-level business goal into a dependency-ordered,
executable sequence of tasks. It uses a DAG (directed acyclic graph) and
topological sort so every task runs only after its prerequisites
are complete. This is the foundation of reliable project planning inside an
AI-powered system.

## Prerequisites

- Python 3.11 or higher
- A running LiteLLM proxy providing access to your chosen LLM
- Required Python packages listed in requirements.txt

## Setup

1. Clone the repository and navigate to the post-14-planning-agent folder.
2. Copy .env.template to .env and fill in the values:
   - LITELLM_BASE_URL: the URL of your LiteLLM proxy
   - MODEL_NAME: the model name LiteLLM will route to
   - LITELLM_API_KEY: the API key for your LiteLLM instance
   - GOAL: the business goal you want to plan
3. Install dependencies:
   pip install -r requirements.txt
4. Run the agent:
   python agent.py

## How to switch providers

All communication goes through LiteLLM. To use a different model or provider,
change only MODEL_NAME in your .env file. No code changes are required.

Examples:
- MODEL_NAME=deepseek/deepseek-chat
- MODEL_NAME=gemini/gemini-2.0-flash
- MODEL_NAME=gpt-4o

## What NosisTech changed from the original

This is an independent educational rebuild inspired by the architecture of the referenced framework or source project. It is not affiliated with, endorsed by, or presented as a replacement for the original project.

The original Packt Chapter 5 implementation was tightly coupled to a single
model and hardcoded the Anthropic provider. It used simulated execution with
mock classes, IPython display elements, and insecure API key entry. NosisTech
rebuilt the agent to be:

- Model and provider agnostic: all configuration is environment-driven via LiteLLM
- Secure by default: no hardcoded keys, no provider overrides
- Small Python implementation: official OpenAI SDK plus python-dotenv, no LangChain or LangGraph
- Practical safeguards: rate-limit backoff, input validation, graceful error handling
- Real-world demo: sample goals reference NosisTech LLC

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.
