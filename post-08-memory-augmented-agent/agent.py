# MIT License, Copyright 2025 Packt

import json
import os
import re
import sys
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def load_env_file(path: str = ".env") -> None:
    if not os.path.exists(path):
        return

    with open(path, encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


load_env_file(os.path.join(PROJECT_DIR, ".env"))

REQUIRED_ENV_VARS = [
    "LITELLM_BASE_URL",
    "MODEL_NAME",
    "LITELLM_API_KEY",
]


def safe_print(text: str) -> None:
    print(text)


def memory_path() -> str:
    path = os.getenv("MEMORY_FILE_PATH", "memory.json")
    if not os.path.isabs(path):
        path = os.path.join(PROJECT_DIR, path)
    return path


def check_environment() -> None:
    missing = [name for name in REQUIRED_ENV_VARS if not os.getenv(name)]
    if missing:
        safe_print(f"[ERROR] Missing environment variables: {', '.join(missing)}")
        sys.exit(1)
    safe_print(f"[INFO] Active model: {os.getenv('MODEL_NAME')}")


def call_llm(messages: list[dict[str, str]]) -> str:
    base_url = os.getenv("LITELLM_BASE_URL", "").rstrip("/")
    payload = json.dumps(
        {
            "model": os.getenv("MODEL_NAME"),
            "messages": messages,
            "temperature": 0.3,
        }
    ).encode("utf-8")

    request = Request(
        f"{base_url}/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {os.getenv('LITELLM_API_KEY')}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=60) as response:
            body = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"LiteLLM returned HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Could not reach LiteLLM at {base_url}: {exc}") from exc

    return body["choices"][0]["message"]["content"].strip()


def load_memory() -> list[dict[str, str]]:
    path = memory_path()
    if not os.path.exists(path):
        return []

    with open(path, encoding="utf-8") as file:
        return json.load(file)


def save_memory(records: list[dict[str, str]]) -> None:
    path = memory_path()
    with open(path, "w", encoding="utf-8") as file:
        json.dump(records, file, indent=2)


def words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def find_relevant_memory(user_input: str, records: list[dict[str, str]]) -> dict[str, str] | None:
    query_words = words(user_input)
    best_record = None
    best_score = 0

    for record in records:
        memory_text = record["user_input"] + " " + record["agent_response"]
        score = len(query_words & words(memory_text))
        if score > best_score:
            best_score = score
            best_record = record

    if best_score == 0:
        return None
    return best_record


def answer_with_memory(user_input: str) -> str:
    records = load_memory()
    relevant_memory = find_relevant_memory(user_input, records)

    if relevant_memory:
        memory_context = (
            f"Relevant previous interaction:\n"
            f"User: {relevant_memory['user_input']}\n"
            f"Assistant: {relevant_memory['agent_response']}"
        )
    else:
        memory_context = "No relevant previous interaction found."

    messages = [
        {
            "role": "system",
            "content": (
                "You are a practical business assistant for NosisTech LLC. "
                "Use the memory context when it is relevant. "
                "If the user states a preference or fact, acknowledge it clearly. "
                "Do not claim you completed external actions."
            ),
        },
        {"role": "system", "content": memory_context},
        {"role": "user", "content": user_input},
    ]
    agent_response = call_llm(messages)

    records.append(
        {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "user_input": user_input,
            "agent_response": agent_response,
        }
    )
    save_memory(records)
    return agent_response


def run_turn(user_input: str) -> None:
    safe_print(f"[USER] {user_input}")
    response = answer_with_memory(user_input)
    safe_print(f"[AGENT] {response}\n")


def main() -> None:
    check_environment()

    if len(sys.argv) > 1:
        run_turn(" ".join(sys.argv[1:]))
        return

    run_turn("Remember that Apex Dynamics prefers Friday status updates.")
    run_turn("How should I schedule Apex Dynamics updates?")


if __name__ == "__main__":
    main()
