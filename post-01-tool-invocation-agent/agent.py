## MIT License, Copyright 2025 Packt

import csv
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))


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

REQUIRED_VARS = [
    "LITELLM_BASE_URL",
    "MODEL_NAME",
    "LITELLM_API_KEY",
    "DATA_FILE_PATH",
]


def check_environment() -> None:
    missing = [name for name in REQUIRED_VARS if not os.getenv(name)]
    if missing:
        print(f"[ERROR] Missing environment variables: {', '.join(missing)}")
        sys.exit(1)
    print(f"[INFO] Active model: {os.getenv('MODEL_NAME')}")


def call_llm(messages: list[dict[str, str]]) -> str:
    base_url = os.getenv("LITELLM_BASE_URL", "").rstrip("/")
    payload = json.dumps(
        {
            "model": os.getenv("MODEL_NAME"),
            "messages": messages,
            "temperature": 0,
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


def read_campaign_rows() -> list[dict[str, str]]:
    data_path = os.getenv("DATA_FILE_PATH")
    if data_path and not os.path.isabs(data_path):
        data_path = os.path.join(PROJECT_DIR, data_path)
    with open(data_path, newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def spend_by_campaign() -> dict[str, float]:
    totals: dict[str, float] = {}
    for row in read_campaign_rows():
        campaign = row["campaign_name"]
        totals[campaign] = totals.get(campaign, 0.0) + float(row["spend"])
    return totals


def clicks_by_month() -> dict[str, int]:
    totals: dict[str, int] = {}
    for row in read_campaign_rows():
        month = row["date"][:7]
        totals[month] = totals.get(month, 0) + int(row["clicks"])
    return totals


TOOLS = {
    "spend_by_campaign": spend_by_campaign,
    "clicks_by_month": clicks_by_month,
}


def choose_tool(user_request: str) -> str:
    tool_list = "\n".join(f"- {name}" for name in TOOLS)
    messages = [
        {
            "role": "system",
            "content": (
                "You route user requests to exactly one tool. "
                "Return only JSON in this format: {\"tool\": \"tool_name\"}. "
                "If none of the tools fit, return {\"tool\": \"none\"}."
            ),
        },
        {
            "role": "user",
            "content": f"Available tools:\n{tool_list}\n\nUser request: {user_request}",
        },
    ]
    raw_response = call_llm(messages)
    cleaned = raw_response.strip().removeprefix("```json").removeprefix("```").strip("`").strip()

    try:
        selected = json.loads(cleaned).get("tool", "none")
    except json.JSONDecodeError:
        selected = "none"

    if selected not in TOOLS:
        return "none"
    return selected


def run_agent(user_request: str) -> None:
    print(f"[USER] {user_request}")
    tool_name = choose_tool(user_request)

    if tool_name == "none":
        print("[AGENT] I do not have a tool for that request.")
        return

    print(f"[AGENT] Selected tool: {tool_name}")
    result = TOOLS[tool_name]()
    print("[TOOL RESULT]")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    check_environment()
    request = " ".join(sys.argv[1:]) or "Show me spend by campaign"
    run_agent(request)
