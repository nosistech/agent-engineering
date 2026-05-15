# Browser Use Web Task Planner

## What This Agent Does

This agent is a safe educational rebuild inspired by the Browser Use framework. Instead of controlling a real browser, it reads fictional static page states, asks a language model to choose the next browser-style action, validates that action locally, and prints a human-reviewable result. No browser opens, no website is contacted, and no data is read or written outside the terminal.

The goal is to teach the observe, decide, validate, report loop that sits behind AI browser automation. Every scenario uses fictional organizations and invented page content. The agent demonstrates how a planner can propose an action, how local rules can override that proposal, and how a human reviewer can inspect the output before any real system is touched.

## Educational and Liability Notice

This software is an educational planning model. It is not scraping advice, bot bypass advice, credential automation advice, or production automation guidance. It does not perform real web automation, interact with real websites, operate accounts, submit payments, or process user data.

Nothing in this repository should be treated as instruction or encouragement to automate real websites without explicit permission from the site owner and qualified review. NosisTech LLC accepts no liability for use of this code outside its educational purpose.

## Prerequisites

- Python 3.14.2 tested
- pip
- A running LiteLLM gateway reachable at the environment-specific value you configure in `.env`

## Setup

1. Clone this repository.
2. Copy `.env.template` to `.env` and fill in your own values:
   - `LITELLM_BASE_URL`: your LiteLLM gateway base URL
   - `MODEL_NAME`: the model identifier your gateway accepts
   - `LITELLM_API_KEY`: your gateway API key
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Run the agent:

```bash
python agent.py
```

## How to Switch AI Providers

Change `MODEL_NAME` in your `.env` file to any model your LiteLLM gateway supports. No code changes are required. The agent can run with any provider LiteLLM supports when your gateway is configured for that provider.

## What NosisTech Changed from Browser Use

- Removed live browser-control framework imports.
- Replaced live browser sessions with static fictional page-state dictionaries.
- Replaced actor click, type, and scroll execution with local validation of proposed actions.
- Replaced screenshot and DOM extraction with plain text page-state summaries.
- Replaced async execution with simple synchronous Python.
- Replaced event bus and watchdog architecture with direct sequential function calls.
- Replaced cloud API endpoints with a configurable LiteLLM gateway through environment variables.
- Replaced provider-specific SDKs with an OpenAI-compatible client pointed at LiteLLM.
- Replaced hardcoded model names and endpoints with `MODEL_NAME` and `LITELLM_BASE_URL` from `.env`.
- Removed captcha, stealth, proxy, bot defense, payment, login, credential, scraping, and destructive workflows.
- Added startup environment validation that exits before any API call if variables are missing.
- Added local action validation that overrides the model if it proposes a blocked action.
- Added rate limit handling with exponential backoff across up to three attempts.

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.

