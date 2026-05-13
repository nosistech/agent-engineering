# (c) 2026 NosisTech LLC. Original implementation.

import os
import re
import sys
from datetime import datetime, timezone

import yfinance as yf
from dotenv import load_dotenv
from openai import OpenAI


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REQUIRED_ENV_VARS = ["LITELLM_BASE_URL", "MODEL_NAME", "LITELLM_API_KEY"]


def check_env() -> None:
    """Stop early if the LiteLLM configuration is incomplete."""
    missing = [name for name in REQUIRED_ENV_VARS if not os.getenv(name)]
    if missing:
        print("Missing required environment variables:")
        for name in missing:
            print(f"  - {name}")
        print("Create a .env file from .env.template and try again.")
        sys.exit(1)


def clean_ticker(ticker: str) -> str:
    """Normalize and validate a stock ticker before calling the data provider."""
    ticker = ticker.strip().upper()
    if not re.fullmatch(r"[A-Z.\-]{1,10}", ticker):
        raise ValueError("Use a valid ticker symbol like AAPL, MSFT, or BRK-B.")
    return ticker


def fetch_market_data(ticker: str) -> dict:
    """Fetch verified market data from yfinance."""
    ticker = clean_ticker(ticker)
    info = yf.Ticker(ticker).info
    if not info or "currentPrice" not in info:
        raise ValueError(f"Could not retrieve market data for {ticker}.")

    return {
        "ticker": ticker,
        "current_price": float(info["currentPrice"]),
        "volume": int(info.get("volume") or 0),
        "week_52_high": float(info.get("fiftyTwoWeekHigh") or 0),
        "week_52_low": float(info.get("fiftyTwoWeekLow") or 0),
        "market_cap": info.get("marketCap"),
        "pe_ratio": info.get("trailingPE"),
        "currency": info.get("currency", "USD"),
        "data_timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "yfinance",
    }


def summarize_market_data(market_data: dict) -> str:
    """Ask the model to summarize only the verified data Python fetched."""
    facts = (
        f"Ticker {market_data['ticker']}; current price {market_data['current_price']} "
        f"{market_data['currency']}; volume {market_data['volume']}; 52-week high "
        f"{market_data['week_52_high']}; 52-week low {market_data['week_52_low']}; "
        f"market cap {market_data.get('market_cap')}; PE ratio {market_data.get('pe_ratio')}; "
        f"source {market_data['source']}."
    )
    client = OpenAI(
        base_url=os.getenv("LITELLM_BASE_URL"),
        api_key=os.getenv("LITELLM_API_KEY"),
        timeout=float(os.getenv("LITELLM_TIMEOUT", "60")),
    )
    response = client.chat.completions.create(
        model=os.getenv("MODEL_NAME"),
        messages=[
            {
                "role": "system",
                "content": (
                    "Return only the final answer. Write one short plain-English "
                    "paragraph summarizing verified market data. Do not use bullet "
                    "points, predictions, recommendations, or financial advice."
                ),
            },
            {
                "role": "user",
                "content": f"Write one complete sentence using only these facts: {facts}",
            },
        ],
        max_tokens=800,
    )

    content = response.choices[0].message.content
    if not content or len(content.strip()) < 40 or content.strip()[-1] not in ".!?":
        raise ValueError("The model returned an empty or incomplete summary.")
    return content


def run_agent(ticker: str) -> dict:
    """Fetch verified numbers first, then let the model explain them."""
    market_data = fetch_market_data(ticker)
    summary = summarize_market_data(market_data)
    return {"market_data": market_data, "summary": summary, "model": os.getenv("MODEL_NAME")}


def print_result(result: dict) -> None:
    """Print the verified figures and model summary."""
    data = result["market_data"]
    print("\n--- Verified Market Data ---")
    print(f"Ticker:       {data['ticker']}")
    print(f"Price:        {data['current_price']} {data['currency']}")
    print(f"Volume:       {data['volume']:,}")
    print(f"52-Week High: {data['week_52_high']}")
    print(f"52-Week Low:  {data['week_52_low']}")
    if data.get("market_cap") is not None:
        print(f"Market Cap:   {data['market_cap']:,.2f}")
    if data.get("pe_ratio") is not None:
        print(f"PE Ratio:     {data['pe_ratio']:.2f}")
    print(f"Source:       {data['source']}")
    print(f"Timestamp:    {data['data_timestamp']}")
    print(f"\nAI Summary ({result['model']}):\n{result['summary']}")


def main() -> None:
    load_dotenv()
    check_env()
    ticker = sys.argv[1] if len(sys.argv) > 1 else input("Enter a stock ticker symbol: ")

    try:
        print(f"Market Data Agent running. Model: {os.getenv('MODEL_NAME')}.")
        print_result(run_agent(ticker))
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
