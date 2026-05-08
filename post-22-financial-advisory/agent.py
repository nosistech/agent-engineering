# MIT License, Copyright 2025 Packt

"""Financial Advisory Agent - fetches market data and news, synthesises via LiteLLM."""
import os
import sys
import time
import re

import requests
from openai import OpenAI, RateLimitError
from dotenv import load_dotenv

load_dotenv()

REQUIRED_ENV_VARS = [
    "LITELLM_BASE_URL",
    "MODEL_NAME",
    "LITELLM_API_KEY",
    "FINNHUB_API_KEY",
    "ALPHA_VANTAGE_API_KEY",
    "TICKER",
]


def load_and_validate_env():
    """Load all required environment variables and exit if any are missing."""
    missing = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
    if missing:
        print("Missing environment variables:")
        for var in missing:
            print(f"  - {var}")
        print("Please set all required variables in your .env file.")
        sys.exit(1)

    model = os.getenv("MODEL_NAME")
    print(f"Active model: {model}")


def validate_ticker(ticker: str) -> str:
    """Return the ticker uppercased and stripped, or raise ValueError."""
    cleaned = ticker.strip().upper()
    if not re.fullmatch(r"[A-Z0-9]{1,5}", cleaned):
        raise ValueError(
            "Ticker must be 1 to 5 alphanumeric characters (letters or digits)."
        )
    return cleaned


FINNHUB_QUOTE_URL = "https://finnhub.io/api/v1/quote"


def fetch_market_data(ticker: str, api_key: str) -> dict:
    """Fetch live market data from Finnhub for the given ticker."""
    try:
        resp = requests.get(
            FINNHUB_QUOTE_URL,
            params={"symbol": ticker, "token": api_key},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(
            "Failed to connect to Finnhub. Please check your network and API key."
        ) from exc

    required = {"c": "current_price", "dp": "change_percent", "h": "high",
                "l": "low"}
    for key in required:
        if key not in data or data[key] is None:
            raise RuntimeError(
                f"Finnhub response missing expected field '{key}'."
            )

    current = data["c"]
    if current == 0:
        raise RuntimeError(
            f"No data found for ticker '{ticker}'. It may be invalid or delisted."
        )

    return {
        "current_price": current,
        "change_percent": data["dp"],
        "high": data["h"],
        "low": data["l"],
        "volume": data.get("v") or "Not available on free tier",
    }


def format_market_block(data: dict, ticker: str) -> str:
    """Convert market data dict into a human-readable text block."""
    return (
        f"Ticker: {ticker}\n"
        f"Current Price: {data['current_price']}\n"
        f"Change: {data['change_percent']}%\n"
        f"High: {data['high']}\n"
        f"Low: {data['low']}\n"
        f"Volume: {data['volume']}"
    )


ALPHA_VANTAGE_URL = "https://www.alphavantage.co/query"


def fetch_news(ticker: str, api_key: str, limit: int = 5) -> list[dict]:
    """Fetch recent news headlines and sentiment for the given ticker."""
    try:
        resp = requests.get(
            ALPHA_VANTAGE_URL,
            params={
                "function": "NEWS_SENTIMENT",
                "tickers": ticker,
                "apikey": api_key,
                "limit": limit,
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(
            "Failed to connect to Alpha Vantage. Please check your network and API key."
        ) from exc

    if "Information" in data:
        raise RuntimeError(
            "Alpha Vantage API rate limit reached. Please try again later."
        )

    feed = data.get("feed")
    if not feed:
        raise RuntimeError(
            "No news articles returned for the ticker. The feed may be empty."
        )

    articles = []
    for item in feed:
        articles.append(
            {
                "title": item.get("title", "Untitled"),
                "summary": item.get("summary", "No summary available."),
                "overall_sentiment_label": item.get("overall_sentiment_label", "neutral"),
            }
        )
    return articles


def format_news_block(articles: list[dict]) -> str:
    """Convert list of article dicts into a structured text block."""
    blocks = []
    for art in articles:
        blocks.append(
            f"Headline: {art['title']}\n"
            f"Summary: {art['summary']}\n"
            f"Sentiment: {art['overall_sentiment_label']}"
        )
    return "\n\n".join(blocks)


SYSTEM_PROMPT = (
    "You are a data summarization assistant. Your role is to organize and summarize "
    "the market data and news content provided to you. Do not generate investment "
    "recommendations or financial advice from your own knowledge. Summarize and "
    "analyze only the data provided. Your output is for informational purposes only "
    "and does not constitute financial advice."
)

USER_PROMPT_TEMPLATE = """Here is the latest market data and news for {ticker}:

MARKET DATA:
{market_block}

NEWS HEADLINES:
{news_block}

Provide your analysis in exactly four sections:

1) Market Conditions: Summarize the current price data and what it indicates about recent performance.
2) News Sentiment: Summarize the overall tone and key themes from the news articles.
3) Risk Indicators: Identify any signals in the combined data that suggest elevated risk or uncertainty.
4) Summary: One paragraph synthesizing both data sets into a plain-English briefing for a non-technical business professional."""


def analyze_combined(
    market_block: str,
    news_block: str,
    ticker: str,
    client: OpenAI,
    model_name: str,
) -> str:
    """Send combined data to the LLM and return the structured briefing."""
    user_prompt = USER_PROMPT_TEMPLATE.format(
        ticker=ticker,
        market_block=market_block,
        news_block=news_block,
    )

    max_attempts = 3
    delay = 2
    for attempt in range(1, max_attempts + 1):
        try:
            completion = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
            )
            return completion.choices[0].message.content.strip()
        except RateLimitError:
            if attempt == max_attempts:
                raise RuntimeError(
                    "LLM rate limit exceeded after 3 attempts. Please try again later."
                )
            print(f"Rate limit hit. Retrying in {delay} seconds (attempt {attempt}/{max_attempts})...")
            time.sleep(delay)
            delay *= 2
        except Exception as exc:
            raise RuntimeError(
                "Could not reach the AI service. Please verify LITELLM_BASE_URL and your network connection."
            ) from exc

    raise RuntimeError("Unexpected failure in LLM call.")


def main():
    """Run the full financial advisory agent flow."""
    load_and_validate_env()
    ticker_raw = os.getenv("TICKER", "")
    try:
        ticker = validate_ticker(ticker_raw)
    except ValueError as e:
        print(f"Invalid ticker: {e}")
        sys.exit(1)

    finnhub_key = os.getenv("FINNHUB_API_KEY")
    av_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    litellm_base = os.getenv("LITELLM_BASE_URL")
    litellm_key = os.getenv("LITELLM_API_KEY")
    model_name = os.getenv("MODEL_NAME")

    print(f"Fetching market data for {ticker}...")
    try:
        market_data = fetch_market_data(ticker, finnhub_key)
        market_block = format_market_block(market_data, ticker)
    except RuntimeError as e:
        print(f"Market data error: {e}")
        sys.exit(1)

    print(f"Fetching news headlines for {ticker}...")
    try:
        news_articles = fetch_news(ticker, av_key)
        news_block = format_news_block(news_articles)
    except RuntimeError as e:
        print(f"News data error: {e}")
        sys.exit(1)

    client = OpenAI(base_url=litellm_base, api_key=litellm_key)
    print("Generating financial advisory briefing...")
    try:
        briefing = analyze_combined(
            market_block=market_block,
            news_block=news_block,
            ticker=ticker,
            client=client,
            model_name=model_name,
        )
    except RuntimeError as e:
        print(f"LLM error: {e}")
        sys.exit(1)

    print(f"\nFinancial Advisory Briefing: {ticker}\n")
    print(briefing)


if __name__ == "__main__":
    main()