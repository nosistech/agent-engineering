# MIT License, Copyright 2025 Packt
import os
import json
import time
import logging
import sys
from dotenv import load_dotenv
from openai import OpenAI, RateLimitError, APIConnectionError, OpenAIError

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def check_environment():
    """Verify that all required environment variables are present. Exit cleanly if any are missing."""
    required_vars = [
        "LITELLM_BASE_URL",
        "MODEL_NAME",
        "LITELLM_API_KEY",
        "GOAL",
    ]
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        print("Missing required environment variables. Please set the following in your .env file:")
        for var in missing:
            print(f"  - {var}")
        sys.exit(1)

def setup_llm_client():
    """Create and return an OpenAI client pointed at the LiteLLM proxy."""
    return OpenAI(
        base_url=os.getenv("LITELLM_BASE_URL"),
        api_key=os.getenv("LITELLM_API_KEY"),
    )

def call_with_backoff(client, model, messages):
    """
    Send a chat completion request to LiteLLM with rate-limit handling.
    Retries with exponential backoff on rate limits; exits on connection errors.
    """
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
            )
            return response
        except RateLimitError:
            wait = 2 ** attempt
            logging.warning("Rate limit hit, retrying in %d seconds (attempt %d/3)", wait, attempt)
            time.sleep(wait)
        except APIConnectionError:
            print("Cannot reach the LiteLLM endpoint. Check that the service is running and LITELLM_BASE_URL is correct.")
            sys.exit(1)
        except OpenAIError as exc:
            logging.error("OpenAI API error: %s", exc)
            sys.exit(1)
    print("Failed after multiple rate-limit retries. Please try again later.")
    sys.exit(1)

def generate_task_plan(client, model, goal):
    """
    Ask the LLM to break the goal into tasks with explicit dependencies.
    Returns a list of dicts, each containing 'task' and 'depends_on'.
    """
    system_prompt = (
        "You are a planning assistant. Break the following high-level goal into a list of smaller "
        "tasks with clear dependencies. Return ONLY a JSON array. Each element must be an object "
        "with exactly two fields: 'task' (string, task name) and 'depends_on' (array of strings, "
        "names of tasks that must be completed before this one; empty if none). Do not include any "
        "explanations or markdown formatting."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Goal: {goal}"},
    ]
    response = call_with_backoff(client, model, messages)
    content = response.choices[0].message.content.strip()

    if content.startswith("```"):
        content = "\n".join(content.splitlines()[1:])
    if content.endswith("```"):
        content = "\n".join(content.splitlines()[:-1])
    content = content.strip()

    try:
        task_list = json.loads(content)
        if not isinstance(task_list, list):
            raise ValueError("Response is not a JSON array")
        for item in task_list:
            if not isinstance(item, dict) or "task" not in item or "depends_on" not in item:
                raise ValueError("Task item missing required fields")
        return task_list
    except (json.JSONDecodeError, ValueError) as err:
        print("Failed to parse the LLM's task plan. The model may have returned invalid JSON.")
        print("Try reformulating your goal or switching to a different model.")
        logging.debug("Raw LLM response: %s", content)
        sys.exit(1)

def build_dag(task_list):
    """
    Convert the task list into a dependency graph mapping task name to list of dependencies.
    Validates that every mentioned dependency exists in the task list.
    """
    task_names = {item["task"] for item in task_list}
    dag = {}
    for item in task_list:
        name = item["task"]
        deps = item["depends_on"]
        for dep in deps:
            if dep not in task_names:
                print(f"Error: Task '{name}' depends on '{dep}', but '{dep}' was not defined in the task list.")
                print("The LLM has produced an inconsistent plan. Please try again.")
                sys.exit(1)
        dag[name] = deps
    return dag

def topological_sort(dag):
    """
    Perform a topological sort using Kahn's algorithm.
    Returns an ordered list of task names. Exits if a cycle is detected.
    """
    in_degree = {node: 0 for node in dag}
    for node, deps in dag.items():
        for dep in deps:
            in_degree[node] += 1

    zero_queue = [node for node, degree in in_degree.items() if degree == 0]
    sorted_tasks = []

    while zero_queue:
        current = zero_queue.pop(0)
        sorted_tasks.append(current)
        for node, deps in dag.items():
            if current in deps:
                in_degree[node] -= 1
                if in_degree[node] == 0:
                    zero_queue.append(node)

    if len(sorted_tasks) != len(dag):
        print("Cycle detected in the task dependencies. The LLM's plan contains a circular dependency and cannot be executed.")
        print("Please regenerate the plan with a different goal or model.")
        sys.exit(1)

    return sorted_tasks

def execute_plan(ordered_tasks):
    """Simulate execution of tasks in the given order, with a short artificial delay."""
    for task in ordered_tasks:
        logging.info("Starting task: %s", task)
        time.sleep(1)
        logging.info("Completed task: %s", task)

def main():
    """Entry point: load environment, validate, generate and execute the plan."""
    load_dotenv()
    check_environment()

    model = os.getenv("MODEL_NAME")
    print("Active model: " + model)

    client = setup_llm_client()

    goal = os.getenv("GOAL")
    if not goal:
        goal = "Launch a client onboarding workflow for NosisTech LLC"
        print("No GOAL environment variable set. Using demo goal: " + goal)
    if len(goal) > 1000:
        print("The GOAL exceeds 1000 characters. Please shorten it.")
        sys.exit(1)

    logging.info("Generating task plan for goal.")
    task_list = generate_task_plan(client, model, goal)
    if not task_list:
        print("The LLM returned an empty task list. Exiting.")
        sys.exit(1)

    dag = build_dag(task_list)
    logging.info("DAG constructed with %d tasks", len(dag))

    ordered_tasks = topological_sort(dag)
    logging.info("Execution order determined.")

    execute_plan(ordered_tasks)
    logging.info("All tasks completed successfully.")

if __name__ == "__main__":
    main()