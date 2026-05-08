# MIT License, Copyright 2025 Packt

"""
Compliance Architecture Principle:
All financial figures in the output originate from the configured data provider
(yfinance or Finnhub). The language model (LiteLLM) only summarizes the
pre-validated data. It never invents, guesses, or adds any financial metric
not present in the input. This separation of roles ensures that every number
presented to a user is traceable to a data provider.
"""

import os
import sys
import json
import time
import re
from datetime import datetime, timezone

import dotenv
from pydantic import BaseModel, Field
from openai import OpenAI, RateLimitError

# ---------------------------------------------------------------------------
# Environment and configuration
# ---------------------------------------------------------------------------
dotenv.load_dotenv()

# ---------------------------------------------------------------------------
# Pydantic model for validated market data
# ---------------------------------------------------------------------------
class MarketData(BaseModel):
    ticker: str = Field(..., description="Stock ticker symbol")
    current_price: float = Field(..., description="Most recent trading price")
    volume: int = Field(..., description="Trading volume of the last session")
    week_52_high: float = Field(..., description="Highest price in the last 52 weeks")
    week_52_low: float = Field(..., description="Lowest price in the last 52 weeks")
    market_cap: float | None = Field(None, description="Market capitalisation, if available")
    pe_ratio: float | None = Field(None, description="Price-to-earnings ratio, if available")
    currency: str = Field(default="USD", description="Currency of the quoted price")
    data_timestamp: str = Field(..., description="UTC ISO timestamp when data was fetched")


# ---------------------------------------------------------------------------
# Startup checks
# ---------------------------------------------------------------------------
def check_env():
    """Validate all required environment variables and exit cleanly if any are missing."""
    missing = []
    for var in ("LITELLM_BASE_URL", "MODEL_NAME", "LITELLM_API_KEY"):
        if not os.getenv(var):
            missing.append(var)
    if os.getenv("DATA_PROVIDER") == "finnhub" and not os.getenv("FINNHUB_API_KEY"):
        missing.append("FINNHUB_API_KEY")
    if missing:
        print("Missing required environment variables:")
        for m in missing:
            print(f"  - {m}")
        print("Create a .env file from .env.template and try again.")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Ticker validation
# ---------------------------------------------------------------------------
def validate_ticker(ticker: str) -> str:
    """Clean and validate a stock ticker symbol; raise ValueError if invalid."""
    ticker = ticker.strip().upper()
    if not re.fullmatch(r'^[A-Z.\-]{1,10}$', ticker):
        raise ValueError(
            f"Invalid ticker symbol '{ticker}'. "
            "Use 1-10 letters, dots, or hyphens (e.g., AAPL, BRK-B)."
        )
    return ticker


# ---------------------------------------------------------------------------
# Data retrieval
# ---------------------------------------------------------------------------
def get_market_data(ticker: str) -> dict:
    """Fetch market data for a ticker and return a validated MarketData dict."""
    provider = os.getenv("DATA_PROVIDER", "yfinance").strip().lower()
    ticker_clean = validate_ticker(ticker)

    try:
        if provider == "yfinance":
            import yfinance as yf
            stock = yf.Ticker(ticker_clean)
            info = stock.info
            if not info or "currentPrice" not in info:
                raise ValueError(
                    f"Could not retrieve data for ticker {ticker_clean}. "
                    "Verify the ticker symbol is correct and yfinance is not rate-limited."
                )
            market_data = MarketData(
                ticker=ticker_clean,
                current_price=float(info["currentPrice"]),
                volume=int(info.get("volume", 0)),
                week_52_high=float(info.get("fiftyTwoWeekHigh", 0.0)),
                week_52_low=float(info.get("fiftyTwoWeekLow", 0.0)),
                market_cap=float(info["marketCap"]) if info.get("marketCap") is not None else None,
                pe_ratio=float(info["trailingPE"]) if info.get("trailingPE") is not None else None,
                currency=info.get("currency", "USD"),
                data_timestamp=datetime.now(timezone.utc).isoformat(),
            )

        elif provider == "finnhub":
            import finnhub
            api_key = os.getenv("FINNHUB_API_KEY")
            client = finnhub.Client(api_key=api_key)

            quote = client.quote(ticker_clean)
            if not quote or "c" not in quote:
                raise ValueError(
                    f"Finnhub quote empty for {ticker_clean}. Check ticker and API key."
                )

            metrics = client.company_basic_financials(ticker_clean, "all")
            pe_ratio = None
            market_cap = None
            week_52_high = float(quote.get("h", 0.0))
            week_52_low = float(quote.get("l", 0.0))

            if metrics and "metric" in metrics:
                metric = metrics["metric"]
                pe_ratio = float(metric["peBasicExclExtraTTM"]) if metric.get("peBasicExclExtraTTM") else None
                market_cap = float(metric["marketCapitalization"]) if metric.get("marketCapitalization") else None
                if metric.get("52WeekHigh"):
                    week_52_high = float(metric["52WeekHigh"])
                if metric.get("52WeekLow"):
                    week_52_low = float(metric["52WeekLow"])

            market_data = MarketData(
                ticker=ticker_clean,
                current_price=float(quote["c"]),
                volume=int(quote.get("v", 0)),
                week_52_high=week_52_high,
                week_52_low=week_52_low,
                market_cap=market_cap,
                pe_ratio=pe_ratio,
                currency="USD",
                data_timestamp=datetime.now(timezone.utc).isoformat(),
            )

        else:
            raise ValueError(
                f"Unknown DATA_PROVIDER: {provider}. "
                "Supported values are yfinance and finnhub."
            )

        return market_data.model_dump()

    except ValueError:
        raise
    except Exception as e:
        raise ValueError(
            f"Market data retrieval failed for {ticker_clean}: {str(e)}"
        ) from e


# ---------------------------------------------------------------------------
# LLM summarization via LiteLLM
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = (
    "You are a market data summarizer for NosisTech LLC. "
    "Summarize the following market data in 3-4 plain sentences a non-technical "
    "business professional can understand. Report only what the data shows. "
    "Do not add analysis, predictions, or information not present in the input data."
)


def _build_client() -> OpenAI:
    """Create an OpenAI client pointed at the LiteLLM proxy."""
    return OpenAI(
        base_url=os.getenv("LITELLM_BASE_URL"),
        api_key=os.getenv("LITELLM_API_KEY"),
    )


def summarize_market_data(market_data: dict) -> str:
    """Send validated market data to LiteLLM and return a plain-English summary."""
    client = _build_client()
    user_msg = (
        "Summarize this market data for a business professional:\n"
        + json.dumps(market_data, indent=2)
    )

    max_attempts = 3
    delays = [5, 15]

    for attempt in range(max_attempts):
        try:
            response = client.chat.completions.create(
                model=os.getenv("MODEL_NAME"),
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                max_tokens=300,
            )
            content = response.choices[0].message.content
            if not content:
                content = getattr(response.choices[0].message, "reasoning_content", None)
            if not content:
                raise ValueError("Model returned an empty response. Check your LiteLLM config and model name.")
            return content
        except RateLimitError:
            if attempt < max_attempts - 1:
                wait = delays[attempt] if attempt < len(delays) else 15
                time.sleep(wait)
                continue
            raise ValueError(
                "Rate limit exceeded after multiple retries. "
                "Please wait a few minutes and try again."
            )
        except Exception as e:
            base_url = os.getenv("LITELLM_BASE_URL", "unknown")
            raise ValueError(
                f"Cannot reach LiteLLM at {base_url}. "
                "Verify your VPS is running and the port is open."
            ) from e

    return ""


# ---------------------------------------------------------------------------
# Agent orchestration
# ---------------------------------------------------------------------------
def run_agent(ticker: str) -> dict:
    """Execute market data retrieval and summarization, returning a structured result."""
    market_data = get_market_data(ticker)
    summary = summarize_market_data(market_data)
    return {
        "ticker": ticker.upper(),
        "market_data": market_data,
        "summary": summary,
        "provider": os.getenv("DATA_PROVIDER", "yfinance"),
        "model_used": os.getenv("MODEL_NAME"),
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def main():
    """Command-line entry point: validate environment, get ticker, run agent, print results."""
    check_env()
    model_name = os.getenv("MODEL_NAME")
    data_provider = os.getenv("DATA_PROVIDER", "yfinance")
    print(f"Market Data Agent running. Model: {model_name}. Data provider: {data_provider}.")

    if len(sys.argv) > 1:
        ticker = sys.argv[1]
    else:
        ticker = input("Enter a stock ticker symbol: ").strip()

    try:
        result = run_agent(ticker)
    except ValueError as e:
        print(str(e))
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        sys.exit(1)

    md = result["market_data"]
    print("\n--- Market Data Summary ---")
    print(f"Ticker:       {result['ticker']}")
    print(f"Price:        {md['current_price']} {md['currency']}")
    print(f"Volume:       {md['volume']:,}")
    print(f"52-Week High: {md['week_52_high']}")
    print(f"52-Week Low:  {md['week_52_low']}")
    if md.get("market_cap") is not None:
        print(f"Market Cap:   {md['market_cap']:,.2f}")
    if md.get("pe_ratio") is not None:
        print(f"PE Ratio:     {md['pe_ratio']:.2f}")
    print(f"Timestamp:    {md['data_timestamp']}")
    print(f"\nAI Summary (by {result['model_used']}):\n{result['summary']}")


if __name__ == "__main__":
    main()