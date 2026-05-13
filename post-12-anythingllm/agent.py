# (c) 2026 NosisTech LLC. Original implementation.
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parent
load_dotenv(PROJECT_DIR / ".env")

REQUIRED_VARS = ["ANYTHINGLLM_BASE_URL", "ANYTHINGLLM_API_KEY", "ANYTHINGLLM_WORKSPACE"]


def load_config():
    missing = [name for name in REQUIRED_VARS if not os.getenv(name)]
    if missing:
        print("Missing required environment variables: " + ", ".join(missing))
        sys.exit(1)

    return {
        "base_url": os.getenv("ANYTHINGLLM_BASE_URL").rstrip("/"),
        "api_key": os.getenv("ANYTHINGLLM_API_KEY"),
        "workspace": os.getenv("ANYTHINGLLM_WORKSPACE"),
    }


def request_anythingllm(config, method, path, **kwargs):
    url = f"{config['base_url']}{path}"
    headers = {"Authorization": f"Bearer {config['api_key']}"}

    for attempt in range(3):
        try:
            response = requests.request(method, url, headers=headers, timeout=120, **kwargs)
            if response.status_code != 429:
                return response
            wait_seconds = 2 ** (attempt + 1)
            print(f"Rate limit hit. Retrying in {wait_seconds} seconds.")
            time.sleep(wait_seconds)
        except requests.RequestException as error:
            if attempt == 2:
                raise RuntimeError(f"Cannot reach AnythingLLM at {config['base_url']}: {error}")
            wait_seconds = 2 ** (attempt + 1)
            print(f"Network issue. Retrying in {wait_seconds} seconds.")
            time.sleep(wait_seconds)

    raise RuntimeError("AnythingLLM rate limit persisted after retries.")


def check_health(config):
    response = request_anythingllm(config, "GET", "/api/v1/auth")
    if response.status_code != 200:
        raise RuntimeError(f"Health check failed with status {response.status_code}: {response.text[:300]}")
    print("Health check passed. AnythingLLM is reachable and the API key works.")


def query_workspace(config, question):
    if not question.strip():
        raise ValueError("Question cannot be empty.")

    path = f"/api/v1/workspace/{config['workspace']}/chat"
    response = request_anythingllm(
        config,
        "POST",
        path,
        json={"message": question, "mode": "query"},
    )
    if response.status_code != 200:
        raise RuntimeError(f"Workspace query failed with status {response.status_code}: {response.text[:300]}")

    data = response.json()
    sources = []
    for source in data.get("sources", []):
        sources.append(source.get("title") or source.get("source") or source.get("filename", "unknown"))
    return data.get("textResponse", ""), sources


def get_chat_history(config, limit=5):
    path = f"/api/v1/workspace/{config['workspace']}/chats"
    response = request_anythingllm(config, "GET", path, params={"limit": limit})
    if response.status_code != 200:
        print(f"Chat history request failed with status {response.status_code}.")
        return []

    data = response.json()
    raw_chats = data.get("chats", data) if isinstance(data, dict) else data
    history = []
    for entry in raw_chats:
        if isinstance(entry, dict):
            role = entry.get("role")
            content = entry.get("content") or entry.get("message")
            if role and content:
                history.append({"role": role, "content": content})
    return history


def print_result(answer, sources):
    print("\nAnswer:")
    print(answer or "No answer returned.")
    if not sources:
        print("\nNo source citations returned.")
        return

    print("\nSources:")
    for source in sources:
        print(f"  - {source}")


def main():
    config = load_config()
    print(f"Active workspace: {config['workspace']}")
    check_health(config)

    question = "What is NosisTech's data handling policy?"
    print(f"\nQuerying workspace: {question}")
    answer, sources = query_workspace(config, question)
    print_result(answer, sources)

    print("\nLast 5 chat exchanges:")
    for entry in get_chat_history(config, limit=5):
        content = entry["content"]
        preview = content[:200] + "..." if len(content) > 200 else content
        print(f"  [{entry['role']}]: {preview}")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError) as error:
        print(error)
        sys.exit(1)
