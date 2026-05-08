# (c) 2026 NosisTech LLC. Original implementation.
import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI, APIError, RateLimitError, APIConnectionError

# ----------------------------------------------------------------------
# Environment and configuration
# ----------------------------------------------------------------------
def load_environment():
    """Load required environment variables, validate, and return them."""
    required_vars = [
        "LITELLM_BASE_URL",
        "MODEL_NAME",
        "LITELLM_API_KEY",
        "INPUT_FILE",
        "OUTPUT_DIR"
    ]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        print("ERROR: Missing required environment variables:")
        for var in missing:
            print(f"  - {var}")
        sys.exit(1)

    config = {var: os.getenv(var) for var in required_vars}
    print(f"Active model: {config['MODEL_NAME']}")
    return config


# ----------------------------------------------------------------------
# Standup data loading
# ----------------------------------------------------------------------
def load_updates(input_path):
    """Load contributor updates from a JSON file, skipping malformed entries."""
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: Input file not found: {input_path}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"ERROR: Input file contains invalid JSON: {input_path}")
        sys.exit(1)

    if not isinstance(data, list):
        print("ERROR: Input JSON must be a list of contributor objects.")
        sys.exit(1)

    contributors = []
    for idx, entry in enumerate(data, start=1):
        if not isinstance(entry, dict):
            print(f"WARNING: Entry {idx} is not a dictionary, skipping.")
            continue
        if "name" not in entry or "update" not in entry:
            print(f"WARNING: Entry {idx} missing 'name' or 'update', skipping.")
            continue
        contributors.append({"name": entry["name"], "update": entry["update"]})

    if not contributors:
        print("ERROR: No valid contributor entries found in the input file.")
        sys.exit(1)

    return contributors


# ----------------------------------------------------------------------
# LLM helper with exponential backoff
# ----------------------------------------------------------------------
def _call_with_backoff(client, model, messages, max_retries=3):
    """Call the LiteLLM completion endpoint with exponential backoff on rate limits."""
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        except RateLimitError:
            wait = 2 ** attempt
            print(f"Rate limited. Retrying in {wait}s (attempt {attempt + 1}/{max_retries})...")
            time.sleep(wait)
        except APIConnectionError:
            print("ERROR: Cannot connect to the LiteLLM endpoint. Check LITELLM_BASE_URL and your network.")
            sys.exit(1)
        except APIError as e:
            print(f"ERROR: API call failed: {e}")
            sys.exit(1)

    print("ERROR: Rate limit retries exhausted. Please try again later.")
    sys.exit(1)


# ----------------------------------------------------------------------
# Individual summarization
# ----------------------------------------------------------------------
def summarize_individual(client, model_name, contributor):
    """Summarize a single contributor's standup into three concise lines."""
    system_prompt = (
        "You are a professional meeting assistant. Summarize the standup update "
        "into exactly three lines.\n"
        "Line 1: Completed (what was finished).\n"
        "Line 2: In Progress (what is being worked on now).\n"
        "Line 3: Blockers (anything blocking progress, or 'None' if none exist).\n"
        "Be concise and factual. Do not add information not present in the original update."
    )
    user_prompt = (
        f"Contributor name: {contributor['name']}.\n"
        f"Update: {contributor['update']}"
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    return _call_with_backoff(client, model_name, messages)


# ----------------------------------------------------------------------
# Team report synthesis
# ----------------------------------------------------------------------
def synthesize_team_report(client, model_name, summaries):
    """Combine individual summaries into a consolidated team standup report."""
    system_prompt = (
        "You are a professional meeting assistant. You will receive individual "
        "standup summaries from multiple team members. Produce a consolidated "
        "team standup report. Group the report into three sections:\n"
        "1. Completed This Period\n"
        "2. In Progress\n"
        "3. Active Blockers\n\n"
        "Under each section, list contributors and their relevant items as bullet "
        "points. Keep the tone factual and professional."
    )
    contributors_text = ""
    for idx, (contributor, summary) in enumerate(summaries, start=1):
        contributors_text += (
            f"Contributor {idx}: {contributor['name']}\n"
            f"Summary:\n{summary}\n\n"
        )
    user_prompt = f"Team standup summaries:\n\n{contributors_text}"
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    return _call_with_backoff(client, model_name, messages)


# ----------------------------------------------------------------------
# Output persistence
# ----------------------------------------------------------------------
def save_report(report_text, output_dir):
    """Save the team report to a timestamped file inside output_dir."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"standup_report_{timestamp}.txt"
    filepath = os.path.join(output_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report_text)
    print(f"Report saved to: {filepath}")


# ----------------------------------------------------------------------
# Main orchestration
# ----------------------------------------------------------------------
def main():
    """Run the full async standup summarization pipeline."""
    load_dotenv()
    config = load_environment()

    client = OpenAI(
        base_url=config["LITELLM_BASE_URL"],
        api_key=config["LITELLM_API_KEY"]
    )

    contributors = load_updates(config["INPUT_FILE"])
    print(f"Loaded {len(contributors)} contributor(s).")

    individual_summaries = []
    for contributor in contributors:
        summary = summarize_individual(client, config["MODEL_NAME"], contributor)
        individual_summaries.append((contributor, summary))
        print(f"{contributor['name']}: summarized")

    print("Generating team report...")
    team_report = synthesize_team_report(client, config["MODEL_NAME"], individual_summaries)

    print("\n" + "=" * 60)
    print(team_report)
    print("=" * 60 + "\n")

    save_report(team_report, config["OUTPUT_DIR"])


if __name__ == "__main__":
    main()