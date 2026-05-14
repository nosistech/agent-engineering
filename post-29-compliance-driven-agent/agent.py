# MIT License, Copyright 2025 Packt

import ast
import os
import re
import time
from pathlib import Path

import requests
import yaml
from dotenv import load_dotenv


REQUIRED_ENV = ("LITELLM_BASE_URL", "MODEL_NAME", "LITELLM_API_KEY")
RULES_FILE = Path(__file__).with_name("rules.yaml")
MAX_REQUIREMENT_LENGTH = 2500
MAX_ATTEMPTS = 3


def fail(message: str) -> None:
    raise SystemExit(message)


def load_environment() -> dict:
    load_dotenv()
    missing = [name for name in REQUIRED_ENV if not os.getenv(name)]
    if missing:
        fail("Missing required environment variables: " + ", ".join(missing))
    print(f"Active model: {os.environ['MODEL_NAME']}")
    return {key: os.environ[key] for key in REQUIRED_ENV}


def call_model(prompt: str, config: dict) -> str:
    payload = {"model": config["MODEL_NAME"], "messages": [{"role": "user", "content": prompt}]}
    url = config["LITELLM_BASE_URL"].rstrip("/") + "/v1/chat/completions"
    headers = {"Authorization": f"Bearer {config['LITELLM_API_KEY']}", "Content-Type": "application/json"}

    for attempt in range(MAX_ATTEMPTS):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=120)
            if response.status_code == 429:
                raise RuntimeError("rate limit")
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"].strip()
        except Exception as error:
            if "rate limit" in str(error).lower() and attempt < MAX_ATTEMPTS - 1:
                wait = 2**attempt
                print(f"Rate limit reached. Retrying in {wait} seconds.")
                time.sleep(wait)
                continue
            fail("The AI model service is unavailable. Check the LiteLLM settings and try again.")
    fail("The AI model request could not be completed.")


def extract_code(text: str) -> str:
    match = re.search(r"```(?:python)?\s*(.*?)```", text, re.DOTALL)
    return (match.group(1) if match else text).strip()


def load_rules() -> list[dict]:
    try:
        data = yaml.safe_load(RULES_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail("The compliance rules file is missing.")
    except yaml.YAMLError:
        fail("The compliance rules file is not valid YAML.")

    rules = data.get("rules", []) if isinstance(data, dict) else []
    if not rules:
        fail("The compliance rules file does not contain any rules.")
    return rules


def check_syntax(code: str) -> str:
    try:
        ast.parse(code)
        return ""
    except SyntaxError as error:
        return f"{error.msg} on line {error.lineno or 'unknown'}"


def scan_compliance(code: str, rules: list[dict]) -> list[dict]:
    findings = []
    for line_number, line in enumerate(code.splitlines(), start=1):
        for rule in rules:
            for pattern in rule.get("patterns", []):
                try:
                    matched = re.search(pattern, line, re.IGNORECASE)
                except re.error:
                    fail("A compliance rule contains an invalid pattern.")
                if matched:
                    findings.append(
                        {
                            "rule_id": rule["id"],
                            "description": rule["description"],
                            "severity": rule["severity"],
                            "action": rule["action"],
                            "line": line_number,
                        }
                    )
    return findings


def ask(role: str, requirement: str, config: dict, plan: str = "", tests: str = "", feedback: str = "") -> str:
    prompts = {
        "planner": (
            "Create a short engineering plan for this request. Include inputs, outputs, "
            "edge cases, and acceptance criteria.\n\n"
            f"Request: {requirement}"
        ),
        "tester": (
            "Write minimal pytest-style tests for this request. Return only Python code.\n\n"
            f"Request: {requirement}\n\nPlan:\n{plan}"
        ),
        "developer": (
            "Write the smallest Python implementation that satisfies this request and tests. "
            "Return implementation code only. Do not include tests, pytest imports, markdown, "
            "examples, comments, or explanations. Do not use unnecessary imports or external packages.\n\n"
            f"Request:\n{requirement}\n\nTests:\n{tests}\n\nFeedback from prior attempt:\n{feedback}"
        ),
    }
    answer = call_model(prompts[role], config)
    return extract_code(answer) if role in {"tester", "developer"} else answer


def run_workflow(requirement: str) -> dict:
    config = load_environment()
    rules = load_rules()
    requirement = requirement.strip()
    if not requirement:
        fail("Requirement is empty. Please provide a plain-English software request.")
    if len(requirement) > MAX_REQUIREMENT_LENGTH:
        fail(f"Requirement is too long. Maximum length is {MAX_REQUIREMENT_LENGTH} characters.")

    print("Generating engineering plan.")
    plan = ask("planner", requirement, config)
    print("Generating test cases.")
    tests = ask("tester", requirement, config, plan=plan)

    feedback = "No prior attempt."
    code = syntax_error = ""
    findings = []

    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"Developer attempt {attempt}.")
        code = ask("developer", requirement, config, tests=tests, feedback=feedback)
        syntax_error = check_syntax(code)
        if syntax_error:
            feedback = f"Syntax failed: {syntax_error}"
            continue
        findings = scan_compliance(code, rules)
        if any(finding["action"] in {"rewrite", "block"} for finding in findings):
            rule_ids = ", ".join(finding["rule_id"] for finding in findings)
            feedback = f"Compliance failed. Avoid these rule patterns: {rule_ids}"
            continue
        break

    return {
        "requirement": requirement,
        "attempts": attempt,
        "syntax_error": syntax_error,
        "findings": findings,
        "code": code,
    }


def print_summary(result: dict) -> None:
    print("\n=== Final Results ===")
    print(f"Requirement: {result['requirement']}")
    print(f"Attempts: {result['attempts']}")
    print(f"Syntax valid: {not bool(result['syntax_error'])}")
    if result["syntax_error"]:
        print(f"Syntax error: {result['syntax_error']}")

    print(f"Compliance findings: {len(result['findings'])}")
    for finding in result["findings"]:
        print(f"  - {finding['rule_id']} on line {finding['line']}: {finding['description']} [{finding['action']}]")

    if result["code"]:
        print("\nGenerated code:")
        print(result["code"])


def main() -> None:
    requirement = (
        "Create a Python function named factorial that takes an integer and returns its factorial. "
        "Handle invalid inputs by raising a ValueError."
    )
    print_summary(run_workflow(requirement))


if __name__ == "__main__":
    main()
