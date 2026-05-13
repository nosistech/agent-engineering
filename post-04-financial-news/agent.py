# MIT License, Copyright 2025 Packt

"""Financial News Agent: fetch ticker news and summarize it through LiteLLM."""

import os
import sys
import time

import requests
from dotenv import load_dotenv
from openai import APIConnectionError, OpenAI, RateLimitError


REQUIRED_ENV = [
    "LITELLM_BASE_URL",
    "MODEL_NAME",
    "LITELLM_API_KEY",
    "ALPHA_VANTAGE_API_KEY",
    "TICKER",
]

SYSTEM_PROMPT = (
    "You are a financial news summarizer. "
    "Your role is to summarize only the news content provided to you. "
    "Do not generate price predictions, investment recommendations, "
    "or financial opinions from your own knowledge. "
    "Report only what the provided articles say."
)


def load_config() -> dict[str, str]:
    """Load required settings from .env and stop early if any are missing."""
    load_dotenv()
    missing = [name for name in REQUIRED_ENV if not os.getenv(name)]
    if missing:
        print("Missing required environment variables:")
        for name in missing:
            print(f"  - {name}")
        sys.exit(1)

    config = {name: os.environ[name] for name in REQUIRED_ENV}
    print(f"Active model: {config['MODEL_NAME']}")
    return config


def validate_ticker(ticker: str) -> str:
    """Clean the ticker symbol and ensure it is 1-5 alphanumeric characters."""
    cleaned = ticker.strip().upper()
    if not cleaned.isalnum():
        raise ValueError("Ticker symbol must contain only letters and numbers.")
    if not 1 <= len(cleaned) <= 5:
        raise ValueError("Ticker symbol must be 1 to 5 characters long.")
    return cleaned


def fetch_news(ticker: str, api_key: str, limit: int = 5) -> list[dict[str, str]]:
    """Retrieve recent Alpha Vantage news articles for a ticker."""
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "NEWS_SENTIMENT",
        "tickers": ticker,
        "apikey": api_key,
        "limit": limit,
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        raise RuntimeError("Network error while reaching Alpha Vantage.") from exc

    data = response.json()
    if "Information" in data:
        raise RuntimeError(
            "Alpha Vantage API limit reached or usage restricted. "
            f"The API responded with: {data['Information']}"
        )

    articles = data.get("feed") or []
    if not articles:
        raise RuntimeError(f"No news articles returned for ticker '{ticker}'.")

    return [
        {
            "title": article.get("title", "No title"),
            "summary": article.get("summary", "No summary"),
            "sentiment": article.get("overall_sentiment_label", "Neutral"),
        }
        for article in articles[:limit]
    ]


def format_articles(articles: list[dict[str, str]]) -> str:
    """Format articles as a consistent text block for the model."""
    return "\n\n".join(
        "Headline: {title}\nSummary: {summary}\nSentiment: {sentiment}".format(**article)
        for article in articles
    )


def analyze_news(client: OpenAI, model: str, ticker: str, articles: list[dict[str, str]]) -> str:
    """Ask the model for a grounded briefing using only the retrieved articles."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"News articles for {ticker}:\n\n{format_articles(articles)}\n\n"
                f"Provide a briefing for {ticker} based only on the articles above.\n\n"
                "Return:\n"
                "1) An overall sentiment label: Positive, Negative, or Neutral.\n"
                "2) A clear three-sentence summary of what the news says.\n"
                "3) A numbered list of the top three headlines from the articles."
            ),
        },
    ]

    for attempt in range(1, 4):
        try:
            response = client.chat.completions.create(model=model, messages=messages)
            return response.choices[0].message.content
        except RateLimitError:
            if attempt == 3:
                raise RuntimeError("LLM rate limit exceeded after multiple attempts.")
            wait = 2 ** attempt
            print(f"Rate limit hit, retrying in {wait} seconds (attempt {attempt}/3)...")
            time.sleep(wait)
        except APIConnectionError as exc:
            raise RuntimeError(
                "Unable to connect to the LiteLLM endpoint. "
                "Check your LITELLM_BASE_URL and network."
            ) from exc

    raise RuntimeError("Unable to generate a briefing.")


def main() -> None:
    """Run the Financial News Agent workflow."""
    try:
        config = load_config()
        ticker = validate_ticker(config["TICKER"])
        articles = fetch_news(ticker, config["ALPHA_VANTAGE_API_KEY"])
        client = OpenAI(
            base_url=config["LITELLM_BASE_URL"],
            api_key=config["LITELLM_API_KEY"],
        )

        print(f"\nFinancial News Briefing: {ticker}")
        print(analyze_news(client, config["MODEL_NAME"], ticker, articles))
    except (RuntimeError, ValueError) as exc:
        print(exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
