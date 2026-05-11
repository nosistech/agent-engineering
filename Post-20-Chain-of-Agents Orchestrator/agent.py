# MIT License, Copyright 2025 Packt
import os
import sys
import json
import time
import re
from datetime import datetime, timezone

import dotenv
from openai import OpenAI


def check_env_vars(required_vars):
    """Verify all required environment variables are set, exit if any missing."""
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        print("Missing required environment variables:")
        for var in missing:
            print(f"  - {var}")
        sys.exit(1)


def get_target(default_target):
    """Return the target string from CLI argument or the default, with validation."""
    if len(sys.argv) > 1:
        target = sys.argv[1]
    else:
        target = default_target
    target = target.strip()
    if not target:
        print("Target must not be empty.")
        sys.exit(1)
    if len(target) > 200:
        print("Target must be 200 characters or fewer.")
        sys.exit(1)
    return target


def run_specialist_agent(agent_name, task, target, client, model_name):
    """Send research task to LiteLLM for a specialist agent, with retries. Returns finding or empty string."""
    prompt = (
        f"You are a market intelligence specialist agent named '{agent_name}'. "
        f"Research the following about {target}: {task}. "
        "Provide your findings as a concise, plain-English paragraph."
    )
    delay = 1
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            finding = response.choices[0].message.content.strip()
            return finding
        except Exception as e:
            error_type = type(e).__name__
            if "RateLimitError" in error_type or (hasattr(e, "status_code") and e.status_code == 429):
                if attempt < 2:
                    time.sleep(delay)
                    delay *= 2
                    continue
                else:
                    print(f"Rate limit exceeded for {agent_name} after 3 attempts. Skipping.")
                    return ""
            elif "APIConnectionError" in error_type or "ConnectionError" in error_type:
                print("Cannot reach the AI service. Check that LiteLLM is running at the configured base URL.")
                sys.exit(1)
            else:
                print(f"Error during {agent_name} research: {e}. Skipping this agent.")
                return ""
    return ""


def write_to_memory(agent_name, task, finding, memory_log_path):
    """Append a JSON line with agent finding to the memory log file."""
    os.makedirs(os.path.dirname(memory_log_path), exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": agent_name,
        "task": task,
        "finding": finding,
    }
    with open(memory_log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def read_memory(memory_log_path):
    """Read all lines from memory log and return list of dicts. Returns empty list if file missing."""
    if not os.path.exists(memory_log_path):
        return []
    entries = []
    with open(memory_log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return entries


def detect_conflict(findings_list, client, model_name, conflict_threshold):
    """Assess contradictions among findings. Returns conflict_detected, score, explanation."""
    combined = "\n\n".join(
        f"Agent: {f['agent']}\nFinding: {f['finding']}" for f in findings_list
    )
    prompt = (
        "You are an impartial conflict detector. Below are three findings from different analysts "
        "about the same target. Score the level of factual contradiction among them on a scale of 0.0 "
        "(no contradiction) to 1.0 (completely contradictory). Provide the score as a number "
        "on a line by itself, and then a one-paragraph explanation of what specifically conflicts. "
        "If the score is above 0.5, mention the conflict clearly. If it is below 0.5, explain why "
        "the findings are largely consistent.\n\n"
        f"{combined}\n\n"
        "Output format:\nScore: 0.X\nExplanation: ..."
    )
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        content = response.choices[0].message.content.strip()
        score_match = re.search(r"Score:\s*([\d.]+)", content, re.IGNORECASE)
        if score_match:
            score = float(score_match.group(1))
            score = max(0.0, min(1.0, score))
        else:
            score = 0.0
        expl_match = re.search(r"Explanation:\s*(.*)", content, re.IGNORECASE | re.DOTALL)
        explanation = expl_match.group(1).strip() if expl_match else "No explanation parsed."
        conflict_detected = score >= conflict_threshold
        return conflict_detected, score, explanation
    except Exception as e:
        print(f"Conflict analysis failed: {e}. Reporting no conflict.")
        return False, 0.0, "Conflict analysis unavailable."


def run_manager_agent(memory_entries, conflict_detected, conflict_explanation, client, model_name):
    """Synthesize findings into a plain-English intelligence report."""
    findings_text = "\n".join(
        f"- {entry['agent']} ({entry['task']}): {entry['finding']}" for entry in memory_entries
    )
    conflict_instruction = ""
    if conflict_detected:
        conflict_instruction = (
            f"\n\nIMPORTANT: The specialist findings contain a notable conflict "
            f"(explanation: {conflict_explanation}). "
            "Your report must explicitly include this conflict in a clearly labeled section, "
            "without resolving or hiding it."
        )
    prompt = (
        "You are the Manager intelligence analyst. Synthesize the following findings from "
        "three specialist agents into a single, concise market intelligence report "
        "for the target.{conflict_instruction}\n\n"
        f"{findings_text}\n\n"
        "Provide a plain-English report with an Executive Summary section."
    ).format(conflict_instruction=conflict_instruction)

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
        )
        report = response.choices[0].message.content.strip()
        return report
    except Exception as e:
        return f"Manager agent report generation failed: {e}"


def main():
    """Orchestrate multi-agent market intelligence pipeline."""
    dotenv.load_dotenv()

    required_vars = [
        "LITELLM_BASE_URL",
        "MODEL_NAME",
        "LITELLM_API_KEY",
        "MEMORY_LOG_PATH",
        "CONFLICT_THRESHOLD",
        "DEFAULT_TARGET",
    ]
    check_env_vars(required_vars)

    base_url = os.getenv("LITELLM_BASE_URL")
    model_name = os.getenv("MODEL_NAME")
    api_key = os.getenv("LITELLM_API_KEY")
    memory_log_path = os.getenv("MEMORY_LOG_PATH")
    conflict_threshold = float(os.getenv("CONFLICT_THRESHOLD"))
    default_target = os.getenv("DEFAULT_TARGET")

    print(f"Active AI model: {model_name}")

    client = OpenAI(base_url=base_url, api_key=api_key)

    target = get_target(default_target)
    print(f"Target: {target}")

    specialists = [
        ("News Agent", "Summarize recent news headlines about the target"),
        ("Financials Agent", "Summarize key financial indicators or performance metrics for the target"),
        ("Sentiment Agent", "Summarize current public and professional sentiment toward the target"),
    ]

    findings = []
    for agent_name, task in specialists:
        finding = run_specialist_agent(agent_name, task, target, client, model_name)
        if finding:
            findings.append({"agent": agent_name, "task": task, "finding": finding})
            write_to_memory(agent_name, task, finding, memory_log_path)
        else:
            placeholder = "No finding obtained due to an error."
            findings.append({"agent": agent_name, "task": task, "finding": placeholder})
            write_to_memory(agent_name, task, placeholder, memory_log_path)


    conflict_detected, score, explanation = detect_conflict(
        findings, client, model_name, conflict_threshold
    )

    report = run_manager_agent(findings, conflict_detected, explanation, client, model_name)

    print("\n" + "=" * 60)
    print("MARKET INTELLIGENCE REPORT")
    print("=" * 60)
    print(report)

    if conflict_detected:
        print("\n" + "!" * 40)
        print("CONFLICT WARNING")
        print("!" * 40)
        print(f"Conflict score: {score:.2f} (threshold: {conflict_threshold})")
        print(f"Explanation: {explanation}")
        print("!" * 40)

    print("\nAgent run complete.")


if __name__ == "__main__":
    main()