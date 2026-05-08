# Financial Advisory Agent

## What this agent does
Accepts a stock ticker symbol, fetches live market data from Finnhub (current
price, change percentage, high, low, volume), fetches recent news headlines and
sentiment from Alpha Vantage, and passes both data sets to an LLM via LiteLLM.
The LLM returns a structured four-section briefing: Market Conditions, News
Sentiment, Risk Indicators, and a plain-English Summary. The agent never
generates investment recommendations from its own knowledge. It summarizes and
synthesizes only the data it retrieves.

## Prerequisites
- Python 3.14.2
- A running LiteLLM proxy at http://localhost:4000 (or any OpenAI-compatible endpoint)
- A Finnhub API key (free tier available at finnhub.io)
- An Alpha Vantage API key (free tier available at alphavantage.co)
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
- Removed LangChain and LangGraph entirely. Replaced with direct openai SDK pointed at LiteLLM.
- Removed all hardcoded secrets, model names, and file paths. Everything comes from .env.
- Added load_dotenv() so the .env file is read automatically on startup.
- Added thorough input validation for the ticker symbol before any API call fires.
- Added partial failure handling: if one data source fails, the agent reports which one and exits cleanly rather than passing incomplete data to the LLM.
- Added zero price guard: if Finnhub returns a current price of zero, the agent exits with a plain English message before calling the LLM.
- Added exponential backoff rate-limit handling for the LLM, maximum three attempts.
- Added a compliance-framed system prompt that explicitly states the output does not constitute financial advice.

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.S