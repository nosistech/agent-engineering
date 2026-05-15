# (c) 2026 NosisTech LLC. Original implementation.

import json
import os
import re
import sys
import time
from openai import APIConnectionError, APIStatusError, OpenAI, OpenAIError, RateLimitError

REQUIRED_VARS = ["LITELLM_BASE_URL", "MODEL_NAME", "LITELLM_API_KEY"]
VERDICTS = {"SUPPORTED", "PARTIAL", "NEEDS_REVIEW"}
BLOCKED = ["password", "secret key", "exploit", "medical diagnosis", "investment advice", "legal advice", "personal data", "confidential"]

PACKETS = [
    {"id": "SRC-001", "title": "Aether Works AI Policy Notes", "tags": "ai policy governance approval automation", "text": "Internal AI workflow pilots receive documented review before wider use. Human review is expected when outputs may affect budgets or staffing."},
    {"id": "SRC-002", "title": "Meridian Operations Automation Pilot", "tags": "workflow automation efficiency training pilot", "text": "Three reporting workflows used automation. Processing time decreased, while staff training created a temporary first-phase cost."},
    {"id": "SRC-003", "title": "Orion Review Group Governance Survey", "tags": "governance audit oversight risk policy", "text": "Many teams lacked version tracking, review cycles, and incident notes for AI-assisted internal tools."},
    {"id": "SRC-004", "title": "Callisto Responsible Automation Brief", "tags": "automation review transparency limits ethics", "text": "The brief recommends labeling automated outputs, documenting review steps, and avoiding unsupported claims when evidence is incomplete."},
]

SCENARIOS = [("AI Governance Controls", "What governance controls are useful for internal AI automation pilots?"), ("Automation Efficiency Review", "What does the evidence say about workflow automation and training cost?"), ("Unsupported Broad Topic", "What is the best approach to every possible technology risk?")]


def load_env():
    """Load KEY=value pairs from a local .env file if one exists."""
    if not os.path.exists(".env"):
        return
    with open(".env", "r", encoding="utf-8-sig") as env_file:
        for line in env_file:
            clean = line.strip()
            if clean and not clean.startswith("#") and "=" in clean:
                key, value = clean.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())


def check_env():
    """Stop before model calls when required environment values are missing."""
    missing = [name for name in REQUIRED_VARS if not os.getenv(name)]
    if missing:
        print("Missing required environment variables:")
        for name in missing:
            print("  - " + name)
        sys.exit(1)
    print("NosisTech Micro Research Agent")
    print("Active model: " + os.getenv("MODEL_NAME"))
    print("Educational model only. No internet search. No real websites accessed.")


def make_client():
    """Create an OpenAI-compatible client pointed at LiteLLM."""
    return OpenAI(base_url=os.getenv("LITELLM_BASE_URL"), api_key=os.getenv("LITELLM_API_KEY"))


def extract_json(text):
    """Return the first valid JSON object found in model output."""
    if not text:
        return None
    start = text.find("{")
    while start != -1:
        depth = 0
        for index in range(start, len(text)):
            if text[index] == "{":
                depth += 1
            if text[index] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : index + 1])
                    except json.JSONDecodeError:
                        break
        start = text.find("{", start + 1)
    return None


def call_model(client, prompt):
    """Call the active model and handle common provider failures clearly."""
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=os.getenv("MODEL_NAME"),
                messages=[{"role": "user", "content": prompt}],
                max_tokens=600,
            )
            return response.choices[0].message.content or ""
        except RateLimitError:
            if attempt == 2:
                print("Rate limit exceeded after three attempts. Please try again later.")
                return ""
            wait = 2**attempt
            print("Rate limit hit. Retrying in " + str(wait) + " seconds.")
            time.sleep(wait)
        except APIConnectionError:
            print("Cannot reach the LiteLLM endpoint. Check your environment-specific proxy setting.")
            return ""
        except APIStatusError as error:
            print("The provider returned an error with status code " + str(error.status_code) + ".")
            return ""
        except OpenAIError:
            print("The model request failed. Check your LiteLLM and provider configuration.")
            return ""


def safe_question(question):
    """Reject empty or sensitive demo questions before model calls."""
    if not question.strip():
        return False, "Question is empty."
    if "every possible" in question.lower() or "all possible" in question.lower():
        return False, "Question is too broad for this small fictional evidence set."
    if any(term in question.lower() for term in BLOCKED):
        return False, "Question contains sensitive wording and needs review."
    return True, ""


def plan(client, topic):
    """Ask the model for three short research questions."""
    prompt = (
        "Create exactly three research questions for this educational topic:\n"
        + topic
        + '\nReturn only JSON like {"questions":["...","...","..."]}.'
    )
    parsed = extract_json(call_model(client, prompt))
    if isinstance(parsed, dict) and isinstance(parsed.get("questions"), list):
        return [str(item) for item in parsed["questions"][:3]]
    return [topic]


def words(text):
    """Convert text into searchable lowercase keywords."""
    return set(re.findall(r"\b[a-zA-Z]{4,}\b", text.lower()))


def gather(questions):
    """Select fictional source packets using keyword overlap."""
    selected = {}
    for question in questions:
        question_words = words(question)
        for packet in PACKETS:
            packet_words = words(packet["title"] + " " + packet["tags"] + " " + packet["text"])
            if question_words & packet_words:
                selected[packet["id"]] = packet
            if len(selected) == 3:
                return list(selected.values())
    return list(selected.values())


def publish(client, topic, packets):
    """Ask the model to summarize selected source packets with citations."""
    source_text = "\n\n".join("[" + item["id"] + "] " + item["title"] + "\n" + item["text"] for item in packets)
    example_id = packets[0]["id"]
    prompt = (
        "Write a cautious educational research summary using only these fictional source packets.\n"
        "Do not add outside facts. Do not give professional advice.\n"
        "Return only valid JSON. The citations value must be a JSON array of selected source IDs.\n"
        "Example shape: "
        + '{"verdict":"PARTIAL","summary":"Short cited summary using [' + example_id + '].","citations":["' + example_id + '"],"limits":"Short limits note."}'
        + "\nTopic: "
        + topic
        + "\n\nSources:\n"
        + source_text
    )
    return extract_json(call_model(client, prompt))


def review_report(report, packets):
    """Validate report verdict and source citations."""
    allowed_ids = [item["id"] for item in packets]
    if not isinstance(report, dict):
        cited = ", ".join(allowed_ids)
        titles = ", ".join(item["title"] for item in packets)
        return {"verdict": "PARTIAL", "summary": "The selected fictional packets provide related evidence from " + titles + ". The model response did not match the requested JSON shape, so this local fallback summary records only that evidence was selected.", "citations": allowed_ids, "limits": "Fallback summary used because provider JSON formatting was not usable. Cited fictional packets: " + cited + "."}
    citations = report.get("citations", [])
    if report.get("verdict") not in VERDICTS:
        report["verdict"] = "NEEDS_REVIEW"
    if not isinstance(citations, list) or not citations:
        report["verdict"] = "NEEDS_REVIEW"
        report["citations"] = []
    elif any(citation not in allowed_ids for citation in citations):
        report["verdict"] = "NEEDS_REVIEW"
        report["limits"] = "Citation validation failed because the model referenced an unselected source."
    return report


def show(name, questions, packets, report):
    """Print one readable scenario result."""
    print("\n" + "=" * 60)
    print("SCENARIO: " + name)
    print("VERDICT : " + report.get("verdict", "NEEDS_REVIEW"))
    print("PLAN:")
    for number, question in enumerate(questions, 1):
        print("  " + str(number) + ". " + question)
    print("SOURCES : " + (", ".join(item["id"] for item in packets) or "None"))
    print("SUMMARY : " + report.get("summary", "No summary available."))
    print("LIMITS  : " + report.get("limits", "Not specified."))


def run():
    """Run all fictional scenarios through the micro research pipeline."""
    load_env()
    check_env()
    client = make_client()
    for name, question in SCENARIOS:
        allowed, reason = safe_question(question)
        if not allowed:
            show(name, [], [], {"verdict": "NEEDS_REVIEW", "summary": reason, "limits": reason})
            continue
        questions = plan(client, question)
        packets = gather(questions)
        if not packets:
            show(name, questions, [], {"verdict": "NEEDS_REVIEW", "summary": "No matching fictional source packets were found.", "limits": "The topic needs better scoped evidence before summary."})
            continue
        report = review_report(publish(client, question, packets), packets)
        show(name, questions, packets, report)
    print("\n" + "=" * 60)
    print("Run complete. No internet search was performed. No real websites were accessed.")
    print("All examples used fictional source packets for educational purposes only.")


if __name__ == "__main__":
    run()
