# Financial Advisory Agent

## What this agent does

This project demonstrates a small composite-agent pattern:

1. Fetch verified market data for a ticker.
2. Fetch recent news for the same ticker.
3. Pass both retrieved inputs to the model.
4. Ask the model to synthesize only those inputs into a briefing.

The model does not fetch facts and does not give buy/sell advice. It summarizes the data the code retrieved.

## Prerequisites

- Python 3.11 or later
- A running LiteLLM endpoint
- Finnhub API key
- Alpha Vantage API key

## Setup

1. Copy `.env.template` to `.env`.
2. Fill in your LiteLLM, Finnhub, Alpha Vantage, and ticker values.
3. Run the agent:

```bash
python agent.py
```

No package install is required. The agent uses only the Python standard library.

## How to switch AI providers

Edit `MODEL_NAME` in `.env`. Because the agent calls LiteLLM, the code does not need to change when you switch between supported providers.

## What NosisTech changed from the original

- Reduced the project to market data, news data, and model synthesis.
- Removed `requests`, OpenAI SDK, dotenv, retry scaffolding, and formatting layers.
- Kept ticker validation and source separation.
- Kept the compliance boundary: informational summary only, not financial advice.

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.
