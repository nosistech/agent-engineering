# MIT License, Copyright 2025 Packt

import ast
import os
import re
import sys
import time
from pathlib import Path

import requests
import yaml
from dotenv import load_dotenv


REQUIRED_ENV_VARS = ["LITELLM_BASE_URL", "MODEL_NAME", "LITELLM_API_KEY"]
RULES_FILE = Path(__file__).with_name("rules.yaml")
MAX_REQUIREMENT_LENGTH = 2500
MAX_ATTEMPTS = 3


def load_environment() -> dict:
    """Load .env and validate required LiteLLM proxy settings."""
    load_dotenv()
    missing = [name for name in REQUIRED_ENV_VARS if not os.getenv(name)]
    if missing:
        print("Missing required environment variables: " + ", ".join(missing))
        sys.exit(1)

    print(f"Active model: {os.environ['MODEL_NAME']}")
    return {
        "base_url": os.environ["LITELLM_BASE_URL"],
        "model": os.environ["MODEL_NAME"],
        "api_key": os.environ["LITELLM_API_KEY"],
    }


def call_model(prompt: str, config: dict) -> str:
    """Send one prompt to the configured model through the LiteLLM proxy."""
    payload = {"model": config["model"], "messages": [{"role": "user", "content": prompt}]}

    for attempt in range(MAX_ATTEMPTS):
        try:
            response = requests.post(
                f"{config['base_url'].rstrip('/')}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {config['api_key']}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=120,
            )
            if response.status_code == 429:
                raise RuntimeError("rate limit")
            if response.status_code >= 400:
                raise RuntimeError("model request failed")
            return response.json()["choices"][0]["message"]["content"].strip()
        except Exception as error:
            is_rate_limit = "rate limit" in str(error).lower() or "429" in str(error)
            if is_rate_limit and attempt < MAX_ATTEMPTS - 1:
                wait_seconds = 2 ** attempt
                print(f"Rate limit reached. Retrying in {wait_seconds} seconds.")
                time.sleep(wait_seconds)
                continue

            print("The AI model service is unavailable. Check the LiteLLM settings and try again.")
            sys.exit(1)

    print("The AI model request could not be completed.")
    sys.exit(1)


def validate_requirement(requirement: str) -> str:
    """Validate the software request before any model call."""
    cleaned = requirement.strip()
    if not cleaned:
        print("Requirement is empty. Please provide a plain-English software request.")
        sys.exit(1)
    if len(cleaned) > MAX_REQUIREMENT_LENGTH:
        print(f"Requirement is too long. Maximum length is {MAX_REQUIREMENT_LENGTH} characters.")
        sys.exit(1)
    return cleaned


def extract_code(text: str) -> str:
    """Extract Python code from a fenced model response."""
    match = re.search(r"```(?:python)?\s*(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


def load_rules() -> list[dict]:
    """Load compliance rules from rules.yaml."""
    try:
        rules_data = yaml.safe_load(RULES_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print("The compliance rules file is missing.")
        sys.exit(1)
    except yaml.YAMLError:
        print("The compliance rules file is not valid YAML.")
        sys.exit(1)

    rules = rules_data.get("rules", []) if isinstance(rules_data, dict) else []
    if not rules:
        print("The compliance rules file does not contain any rules.")
        sys.exit(1)
    return rules


def check_syntax(code: str) -> str:
    """Return a syntax error message, or an empty string if code is valid."""
    try:
        ast.parse(code)
        return ""
    except SyntaxError as error:
        return f"{error.msg} on line {error.lineno or 'unknown'}"


def scan_compliance(code: str, rules: list[dict]) -> list[dict]:
    """Scan generated code against compliance rules."""
    findings = []
    for line_number, line in enumerate(code.splitlines(), start=1):
        for rule in rules:
            for pattern in rule.get("patterns", []):
                try:
                    matched = re.search(pattern, line, re.IGNORECASE)
                except re.error:
                    print("A compliance rule contains an invalid pattern.")
                    sys.exit(1)

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


def needs_rewrite(findings: list[dict]) -> bool:
    """Return whether compliance findings require another developer attempt."""
    return any(finding["action"] in ("rewrite", "block") for finding in findings)


def build_plan(requirement: str, config: dict) -> str:
    """Ask the planner model call for a short engineering plan."""
    prompt = (
        "Create a short engineering plan for this request. Include inputs, outputs, "
        "edge cases, and acceptance criteria.\n\n"
        f"Request: {requirement}"
    )
    return call_model(prompt, config)


def build_tests(requirement: str, plan: str, config: dict) -> str:
    """Ask the tester model call for pytest-style tests."""
    prompt = (
        "Write minimal pytest-style tests for this request. Return only Python code.\n\n"
        f"Request: {requirement}\n\nPlan:\n{plan}"
    )
    return extract_code(call_model(prompt, config))


def build_code(requirement: str, tests: str, feedback: str, config: dict) -> str:
    """Ask the developer model call for a small Python implementation."""
    prompt = (
        "Write the smallest Python implementation that satisfies this request and tests. "
        "Return implementation code only. Do not include tests, pytest imports, markdown, "
        "examples, comments, or explanations. Do not use unnecessary imports or external packages.\n\n"
        f"Request:\n{requirement}\n\nTests:\n{tests}\n\nFeedback from prior attempt:\n{feedback}"
    )
    return extract_code(call_model(prompt, config))


def run_workflow(requirement: str) -> dict:
    """Run planner, tester, developer, syntax review, and compliance review."""
    config = load_environment()
    rules = load_rules()
    clean_requirement = validate_requirement(requirement)

    print("Generating engineering plan.")
    plan = build_plan(clean_requirement, config)

    print("Generating test cases.")
    tests = build_tests(clean_requirement, plan, config)

    feedback = "No prior attempt."
    code = ""
    syntax_error = ""
    findings = []
    attempts = 0

    while attempts < MAX_ATTEMPTS:
        attempts += 1
        print(f"Developer attempt {attempts}.")
        code = build_code(clean_requirement, tests, feedback, config)

        syntax_error = check_syntax(code)
        if syntax_error:
            feedback = f"Syntax failed: {syntax_error}"
            continue

        findings = scan_compliance(code, rules)
        if needs_rewrite(findings):
            rule_ids = ", ".join(finding["rule_id"] for finding in findings)
            feedback = f"Compliance failed. Avoid these rule patterns: {rule_ids}"
            continue

        break

    return {
        "requirement": clean_requirement,
        "attempts": attempts,
        "syntax_error": syntax_error,
        "findings": findings,
        "code": code,
    }


def print_summary(result: dict) -> None:
    """Print the final workflow summary without exposing configuration values."""
    print("\n=== Final Results ===")
    print(f"Requirement: {result['requirement']}")
    print(f"Attempts: {result['attempts']}")
    print(f"Syntax valid: {not bool(result['syntax_error'])}")
    if result["syntax_error"]:
        print(f"Syntax error: {result['syntax_error']}")

    print(f"Compliance findings: {len(result['findings'])}")
    for finding in result["findings"]:
        print(
            f"  - {finding['rule_id']} on line {finding['line']}: "
            f"{finding['description']} [{finding['action']}]"
        )

    if result["code"]:
        print("\nGenerated code:")
        print(result["code"])


def main() -> None:
    """Run the demo workflow."""
    demo_requirement = (
        "Create a Python function named factorial that takes an integer and returns its factorial. "
        "Handle invalid inputs by raising a ValueError."
    )
    result = run_workflow(demo_requirement)
    print_summary(result)


if __name__ == "__main__":
    main()
