# (c) 2026 NosisTech LLC. Original implementation.

import json
import os
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
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
    "KNOWLEDGE_FILE",
]


def safe_print(text: str) -> None:
    print(text.encode("ascii", errors="replace").decode("ascii"))


def check_environment() -> None:
    missing = [name for name in REQUIRED_VARS if not os.getenv(name)]
    if missing:
        safe_print(f"[ERROR] Missing environment variables: {', '.join(missing)}")
        sys.exit(1)
    safe_print(f"[INFO] Active model: {os.getenv('MODEL_NAME')}")


def project_path(path: str) -> str:
    if os.path.isabs(path):
        return path
    return os.path.join(PROJECT_DIR, path)


def call_llm(messages: list[dict[str, str]]) -> str:
    base_url = os.getenv("LITELLM_BASE_URL", "").rstrip("/")
    payload = json.dumps(
        {
            "model": os.getenv("MODEL_NAME"),
            "messages": messages,
            "temperature": 0.2,
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


def words(text: str) -> set[str]:
    stop_words = {"a", "an", "and", "are", "does", "for", "in", "is", "of", "on", "the", "to", "what"}
    return set(re.findall(r"[a-z0-9]+", text.lower())) - stop_words


def load_knowledge() -> list[str]:
    path = project_path(os.getenv("KNOWLEDGE_FILE", "knowledge.txt"))
    if not os.path.exists(path):
        raise FileNotFoundError(f"Knowledge file not found: {path}")

    with open(path, encoding="utf-8") as file:
        return [chunk.strip() for chunk in file.read().split("\n\n") if chunk.strip()]


def search_internal_knowledge(query: str, chunks: list[str]) -> str | None:
    query_words = words(query)
    external_topic_words = {"competitor", "competitors", "latest", "market", "news", "pricing", "stock", "today"}
    best_chunk = None
    best_score = 0

    for chunk in chunks:
        chunk_words = words(chunk)
        if query_words & external_topic_words and not query_words & external_topic_words & chunk_words:
            continue
        score = len(query_words & chunk_words)
        if score > best_score:
            best_score = score
            best_chunk = chunk

    if best_score >= 2:
        return best_chunk
    return None


def web_search(query: str) -> str:
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

    abstract = data.get("AbstractText")
    if abstract:
        return abstract

    related_topics = data.get("RelatedTopics") or []
    for topic in related_topics:
        if isinstance(topic, dict) and topic.get("Text"):
            return topic["Text"]

    return "No web result was available."


def answer_question(query: str) -> tuple[str, str]:
    chunks = load_knowledge()
    context = search_internal_knowledge(query, chunks)
    source_label = "internal knowledge"

    if context is None:
        context = web_search(query)
        source_label = "web search"

    messages = [
        {
            "role": "system",
            "content": (
                "You are a concise research assistant for NosisTech LLC. "
                "Answer only from the provided context. "
                "If the context is insufficient, say so plainly."
            ),
        },
        {
            "role": "user",
            "content": f"Source: {source_label}\nContext:\n{context}\n\nQuestion: {query}",
        },
    ]
    return call_llm(messages), source_label


def run_agent(query: str) -> None:
    safe_print(f"[USER] {query}")
    answer, source_label = answer_question(query)
    safe_print(f"[AGENT] {answer}")
    safe_print(f"[SOURCE] {source_label}\n")


def main() -> None:
    check_environment()

    if len(sys.argv) > 1:
        run_agent(" ".join(sys.argv[1:]))
        return

    demo_queries = [
        "What services does NosisTech offer?",
        "Who are the main competitors in AI governance consulting?",
    ]
    for query in demo_queries:
        run_agent(query)


if __name__ == "__main__":
    main()
