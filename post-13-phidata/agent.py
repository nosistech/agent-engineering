# (c) 2026 NosisTech LLC. Original implementation.

import json
import os
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


PROJECT_DIR = Path(__file__).resolve().parent

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def load_env():
    env_path = PROJECT_DIR / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if line.strip() and "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def load_config():
    required = ["LITELLM_BASE_URL", "MODEL_NAME", "LITELLM_API_KEY", "KNOWLEDGE_FILE"]
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        print("[ERROR] Missing environment variables: " + ", ".join(missing))
        sys.exit(1)
    return {
        "base_url": os.getenv("LITELLM_BASE_URL").rstrip("/"),
        "model": os.getenv("MODEL_NAME"),
        "api_key": os.getenv("LITELLM_API_KEY"),
        "knowledge_file": os.getenv("KNOWLEDGE_FILE"),
    }


def project_path(path):
    candidate = Path(path)
    return candidate if candidate.is_absolute() else PROJECT_DIR / candidate


def call_llm(config, context, question, source_label):
    payload = json.dumps(
        {
            "model": config["model"],
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a concise research assistant for NosisTech LLC. "
                        "Answer only from the provided context. If the context is "
                        "insufficient, say so plainly."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Source: {source_label}\nContext:\n{context}\n\nQuestion: {question}",
                },
            ],
            "temperature": 0.2,
        }
    ).encode("utf-8")

    request = Request(
        f"{config['base_url']}/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=60) as response:
            body = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"LiteLLM returned HTTP {error.code}: {detail}") from error
    except URLError as error:
        raise RuntimeError(f"Could not reach LiteLLM at {config['base_url']}: {error}") from error
    return body["choices"][0]["message"]["content"].strip()


def words(text):
    stop_words = {"a", "an", "and", "are", "does", "for", "in", "is", "of", "on", "the", "to", "what"}
    return set(re.findall(r"[a-z0-9]+", text.lower())) - stop_words


def load_knowledge(config):
    path = project_path(config["knowledge_file"])
    if not path.exists():
        raise FileNotFoundError(f"Knowledge file not found: {path}")
    return [chunk.strip() for chunk in path.read_text(encoding="utf-8").split("\n\n") if chunk.strip()]


def search_internal_knowledge(query, chunks):
    query_words = words(query)
    external_words = {"competitor", "competitors", "latest", "market", "news", "pricing", "stock", "today"}
    best_chunk = None
    best_score = 0

    for chunk in chunks:
        chunk_words = words(chunk)
        if query_words & external_words and not query_words & external_words & chunk_words:
            continue
        score = len(query_words & chunk_words)
        if score > best_score:
            best_chunk = chunk
            best_score = score

    return best_chunk if best_score >= 2 else None


def web_search(query):
    params = urlencode({"q": query, "format": "json", "no_redirect": "1", "no_html": "1"})
    request = Request(
        f"https://api.duckduckgo.com/?{params}",
        headers={"User-Agent": "NosisTech-Agent-Engineering-Demo"},
    )
    try:
        with urlopen(request, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception:
        return "No web result was available."

    if data.get("AbstractText"):
        return data["AbstractText"]
    for topic in data.get("RelatedTopics") or []:
        if isinstance(topic, dict) and topic.get("Text"):
            return topic["Text"]
    return "No web result was available."


def answer_question(config, question):
    context = search_internal_knowledge(question, load_knowledge(config))
    source_label = "internal knowledge" if context else "web search"
    context = context or web_search(question)
    return call_llm(config, context, question, source_label), source_label


def run_agent(config, query):
    print(f"[USER] {query}")
    answer, source_label = answer_question(config, query)
    print(f"[AGENT] {answer}")
    print(f"[SOURCE] {source_label}\n")


def main():
    load_env()
    config = load_config()
    print(f"[INFO] Active model: {config['model']}")

    queries = sys.argv[1:] or [
        "What services does NosisTech offer?",
        "Who are the main competitors in AI governance consulting?",
    ]
    run_agent(config, " ".join(queries) if sys.argv[1:] else queries[0])
    if not sys.argv[1:]:
        run_agent(config, queries[1])


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        print(error)
        sys.exit(1)
