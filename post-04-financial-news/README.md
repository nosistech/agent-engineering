# Financial News Agent

## What this agent does
Accepts a stock ticker symbol, fetches recent news headlines and article summaries
from the Alpha Vantage News and Sentiment API, formats the content, and passes it
to an LLM via LiteLLM to produce a clear briefing. The briefing contains
an overall sentiment label, a three-sentence summary, and the top three headlines.
The agent summarizes only the content it retrieves. It never generates financial
opinions, price predictions, or investment recommendations from its own knowledge.

## Prerequisites
- Python 3.14.2
- A running LiteLLM Proxy at http://localhost:4000 (or any OpenAI-compatible endpoint)
- An Alpha Vantage API key (free tier is sufficient, 25 requests per day)
- Valid API keys for the LLM provider you intend to use

## Setup
1. Copy the project files into a directory.
2. Copy .env.template to .env and fill in your real values.
3. Install dependencies:
   pip install -r requirements.txt
4. Run the agent:
   python agent.py

## How to switch AI providers
1. Set MODEL_NAME in .env to any model your LiteLLM proxy recognizes.
   Examples: deepseek-v4-pro, gemini-flash, gpt-4o, claude-sonnet-4-6
2. Restart the agent. No code changes required.

## What NosisTech changed from the original

This is an independent educational rebuild inspired by the architecture of the referenced framework or source project. It is not affiliated with, endorsed by, or presented as a replacement for the original project.
- Removed LangChain and LangGraph entirely. Replaced with the direct OpenAI SDK pointed at LiteLLM.
- Removed third-party news wrappers. Uses direct requests calls to Alpha Vantage.
- Added environment variable validation on startup with clear missing-variable messages.
- Added ticker validation: uppercase enforcement, alphanumeric check, 1-5 character limit.
- Added Alpha Vantage error key handling to prevent empty responses reaching the LLM.
- Added exponential backoff rate-limit handling for the LLM, maximum three attempts.
- Added a compliance-framed system prompt that instructs the model to summarize only provided content.
- Removed all hardcoded secrets, model names, and file paths.

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.
