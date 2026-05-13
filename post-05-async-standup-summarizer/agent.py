# (c) 2026 NosisTech LLC. Original implementation.

"""Async Standup Summarizer: turn JSON updates into a team report."""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from openai import APIConnectionError, APIError, OpenAI, RateLimitError


REQUIRED_ENV = ["LITELLM_BASE_URL", "MODEL_NAME", "LITELLM_API_KEY", "INPUT_FILE", "OUTPUT_DIR"]

INDIVIDUAL_PROMPT = (
    "You are a professional meeting assistant. Summarize the standup update into exactly "
    "three lines.\nLine 1: Completed (what was finished).\nLine 2: In Progress "
    "(what is being worked on now).\nLine 3: Blockers (anything blocking progress, "
    "or 'None' if none exist).\nBe concise and factual. Do not add information not "
    "present in the original update."
)

TEAM_PROMPT = (
    "You are a professional meeting assistant. You will receive individual standup "
    "summaries from multiple team members. Produce a consolidated team standup report "
    "with three sections:\n1. Completed This Period\n2. In Progress\n3. Active Blockers\n\n"
    "Under each section, list contributors and their relevant items as bullet points. "
    "Keep the tone factual and professional."
)


def load_config() -> dict[str, str]:
    load_dotenv()
    missing = [name for name in REQUIRED_ENV if not os.getenv(name)]
    if missing:
        raise RuntimeError("Missing required environment variables:\n" + "\n".join(f"  - {name}" for name in missing))
    config = {name: os.environ[name] for name in REQUIRED_ENV}
    print(f"Active model: {config['MODEL_NAME']}")
    return config


def load_updates(input_path: str) -> list[dict[str, str]]:
    path = Path(input_path)
    if not path.exists():
        raise RuntimeError(f"Input file not found: {input_path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Input file contains invalid JSON: {input_path}") from exc

    if not isinstance(data, list):
        raise RuntimeError("Input JSON must be a list of contributor objects.")

    contributors = []
    for index, entry in enumerate(data, start=1):
        if not isinstance(entry, dict):
            print(f"WARNING: Entry {index} is not a dictionary, skipping.")
            continue
        if not entry.get("name") or not entry.get("update"):
            print(f"WARNING: Entry {index} missing 'name' or 'update', skipping.")
            continue
        contributors.append({"name": entry["name"], "update": entry["update"]})

    if not contributors:
        raise RuntimeError("No valid contributor entries found in the input file.")
    return contributors


def call_model(client: OpenAI, model: str, messages: list[dict[str, str]]) -> str:
    for attempt in range(1, 4):
        try:
            response = client.chat.completions.create(model=model, messages=messages, temperature=0.3)
            return response.choices[0].message.content.strip()
        except RateLimitError:
            if attempt == 3:
                raise RuntimeError("Rate limit retries exhausted. Please try again later.")
            wait = 2 ** (attempt - 1)
            print(f"Rate limited. Retrying in {wait}s (attempt {attempt}/3)...")
            time.sleep(wait)
        except APIConnectionError as exc:
            raise RuntimeError("Cannot connect to LiteLLM. Check LITELLM_BASE_URL and your network.") from exc
        except APIError as exc:
            raise RuntimeError(f"API call failed: {exc}") from exc

    raise RuntimeError("Model call failed.")


def summarize_contributor(client: OpenAI, model: str, contributor: dict[str, str]) -> str:
    return call_model(
        client,
        model,
        [
            {"role": "system", "content": INDIVIDUAL_PROMPT},
            {"role": "user", "content": f"Contributor name: {contributor['name']}.\nUpdate: {contributor['update']}"},
        ],
    )


def synthesize_team_report(client: OpenAI, model: str, summaries: list[tuple[dict[str, str], str]]) -> str:
    contributor_blocks = "\n\n".join(
        f"Contributor {index}: {contributor['name']}\nSummary:\n{summary}"
        for index, (contributor, summary) in enumerate(summaries, start=1)
    )
    return call_model(
        client,
        model,
        [
            {"role": "system", "content": TEAM_PROMPT},
            {"role": "user", "content": f"Team standup summaries:\n\n{contributor_blocks}"},
        ],
    )


def save_report(report: str, output_dir: str) -> Path:
    report_dir = Path(output_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"standup_report_{datetime.now():%Y%m%d_%H%M%S}.txt"
    report_path.write_text(report, encoding="utf-8")
    return report_path


def main() -> None:
    try:
        config = load_config()
        client = OpenAI(base_url=config["LITELLM_BASE_URL"], api_key=config["LITELLM_API_KEY"])
        contributors = load_updates(config["INPUT_FILE"])
        print(f"Loaded {len(contributors)} contributor(s).")

        summaries = []
        for contributor in contributors:
            summary = summarize_contributor(client, config["MODEL_NAME"], contributor)
            summaries.append((contributor, summary))
            print(f"{contributor['name']}: summarized")

        print("Generating team report...")
        team_report = synthesize_team_report(client, config["MODEL_NAME"], summaries)
        print(f"\n{'=' * 60}\n{team_report}\n{'=' * 60}\n")
        print(f"Report saved to: {save_report(team_report, config['OUTPUT_DIR'])}")
    except RuntimeError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
