# MIT License, Copyright 2025 Packt

import json
import os
import sys
import time
from collections import deque

from dotenv import load_dotenv
from openai import APIConnectionError, OpenAI, OpenAIError, RateLimitError

load_dotenv()


def require_config():
    required = ["LITELLM_BASE_URL", "MODEL_NAME", "LITELLM_API_KEY", "GOAL"]
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise SystemExit("Missing required environment variables: " + ", ".join(missing))
    if len(os.getenv("GOAL")) > 1000:
        raise SystemExit("The GOAL exceeds 1000 characters. Please shorten it.")


def ask_model(client, model, goal):
    messages = [
        {
            "role": "system",
            "content": (
                "Break the goal into dependency-aware tasks. Return only JSON. "
                "Use an array of objects with task and depends_on fields. "
                "Every depends_on value must exactly match another task field in the array."
            ),
        },
        {"role": "user", "content": f"Goal: {goal}"},
    ]
    for attempt in range(1, 4):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0,
            )
            return response.choices[0].message.content
        except RateLimitError:
            wait = 2 ** attempt
            print(f"Rate limit hit. Retrying in {wait} seconds.")
            time.sleep(wait)
        except APIConnectionError as error:
            raise RuntimeError("Cannot reach LiteLLM. Check the proxy.") from error
        except OpenAIError as error:
            raise RuntimeError(f"LiteLLM request failed: {error}") from error
    raise RuntimeError("Failed after multiple rate-limit retries.")


def parse_tasks(raw_text):
    text = raw_text.strip()
    if text.startswith("```"):
        text = "\n".join(text.splitlines()[1:])
    if text.endswith("```"):
        text = "\n".join(text.splitlines()[:-1])

    tasks = json.loads(text.strip())
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("Plan must be a non-empty JSON array.")
    for item in tasks:
        if not isinstance(item, dict) or not isinstance(item.get("task"), str) or not isinstance(item.get("depends_on"), list):
            raise ValueError("Each item must include task and depends_on.")
    return tasks


def order_tasks(tasks):
    names = {item["task"] for item in tasks}
    graph = {name: [] for name in names}
    in_degree = {name: 0 for name in names}

    for item in tasks:
        for dependency in item["depends_on"]:
            if dependency not in names:
                raise ValueError(f"Undefined dependency: {dependency}")
            graph[dependency].append(item["task"])
            in_degree[item["task"]] += 1

    ready = deque([task for task, count in in_degree.items() if count == 0])
    ordered = []
    while ready:
        task = ready.popleft()
        ordered.append(task)
        for next_task in graph[task]:
            in_degree[next_task] -= 1
            if in_degree[next_task] == 0:
                ready.append(next_task)

    if len(ordered) != len(tasks):
        raise ValueError("Cycle detected in task dependencies.")
    return ordered


def main():
    require_config()
    model = os.getenv("MODEL_NAME")
    goal = os.getenv("GOAL")
    print(f"Active model: {model}")
    print(f"Goal: {goal}")

    client = OpenAI(
        base_url=os.getenv("LITELLM_BASE_URL"),
        api_key=os.getenv("LITELLM_API_KEY"),
        timeout=60,
    )
    tasks = parse_tasks(ask_model(client, model, goal))
    ordered = order_tasks(tasks)

    print("\nExecution order:")
    for index, task in enumerate(ordered, start=1):
        print(f"{index}. {task}")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, json.JSONDecodeError) as error:
        print(error)
        sys.exit(1)
