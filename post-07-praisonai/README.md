# PraisonAI Multi-Agent Workflow

## What This Agent Does

This agent implements a two-agent sequential workflow built on the PraisonAI
pattern. A Researcher agent gathers and structures information on any topic
you provide. A Writer agent then takes those findings and produces a
plain-English summary a business leader can act on immediately.

The entire workflow is configured through a simple agents.yaml file. No
Python code changes are needed to modify the agents' roles, goals, or
instructions. AI provider switching is handled by LiteLLM: changing the
MODEL_NAME environment variable reroutes all requests to a different model
without touching the source code. The project follows production-grade
security practices with no hardcoded secrets and environment-variable-only
configuration.

## Prerequisites

- Python 3.11
- pip package manager
- A running LiteLLM proxy server or any OpenAI-compatible endpoint

## Setup

1. Clone the repository and navigate to the project folder.

2. Create your .env file from the template:

   cp .env.template .env

3. Edit .env and fill in your actual values:
   - LITELLM_BASE_URL: URL of your LiteLLM proxy (example: http://localhost:4000)
   - MODEL_NAME: Model identifier your proxy expects (example: gpt-4o or claude-3-5-sonnet-20241022)
   - LITELLM_API_KEY: Your LiteLLM proxy master key
   - MEMORY_PATH: Optional path for persistent storage (not used in this version)

4. Install dependencies:

   pip install -r requirements.txt

5. Run the agent with a topic:

   python agent.py "latest trends in AI governance"

## How to Switch AI Providers

Change the MODEL_NAME value in your .env file to the model identifier your
LiteLLM proxy recognizes. Nothing else needs to be modified. The same Python
code works identically with any provider as long as LiteLLM routes it correctly.

Examples:

   MODEL_NAME=claude-3-5-sonnet-20241022
   MODEL_NAME=gemini/gemini-1.5-pro
   MODEL_NAME=ollama/llama3

## How to Customize Agents

Open agents.yaml and edit the researcher or writer sections. You can change:

- role: the persona the agent assumes
- goal: what the agent should achieve
- backstory: additional context that shapes its behavior

No Python code needs to be edited. Save the file and the next run
automatically uses your updated configuration.

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.
