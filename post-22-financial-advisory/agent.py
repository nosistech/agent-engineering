# MIT License, Copyright 2025 Packt

import json
import os
import sys
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


PROJECT_DIR = Path(__file__).resolve().parent
REQUIRED_ENV = (
    "LITELLM_BASE_URL",
    "MODEL_NAME",
    "LITELLM_API_KEY",
    "FINNHUB_API_KEY",
    "ALPHA_VANTAGE_API_KEY",
    "TICKER",
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load_env() -> None:
    path = PROJECT_DIR / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key, value)


def require_env() -> None:
    missing = [key for key in REQUIRED_ENV if not os.getenv(key)]
    if missing:
        raise SystemExit(f"Missing environment variables: {', '.join(missing)}")
    print(f"[INFO] Active model: {os.getenv('MODEL_NAME')}")


def ticker() -> str:
    value = os.getenv("TICKER", "").strip().upper()
    if not value.isalnum() or len(value) > 5:
        raise SystemExit("Ticker must be 1 to 5 letters or digits.")
    return value


def get_json(url: str, params: dict, headers: dict | None = None) -> dict:
    request = Request(url + "?" + urlencode(params), headers=headers or {})
    with urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_market_data(symbol: str) -> dict:
    data = get_json(
        "https://finnhub.io/api/v1/quote",
        {"symbol": symbol, "token": os.getenv("FINNHUB_API_KEY")},
    )
    if not data.get("c"):
        raise SystemExit(f"No market price returned for ticker: {symbol}")
    return {
        "ticker": symbol,
        "current_price": data.get("c"),
        "change_percent": data.get("dp"),
        "high": data.get("h"),
        "low": data.get("l"),
    }


def fetch_news(symbol: str, limit: int = 3) -> list[dict]:
    data = get_json(
        "https://www.alphavantage.co/query",
        {
            "function": "NEWS_SENTIMENT",
            "tickers": symbol,
            "apikey": os.getenv("ALPHA_VANTAGE_API_KEY"),
            "limit": limit,
        },
    )
    if "Information" in data:
        raise SystemExit("Alpha Vantage rate limit reached. Try again later.")

    articles = [
        {
            "title": item.get("title"),
            "summary": item.get("summary"),
            "sentiment": item.get("overall_sentiment_label", "Neutral"),
        }
        for item in data.get("feed", [])[:limit]
    ]
    if not articles:
        raise SystemExit(f"No news returned for ticker: {symbol}")
    return articles


def call_llm(prompt: str) -> str:
    payload = json.dumps(
        {
            "model": os.getenv("MODEL_NAME"),
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You summarize only the provided market and news data. "
                        "Do not add outside facts, predictions, buy/sell advice, or financial recommendations. "
                        "State that the output is informational only and not financial advice."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
    ).encode("utf-8")

    request = Request(
        os.getenv("LITELLM_BASE_URL").rstrip("/") + "/chat/completions",
        data=payload,
        headers={
            "Authorization": "Bearer " + os.getenv("LITELLM_API_KEY"),
            "Content-Type": "application/json",
        },
    )
    with urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))["choices"][0]["message"]["content"].strip()


def build_prompt(market: dict, news: list[dict]) -> str:
    return (
        "Create a four-section briefing using only this JSON data:\n\n"
        f"{json.dumps({'market_data': market, 'news': news}, indent=2)}\n\n"
        "Sections: Market Conditions, News Sentiment, Risk Indicators, Summary."
    )


def main() -> None:
    load_env()
    require_env()
    symbol = ticker()

    print(f"[FETCH] Market data for {symbol}")
    market = fetch_market_data(symbol)
    print(f"[FETCH] News for {symbol}")
    news = fetch_news(symbol)

    print("\nVERIFIED INPUTS")
    print(json.dumps({"market_data": market, "news": news}, indent=2))
    print(f"\nFINANCIAL BRIEFING: {symbol}")
    print(call_llm(build_prompt(market, news)))


if __name__ == "__main__":
    main()
