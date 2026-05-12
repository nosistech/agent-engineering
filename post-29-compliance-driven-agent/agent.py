# MIT License, Copyright 2025 Packt

import ast
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import requests
import yaml
from dotenv import load_dotenv


REQUIRED_ENV_VARS = ["LITELLM_BASE_URL", "MODEL_NAME", "LITELLM_API_KEY"]
RULES_FILE = Path(__file__).with_name("rules.yaml")
MAX_REQUIREMENT_LENGTH = 2500
MAX_DEVELOPER_ATTEMPTS = 3


@dataclass
class EngineeringState:
    """Store the workflow state shared by each agent stage."""

    requirement: str = ""
    plan: str = ""
    tests: str = ""
    code: str = ""
    compliance_findings: list[dict] = field(default_factory=list)
    attempts: int = 0
    syntax_error: str = ""
    final_report: str = ""
    self_improvement_notes: list[str] = field(default_factory=list)


def load_environment() -> dict:
    """Load .env and validate required LiteLLM variables."""
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


def call_model(prompt: str, config: dict, system_prompt: str = "") -> str:
    """Send a prompt to the configured model through LiteLLM."""
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    for attempt in range(MAX_DEVELOPER_ATTEMPTS):
        try:
            response = requests.post(
                f"{config['base_url'].rstrip('/')}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {config['api_key']}",
                    "Content-Type": "application/json",
                },
                json={"model": config["model"], "messages": messages},
                timeout=120,
            )
            if response.status_code == 429:
                raise RuntimeError("rate limit")
            if response.status_code >= 400:
                raise RuntimeError("model request failed")
            return response.json()["choices"][0]["message"]["content"].strip()
        except Exception as error:
            message = str(error).lower()
            is_rate_limit = "rate limit" in message or "429" in message
            if is_rate_limit and attempt < MAX_DEVELOPER_ATTEMPTS - 1:
                wait_seconds = 2 ** attempt
                print(f"Rate limit reached. Retrying in {wait_seconds} seconds.")
                time.sleep(wait_seconds)
                continue
            if is_rate_limit:
                print("The AI model service is rate limiting requests. Please try again later.")
                sys.exit(1)

            print("The AI model service is unavailable. Check the LiteLLM settings and try again.")
            sys.exit(1)

    print("The AI model request could not be completed.")
    sys.exit(1)


def validate_requirement(requirement: str) -> str:
    """Validate the software requirement before any model call."""
    cleaned = requirement.strip()
    if not cleaned:
        print("Requirement is empty. Please provide a plain-English software requirement.")
        sys.exit(1)
    if len(cleaned) > MAX_REQUIREMENT_LENGTH:
        print(f"Requirement is too long. Maximum length is {MAX_REQUIREMENT_LENGTH} characters.")
        sys.exit(1)
    return cleaned


def extract_code(text: str) -> str:
    """Extract Python code from a fenced code block or return the raw text."""
    match = re.search(r"```(?:python)?\s*(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


def generate_plan(state: EngineeringState, config: dict) -> None:
    """Generate an engineering plan from the requirement."""
    prompt = (
        "Create a short engineering plan for this requirement. "
        "Include inputs, outputs, edge cases, and acceptance criteria.\n\n"
        f"Requirement: {state.requirement}"
    )
    system_prompt = "You are a senior software architect. Respond with plain text only."
    state.plan = call_model(prompt, config, system_prompt)


def generate_tests(state: EngineeringState, config: dict) -> None:
    """Generate pytest-style tests for the requirement."""
    prompt = (
        "Write a minimal pytest-style test suite for this software requirement. "
        "Return only Python code.\n\n"
        f"Requirement: {state.requirement}\n\nPlan:\n{state.plan}"
    )
    system_prompt = "You write clean, minimal test code. Do not include explanations."
    state.tests = extract_code(call_model(prompt, config, system_prompt))


def generate_code(state: EngineeringState, config: dict) -> str:
    """Generate a minimal Python implementation for the tests."""
    notes = "\n".join(state.self_improvement_notes) if state.self_improvement_notes else "None."
    prompt = (
        "Write the smallest Python implementation that satisfies the requirement and tests. "
        "Return only Python code. Do not use unnecessary imports or external packages.\n\n"
        f"Requirement:\n{state.requirement}\n\n"
        f"Tests:\n{state.tests}\n\n"
        f"Previous improvement notes:\n{notes}"
    )
    system_prompt = "You write minimal, clean Python code with no explanations."
    return extract_code(call_model(prompt, config, system_prompt))


def syntax_check(code: str) -> str:
    """Return a syntax error message, or an empty string if code is valid."""
    try:
        ast.parse(code)
        return ""
    except SyntaxError as error:
        line_number = error.lineno or "unknown"
        return f"{error.msg} on line {line_number}"


def load_rules() -> list[dict]:
    """Load compliance rules from rules.yaml beside this file."""
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


def compliance_scan(code: str, rules: list[dict]) -> list[dict]:
    """Scan generated code against compliance rules."""
    findings = []
    lines = code.splitlines()
    for rule in rules:
        for pattern in rule.get("patterns", []):
            try:
                compiled_pattern = re.compile(pattern, re.IGNORECASE)
            except re.error:
                print("A compliance rule contains an invalid pattern.")
                sys.exit(1)

            for line_number, line in enumerate(lines, start=1):
                if compiled_pattern.search(line):
                    findings.append(
                        {
                            "rule_id": rule["id"],
                            "description": rule["description"],
                            "severity": rule["severity"],
                            "action": rule["action"],
                            "line": line_number,
                            "match": line.strip(),
                        }
                    )
    return findings


def has_blocking_findings(findings: list[dict]) -> bool:
    """Return whether findings require a developer rewrite."""
    return any(finding["action"] in ("rewrite", "block") for finding in findings)


def generate_integration_report(state: EngineeringState, config: dict) -> None:
    """Generate a short release note for the reviewed code."""
    prompt = (
        "Write a short release note for this generated Python code. "
        "State that this is a demo static review, not production approval, "
        "legal advice, or security certification. Mention the syntax check "
        "and compliance scan result.\n\n"
        f"Requirement:\n{state.requirement}\n\nCode:\n{state.code}"
    )
    system_prompt = "You write concise release notes for internal engineering demos."
    state.final_report = call_model(prompt, config, system_prompt)


def add_self_improvement_notes(state: EngineeringState) -> None:
    """Record why the developer stage needs another attempt."""
    if state.syntax_error:
        state.self_improvement_notes.append(
            "Syntax failed. Generate shorter code and check Python syntax before final output."
        )
    if has_blocking_findings(state.compliance_findings):
        rule_ids = [
            finding["rule_id"]
            for finding in state.compliance_findings
            if finding["action"] in ("rewrite", "block")
        ]
        state.self_improvement_notes.append(
            "Compliance failed. Avoid these rule patterns: " + ", ".join(rule_ids)
        )


def run_workflow(requirement: str) -> EngineeringState:
    """Run the planning, testing, development, compliance, and integration workflow."""
    config = load_environment()
    rules = load_rules()
    state = EngineeringState(requirement=validate_requirement(requirement))

    print("Generating engineering plan.")
    generate_plan(state, config)
    print("Generating test cases.")
    generate_tests(state, config)

    while state.attempts < MAX_DEVELOPER_ATTEMPTS:
        state.attempts += 1
        print(f"Developer attempt {state.attempts}.")

        state.code = generate_code(state, config)
        state.syntax_error = syntax_check(state.code)
        if state.syntax_error:
            print("Syntax issue detected. Retrying.")
            add_self_improvement_notes(state)
            continue

        state.compliance_findings = compliance_scan(state.code, rules)
        if has_blocking_findings(state.compliance_findings):
            print("Blocking compliance issue detected. Retrying.")
            add_self_improvement_notes(state)
            continue

        break

    if state.code and not state.syntax_error and not has_blocking_findings(state.compliance_findings):
        print("Generating integration report.")
        generate_integration_report(state, config)
    else:
        state.final_report = "No integration report was generated because the code did not pass review."

    return state


def print_summary(state: EngineeringState) -> None:
    """Print the final workflow summary without exposing configuration values."""
    print("\n=== Final Results ===")
    print(f"Requirement: {state.requirement}")
    print(f"Attempts: {state.attempts}")
    print(f"Syntax valid: {not bool(state.syntax_error)}")
    if state.syntax_error:
        print(f"Syntax error: {state.syntax_error}")

    print(f"Compliance findings: {len(state.compliance_findings)}")
    for finding in state.compliance_findings:
        print(
            f"  - {finding['rule_id']} on line {finding['line']}: "
            f"{finding['description']} [{finding['action']}]"
        )

    if state.self_improvement_notes:
        print("Self-improvement notes:")
        for note in state.self_improvement_notes:
            print(f"  - {note}")

    print(f"\nFinal report: {state.final_report}")
    if state.code:
        print("\nGenerated code:")
        print(state.code)


def main() -> None:
    """Run the demo software engineering workflow."""
    demo_requirement = (
        "Create a Python function named factorial that takes an integer and returns its factorial. "
        "Handle invalid inputs by raising a ValueError."
    )
    state = run_workflow(demo_requirement)
    print_summary(state)


if __name__ == "__main__":
    main()
