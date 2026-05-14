# CrewAI Content Research and Synthesis Crew

## What This Agent Does

This agent is a three-person AI crew that automates content research and synthesis.
A Research Agent gathers structured information on your chosen topic using a built-in
research tool. A Writer Agent drafts a two-paragraph executive summary from those
findings. A Quality Agent reviews the draft and either approves it or requests
specific revisions.

The crew runs sequentially, mimicking a human editorial workflow. It was built by
NosisTech LLC as a practical demonstration of the CrewAI multi-agent orchestration
framework, routed through LiteLLM for full provider flexibility.

## Prerequisites

- Python 3.11 recommended. The pinned CrewAI version does not support Python 3.14.
- pip for package installation
- A running LiteLLM proxy with an API key

## Setup

1. Clone this repository and navigate to the agent folder.
2. Install dependencies:
   pip install -r requirements.txt
3. Copy the template and fill in your values:
   cp .env.template .env
4. Edit .env:
   - LITELLM_BASE_URL: base URL of your LiteLLM proxy
   - MODEL_NAME: model identifier in LiteLLM format
   - LITELLM_API_KEY: your proxy API key
   - RESEARCH_TOPIC: the topic you want the crew to research
5. Run:
   python agent.py

## How to Switch AI Providers

Change MODEL_NAME in your .env file to any LiteLLM-supported model identifier.
No code changes required.

## What NosisTech Built Here

This agent demonstrates the core CrewAI sequential orchestration pattern using
LiteLLM as the model routing layer. It keeps all credentials in environment
variables, disables CrewAI telemetry by default, and uses a plain Python research
tool to keep the build clean and dependency-light.

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.
