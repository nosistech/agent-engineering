# (c) 2026 NosisTech LLC. Original implementation.
import os
import sys
import sqlite3
import datetime
import time
import math
import openai
from dotenv import load_dotenv
import litellm
from litellm import completion, embedding
from litellm.exceptions import RateLimitError, APIConnectionError
from duckduckgo_search import DDGS

# Load environment variables from .env file
load_dotenv()

# Required environment variables
REQUIRED_VARS = [
    "LITELLM_BASE_URL",
    "MODEL_NAME",
    "LITELLM_API_KEY",
    "EMBEDDING_MODEL",
    "KNOWLEDGE_FILE",
    "DB_PATH",
    "SESSION_ID",
]

def check_env_vars():
    """Verify all required environment variables are set and exit if any are missing."""
    missing = [var for var in REQUIRED_VARS if not os.environ.get(var)]
    if missing:
        print("Missing required environment variables:", ", ".join(missing))
        print("Please set them in a .env file. Example provided in .env.template")
        sys.exit(1)

check_env_vars()

LITELLM_BASE_URL = os.environ["LITELLM_BASE_URL"]
MODEL_NAME = os.environ["MODEL_NAME"]
LITELLM_API_KEY = os.environ["LITELLM_API_KEY"]
EMBEDDING_MODEL = os.environ["EMBEDDING_MODEL"]
KNOWLEDGE_FILE = os.environ["KNOWLEDGE_FILE"]
DB_PATH = os.environ["DB_PATH"]
SESSION_ID = os.environ["SESSION_ID"]

print(f"Model active: {MODEL_NAME}")

# ----------------------------------------------------------------------
# SQLite memory management
# ----------------------------------------------------------------------

def init_memory_db(db_path):
    """Create conversations table if it does not exist."""
    os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            session_id TEXT,
            role TEXT,
            content TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()

init_memory_db(DB_PATH)

def load_memory(session_id):
    """Load conversation history for a given session, returning list of dicts with role and content."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role, content FROM conversations WHERE session_id = ? ORDER BY timestamp ASC",
        (session_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"role": row[0], "content": row[1]} for row in rows]

def save_memory(session_id, role, content):
    """Save a single message (role + content) to the conversation history."""
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO conversations (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
        (session_id, role, content, timestamp),
    )
    conn.commit()
    conn.close()

# ----------------------------------------------------------------------
# Embedding and knowledge retrieval
# ----------------------------------------------------------------------

def embed_text(text):
    """Embed text using the LiteLLM proxy via openai SDK with exponential backoff on rate limit errors."""
    import openai
    client = openai.OpenAI(
        api_key=LITELLM_API_KEY,
        base_url=LITELLM_BASE_URL,
    )
    max_retries = 3
    delay = 1
    for attempt in range(max_retries):
        try:
            response = client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=[text],
                encoding_format="float",
            )
            return response.data[0].embedding
        except openai.RateLimitError:
            if attempt < max_retries - 1:
                time.sleep(delay)
                delay *= 2
            else:
                raise
        except openai.APIConnectionError:
            print("Failed to connect to LiteLLM proxy. Check if the service is running.")
            sys.exit(1)

def cosine_similarity(vec_a, vec_b):
    """Pure Python cosine similarity between two vectors."""
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)

def load_knowledge_chunks(file_path):
    """Read knowledge file, split into paragraphs, embed each, return list of dicts with text and embedding."""
    if not os.path.exists(file_path):
        print(f"Knowledge file not found at configured path. Exiting.")
        sys.exit(1)
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    raw_chunks = [chunk.strip() for chunk in content.split("\n\n") if chunk.strip()]
    chunks = []
    for chunk_text in raw_chunks:
        vec = embed_text(chunk_text)
        chunks.append({"text": chunk_text, "embedding": vec})
    return chunks

# Load knowledge on startup
knowledge_base = load_knowledge_chunks(KNOWLEDGE_FILE)

def search_knowledge(query):
    """Search internal knowledge for the most similar chunk above threshold 0.75."""
    query_embedding = embed_text(query)
    best_score = -1.0
    best_chunk = None
    for chunk in knowledge_base:
        score = cosine_similarity(query_embedding, chunk["embedding"])
        if score > best_score:
            best_score = score
            best_chunk = chunk["text"]
    if best_score >= 0.75 and best_chunk is not None:
        return best_chunk
    return None

# ----------------------------------------------------------------------
# Web search tool (fallback)
# ----------------------------------------------------------------------

def web_search(query):
    """Perform a DuckDuckGo text search and return the snippet of the first result, truncated to 500 chars."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=1))
        if results:
            snippet = results[0].get("body", "")
            return snippet[:500]
        else:
            return "No web results found."
    except Exception:
        return "No web results found."

# ----------------------------------------------------------------------
# Prompt construction and agent execution
# ----------------------------------------------------------------------

def build_prompt(memory, context, source_label, query):
    """Build the message list for the LiteLLM completion call."""
    messages = []
    messages.append({
        "role": "system",
        "content": (
            "You are a research assistant for NosisTech LLC. "
            "You answer questions using the provided context. "
            "Be concise and factual. Do not invent information not present in the context."
        ),
    })
    for msg in memory:
        messages.append(msg)
    messages.append({
        "role": "user",
        "content": f"Context from {source_label}:\n{context}\n\nQuestion: {query}",
    })
    return messages

def run_agent(session_id, query):
    """Execute the full agent pipeline: knowledge search, web fallback, LLM reply, memory save."""
    if not query or not isinstance(query, str):
        print("Empty query. Skipping.")
        return
    if len(query) > 1000:
        print("Query too long (max 1000 characters). Skipping.")
        return

    internal_found = search_knowledge(query)
    if internal_found:
        context = internal_found
        source_label = "internal knowledge"
    else:
        context = web_search(query)
        source_label = "web search"

    memory = load_memory(session_id)
    messages = build_prompt(memory, context, source_label, query)

    client = openai.OpenAI(
        api_key=LITELLM_API_KEY,
        base_url=LITELLM_BASE_URL,
    )
    max_retries = 3
    delay = 1
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
            )
            break
        except openai.RateLimitError:
            if attempt < max_retries - 1:
                time.sleep(delay)
                delay *= 2
            else:
                raise
        except openai.APIConnectionError:
            print("Failed to connect to LiteLLM proxy. Check if the service is running.")
            sys.exit(1)

    assistant_reply = response.choices[0].message.content

    save_memory(session_id, "user", query)
    save_memory(session_id, "assistant", assistant_reply)

    print(assistant_reply)
    if f"Source: {source_label}" not in assistant_reply:
        print(f"Source: {source_label}")

# ----------------------------------------------------------------------
# Main demo
# ----------------------------------------------------------------------

if __name__ == "__main__":
    if not os.path.exists(KNOWLEDGE_FILE):
        print("Knowledge file not found. Creating sample knowledge file.")
        sample_content = (
            "NosisTech LLC provides AI governance consulting services. "
            "This includes AI risk assessments, responsible AI policy drafting, "
            "and compliance audits for EU AI Act and NIST AI RMF.\n\n"
            "Our cloud security practice helps organizations secure their multi-cloud "
            "environments on AWS, Azure, and GCP. We perform configuration reviews, "
            "penetration testing, and implement zero-trust architectures.\n\n"
            "Additionally, NosisTech offers executive workshops on AI strategy, "
            "board-level AI risk awareness, and AI ethics framework development."
        )
        os.makedirs(
            os.path.dirname(KNOWLEDGE_FILE) if os.path.dirname(KNOWLEDGE_FILE) else ".",
            exist_ok=True
        )
        with open(KNOWLEDGE_FILE, "w", encoding="utf-8") as f:
            f.write(sample_content)
        knowledge_base = load_knowledge_chunks(KNOWLEDGE_FILE)

    print(f"Session ID: {SESSION_ID}")
    queries = [
        "What services does NosisTech offer?",
        "Who are the main competitors in AI governance consulting?",
        "Remind me what NosisTech does.",
    ]
    for q in queries:
        print(f"\n--- Query: {q} ---")
        run_agent(SESSION_ID, q)