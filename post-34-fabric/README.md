# Fabric Pattern Runner

## What This Agent Does

This agent demonstrates the core architectural pattern behind Fabric: reusable prompt operations called patterns. Each pattern stores a name, purpose, and system prompt. The agent selects a pattern by name, validates the input, combines both into a model request, and routes the request through LiteLLM.

Three built-in patterns are included: summarizing a business briefing, extracting operational or compliance risks, and converting a status note into a numbered action plan. Three fictional demo inputs run automatically so the pattern-router behavior is visible on the first run.

## Prerequisites

- Python 3.14.2
- pip
- A running LiteLLM proxy reachable through the URL you configure in `.env`
- An API key valid for your chosen model provider, passed through LiteLLM

## Setup

1. Clone or copy this agent folder to your machine.
2. Copy `.env.template` to `.env` and fill in all four values.
3. Install dependencies with `pip install -r requirements.txt`.
4. Run the agent with `python agent.py`.

To preview prompts without spending API credits, set `DRY_RUN=true` in `.env` before running.

## How to Switch AI Providers

Change `MODEL_NAME` in `.env` to any model string supported by your LiteLLM proxy. No code changes are required. LiteLLM handles provider routing based on the model name you supply.

## What NosisTech Changed from the Original

This is an independent educational rebuild inspired by the architecture of the referenced framework or source project. It is not affiliated with, endorsed by, or presented as a replacement for the original project.

Fabric is a large open-source project written in Go. It includes a CLI, REST API server, Svelte web UI, YouTube transcript extraction, web scraping, SQLite storage, shell installer scripts, and a large library of community-contributed pattern files. None of those components are recreated here.

This rebuild keeps only the essential idea: store reusable instructions as named patterns, combine a pattern with user input, and send the result to a language model. The Go CLI is replaced with one Python main function. The REST API server and web UI are removed. The pattern library is replaced with three in-code patterns. The provider plugin system is replaced with an OpenAI-compatible client routed through LiteLLM. Secrets and configuration are loaded from environment variables.

NosisTech added startup validation that lists missing environment variables before any API call, graceful error handling that avoids raw stack traces, input length validation, pattern name validation, rate limit handling with exponential backoff, and a dry-run mode for prompt inspection without API cost.

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.
