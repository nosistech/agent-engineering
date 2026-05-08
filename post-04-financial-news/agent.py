# MIT License, Copyright 2025 Packt

"""Financial News Agent - fetches news via Alpha Vantage, summarises via LiteLLM."""
import os
import sys
import time

import requests
from openai import OpenAI, RateLimitError, APIConnectionError
from dotenv import load_dotenv

load_dotenv()


def load_and_validate_env() -> dict:
    """Check required environment variables and return them, exit if any missing."""
    required = [
        "LITELLM_BASE_URL",
        "MODEL_NAME",
        "LITELLM_API_KEY",
        "ALPHA_VANTAGE_API_KEY",
        "TICKER",
    ]
    missing = [var for var in required if not os.getenv(var)]

    if missing:
        print("Missing required environment variables:")
        for var in missing:
            print(f"  - {var}")
        sys.exit(1)

    env = {var: os.getenv(var) for var in required}
    print(f"Active model: {env['MODEL_NAME']}")
    return env


def validate_ticker(ticker: str) -> str:
    """Clean the ticker symbol and ensure it is 1-5 alphanumeric characters."""
    cleaned = ticker.strip().upper()
    if not cleaned.isalnum():
        raise ValueError("Ticker symbol must contain only letters and numbers.")
    if not (1 <= len(cleaned) <= 5):
        raise ValueError("Ticker symbol must be 1 to 5 characters long.")
    return cleaned


def fetch_news(ticker: str, api_key: str, limit: int = 5) -> list[dict]:
    """Retrieve latest news articles for the given ticker from Alpha Vantage."""
    url = (
        "https://www.alphavantage.co/query"
        f"?function=NEWS_SENTIMENT&tickers={ticker}&apikey={api_key}&limit={limit}"
    )

    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
    except requests.exceptions.RequestException as exc:
        raise RuntimeError("Network error while reaching Alpha Vantage.") from exc

    data = resp.json()

    if "Information" in data:
        raise RuntimeError(
            "Alpha Vantage API limit reached or usage restricted. "
            "The API responded with: " + data["Information"]
        )

    articles = data.get("feed")
    if not articles:
        raise RuntimeError(
            f"No news articles returned for ticker '{ticker}'. "
            "The API response did not contain a feed."
        )

    extracted = []
    for article in articles:
        extracted.append(
            {
                "title": article.get("title", "No title"),
                "summary": article.get("summary", "No summary"),
                "overall_sentiment_label": article.get(
                    "overall_sentiment_label", "Neutral"
                ),
            }
        )
    return extracted


def format_news_block(articles: list[dict]) -> str:
    """Convert a list of article dicts into a structured text block."""
    blocks = []
    for article in articles:
        blocks.append(
            f"Headline: {article['title']}\n"
            f"Summary: {article['summary']}\n"
            f"Sentiment: {article['overall_sentiment_label']}"
        )
    return "\n\n".join(blocks)


def analyze_news(news_block: str, ticker: str, client, model_name: str) -> str:
    """Send the news block to the LLM and return the plain-English briefing."""
    system_prompt = (
        "You are a financial news summarizer. "
        "Your role is to summarize only the news content provided to you. "
        "Do not generate price predictions, investment recommendations, "
        "or financial opinions from your own knowledge. "
        "Report only what the provided articles say."
    )

    user_prompt = (
        f"News articles for {ticker}:\n\n{news_block}\n\n"
        f"Provide a briefing for {ticker} based on the articles above.\n\n"
        f"Return:\n"
        f"1) An overall sentiment label: Positive, Negative, or Neutral.\n"
        f"2) A three-sentence plain-English summary of what the news says.\n"
        f"3) A numbered list of the top three headlines from the articles."
    )

    max_attempts = 3
    backoff = 2

    for attempt in range(1, max_attempts + 1):
        try:
            completion = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            return completion.choices[0].message.content
        except RateLimitError:
            if attempt < max_attempts:
                wait = backoff * (2 ** (attempt - 1))
                print(f"Rate limit hit, retrying in {wait} seconds (attempt {attempt}/{max_attempts})...")
                time.sleep(wait)
            else:
                raise RuntimeError(
                    "LLM rate limit exceeded after multiple attempts. "
                    "Please try again later."
                )
        except APIConnectionError:
            raise RuntimeError(
                "Unable to connect to the LiteLLM endpoint. "
                "Check your LITELLM_BASE_URL and network."
            )


def main():
    """Run the Financial News Agent workflow."""
    try:
        env = load_and_validate_env()
        ticker = validate_ticker(env["TICKER"])

        articles = fetch_news(ticker, env["ALPHA_VANTAGE_API_KEY"])
        news_block = format_news_block(articles)

        client = OpenAI(
            base_url=env["LITELLM_BASE_URL"],
            api_key=env["LITELLM_API_KEY"],
        )
        briefing = analyze_news(news_block, ticker, client, env["MODEL_NAME"])

        print(f"\nFinancial News Briefing: {ticker}")
        print(briefing)

    except ValueError as err:
        print(f"Input error: {err}")
        sys.exit(1)
    except requests.exceptions.RequestException as err:
        print(f"Network error: {err}")
        sys.exit(1)
    except RuntimeError as err:
        print(str(err))
        sys.exit(1)
    except Exception as err:
        print(f"An unexpected error occurred: {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()