# Market Data Agent for NosisTech LLC

## What this agent does

The Market Data Agent is a focused financial data worker built by NosisTech LLC, a boutique
AI governance and cloud security consultancy. It accepts a stock ticker symbol (e.g., AAPL)
and retrieves the current price, trading volume, 52-week high/low, market capitalisation, and
PE ratio from a configurable data source. The validated, real-world numbers are then passed to
a language model through a LiteLLM proxy, which generates a plain-English summary suitable for
a non-technical business professional.

Every financial figure in the output comes directly from the data provider, never from the
language model. The model only summarizes the provided data. It does not invent, interpret, or
add any numbers. This strict separation makes the agent's output safe for business use and easy
to audit.

## Prerequisites

- Python 3.11 or later
- pip
- A LiteLLM proxy running on a VPS or locally, reachable via HTTP (default: http://localhost:4000)
- An LLM accessible through that proxy (any provider supported by LiteLLM)

## Setup

1. Clone this repository.

2. Copy `.env.template` to `.env` and fill in your values:
   ```
   cp .env.template .env
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Run the agent with a ticker:
   ```
   python agent.py AAPL
   ```

If no ticker is given on the command line, you will be prompted to enter one.

## How to switch AI providers

Change `MODEL_NAME` in your `.env` file to any model string recognised by your LiteLLM proxy,
for example `gpt-4o`, `claude-sonnet-4-20250514`, `ollama/llama3`, or `deepseek/deepseek-chat`.
No changes to the code are required.

## How to switch data providers

The agent supports two data sources:

- `yfinance` (default, no extra API key needed)
- `finnhub` (requires a free or paid Finnhub API key)

To switch to Finnhub:

1. Set `DATA_PROVIDER=finnhub` in `.env`
2. Add your key as `FINNHUB_API_KEY=your_key_here`

All other logic remains the same. The validated data structure is identical regardless of source.

## What NosisTech changed from the original

This agent was extracted from a LangGraph-based supervisor system and rebuilt as a standalone,
single-responsibility worker. The original used LangChain, LangGraph, and state-graph constructs.
All of those were removed in favour of plain Python functions and the openai Python SDK pointed
at a LiteLLM proxy. Additional improvements include:

- Pydantic validation of all market data before it reaches the language model
- Startup environment variable checks that exit cleanly if required variables are missing
- Ticker symbol validation before any API call is made
- Resilient retries with exponential backoff on LLM rate-limit errors
- User-friendly error messages throughout, no raw Python exceptions exposed

---

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.
