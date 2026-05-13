# Market Data Agent for NosisTech LLC

## What this agent does

The Market Data Agent accepts a stock ticker symbol, fetches verified market
data with `yfinance`, and sends those numbers to a language model through a
LiteLLM-compatible OpenAI SDK client.

The architecture lesson is compliance by separation: Python retrieves the
financial figures, and the model only summarizes the verified data it receives.
The model should not invent prices, market caps, PE ratios, or recommendations.

## Prerequisites

- Python 3.11 or later
- pip
- A LiteLLM proxy running locally or on a VPS
- A chat model reachable through that proxy

## Setup

1. Copy `.env.template` to `.env` and fill in your values:

   ```bash
   cp .env.template .env
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run the agent with a ticker:

   ```bash
   python agent.py AAPL
   ```

If no ticker is given on the command line, the script asks for one.

## Environment variables

- `LITELLM_BASE_URL`: URL of your LiteLLM-compatible endpoint
- `MODEL_NAME`: model route configured in LiteLLM
- `LITELLM_API_KEY`: API key expected by your LiteLLM endpoint
- `LITELLM_TIMEOUT`: request timeout in seconds

## What NosisTech changed from the original

- Reduced the example to one data provider: `yfinance`
- Removed unused local `litellm`, Finnhub, and Pydantic dependencies
- Kept ticker validation before the provider call
- Kept verified Python data retrieval separate from model summarization
- Added a clear source line so readers know where the market data came from

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.
