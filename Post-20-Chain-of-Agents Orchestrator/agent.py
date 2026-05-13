# MIT License, Copyright 2025 Packt

import json
import os
import sys
from datetime import datetime, timezone
from urllib.request import Request, urlopen


PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

SPECIALISTS = [
    ("News Agent", "recent news and public updates"),
    ("Financials Agent", "financial performance and business signals"),
    ("Sentiment Agent", "public and professional sentiment"),
]


def load_env() -> None:
    path = os.path.join(PROJECT_DIR, ".env")
    if not os.path.exists(path):
        return
    for line in open(path, encoding="utf-8"):
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.strip().split("=", 1)
            os.environ.setdefault(key, value)


def require_env() -> None:
    missing = [key for key in ("LITELLM_BASE_URL", "MODEL_NAME", "LITELLM_API_KEY") if not os.getenv(key)]
    if missing:
        raise SystemExit(f"Missing environment variables: {', '.join(missing)}")
    print(f"[INFO] Active model: {os.getenv('MODEL_NAME')}")


def call_llm(prompt: str, temperature: float = 0.3) -> str:
    payload = json.dumps(
        {
            "model": os.getenv("MODEL_NAME"),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }
    ).encode("utf-8")

    request = Request(
        os.getenv("LITELLM_BASE_URL").rstrip("/") + "/chat/completions",
        data=payload,
        headers={
            "Authorization": "Bearer " + os.getenv("LITELLM_API_KEY"),
            "Content-Type": "application/json",
        },
    )
    with urlopen(request, timeout=90) as response:
        data = json.loads(response.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"].strip()


def journal_path() -> str:
    path = os.getenv("MEMORY_LOG_PATH", "outputs/memory_log.jsonl")
    if os.path.isabs(path):
        return path
    return os.path.join(PROJECT_DIR, path)


def write_journal(target: str, findings: list[dict[str, str]], report: str) -> None:
    path = journal_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "target": target,
        "findings": findings,
        "report": report,
    }
    with open(path, "a", encoding="utf-8") as file:
        file.write(json.dumps(entry) + "\n")


def run_specialist(name: str, focus: str, target: str) -> dict[str, str]:
    prompt = (
        f"You are {name}, one specialist in a chain-of-agents workflow. "
        f"Target: {target}\n"
        f"Focus only on: {focus}.\n"
        "You do not have live browsing or private company data. "
        "Do not invent specific funding rounds, partnerships, metrics, clients, dates, or news. "
        "Return one concise paragraph of cautious analysis and open signals to investigate. "
        "Do not write the final report."
    )
    return {"agent": name, "focus": focus, "finding": call_llm(prompt)}


def run_manager(target: str, findings: list[dict[str, str]]) -> str:
    findings_text = "\n\n".join(
        f"{item['agent']} ({item['focus']}):\n{item['finding']}" for item in findings
    )
    prompt = (
        "You are the manager agent in a chain-of-agents workflow. "
        "Synthesize the specialist findings into one plain-English intelligence report.\n\n"
        f"Target: {target}\n\n"
        f"Specialist findings:\n{findings_text}\n\n"
        "Use short sections: Executive Summary, Key Signals, Open Questions. "
        "Do not turn open questions into asserted facts."
    )
    return call_llm(prompt, temperature=0.4)


def run_chain(target: str) -> None:
    print(f"[TARGET] {target}\n")
    findings = []

    for name, focus in SPECIALISTS:
        print(f"[RUNNING] {name}")
        finding = run_specialist(name, focus, target)
        findings.append(finding)
        print(finding["finding"] + "\n")

    print("=" * 60)
    print("FINAL MANAGER REPORT")
    print("=" * 60)
    report = run_manager(target, findings)
    print(report)
    write_journal(target, findings, report)
    print(f"\n[JOURNAL] Appended audit record to {journal_path()}")


def main() -> None:
    load_env()
    require_env()
    target = " ".join(sys.argv[1:]).strip() or os.getenv("DEFAULT_TARGET", "NosisTech LLC")
    if len(target) > 200:
        raise SystemExit("Target must be 200 characters or fewer.")
    run_chain(target)


if __name__ == "__main__":
    main()
