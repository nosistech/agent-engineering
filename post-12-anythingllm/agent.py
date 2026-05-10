# (c) 2026 NosisTech LLC. Original implementation.
import os
import sys
import time
import requests
from dotenv import load_dotenv

load_dotenv()

REQUIRED_VARS = {
    "ANYTHINGLLM_BASE_URL": "The base URL of your AnythingLLM instance (e.g., http://localhost:3001)",
    "ANYTHINGLLM_API_KEY": "Your AnythingLLM API key",
    "ANYTHINGLLM_WORKSPACE": "The slug of the target workspace"
}

missing = []
for var, desc in REQUIRED_VARS.items():
    if not os.getenv(var):
        missing.append(f"{var} ({desc})")
if missing:
    print("Missing required environment variables. Please set the following in your .env file:")
    for item in missing:
        print(f"  - {item}")
    sys.exit(1)

BASE_URL = os.getenv("ANYTHINGLLM_BASE_URL").rstrip("/")
API_KEY = os.getenv("ANYTHINGLLM_API_KEY")
WORKSPACE_SLUG = os.getenv("ANYTHINGLLM_WORKSPACE")

HEADERS = {"Authorization": f"Bearer {API_KEY}"}


def _retry_request(method, url, max_retries=3, backoff_factor=2, **kwargs):
    """Send an HTTP request with exponential backoff on 429 rate limit errors."""
    last_exception = None
    for attempt in range(max_retries + 1):
        try:
            response = getattr(requests, method)(url, headers=HEADERS, **kwargs)
            if response.status_code == 429:
                wait = backoff_factor ** (attempt + 1)
                print(f"Rate limit hit. Retrying in {wait} seconds.")
                time.sleep(wait)
                continue
            return response
        except requests.exceptions.RequestException as exc:
            last_exception = exc
            print(f"Network error: {exc}")
            if attempt < max_retries:
                wait = backoff_factor ** (attempt + 1)
                print(f"Retrying in {wait} seconds.")
                time.sleep(wait)
            else:
                raise last_exception
    raise requests.exceptions.HTTPError("429 Too Many Requests after maximum retries")


def check_health():
    """Confirm the AnythingLLM instance is reachable and the API key is accepted."""
    try:
        resp = _retry_request("get", f"{BASE_URL}/api/v1/auth")
        if resp.status_code == 200:
            print(f"Health check passed. AnythingLLM instance is reachable and API key accepted.")
            return True
        else:
            print(f"Health check failed. Status {resp.status_code}. Check your URL and API key.")
            sys.exit(1)
    except Exception as exc:
        print(f"Cannot reach AnythingLLM. Please verify ANYTHINGLLM_BASE_URL and network connectivity.")
        sys.exit(1)


def query_workspace(question: str) -> dict:
    """Send a question to the workspace and return the answer with source citations."""
    if not question or not question.strip():
        print("Error: The question must be a non-empty string.")
        return {}

    url = f"{BASE_URL}/api/v1/workspace/{WORKSPACE_SLUG}/chat"
    payload = {"message": question, "mode": "chat"}
    try:
        resp = _retry_request("post", url, json=payload)
        if resp.status_code != 200:
            print(f"Query failed. Server returned {resp.status_code}.")
            return {}
        data = resp.json()
        answer = data.get("textResponse", "")
        sources_raw = data.get("sources", [])

        sources = []
        for src in sources_raw:
            doc_name = src.get("title") or src.get("source") or src.get("filename", "unknown")
            sources.append(doc_name)

        if not sources:
            print("Note: Answer generated without specific document retrieval. No source citations returned.")

        return {"answer": answer, "sources": sources}
    except Exception as exc:
        print(f"Error querying workspace: {str(exc)}")
        return {}


def upload_document(file_path: str) -> bool:
    """Upload a file to the workspace for indexing."""
    if not os.path.isfile(file_path):
        print(f"Error: File not found. Please check the path and try again.")
        return False

    url = f"{BASE_URL}/api/v1/document/upload"
    try:
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f)}
            resp = _retry_request("post", url, files=files)
        if resp.status_code == 200:
            print(f"Upload succeeded. {os.path.basename(file_path)} has been uploaded to workspace {WORKSPACE_SLUG}.")
            return True
        else:
            try:
                reason = resp.json().get("error", resp.text)
            except Exception:
                reason = resp.text
            print(f"Upload failed. Server response: {reason}")
            return False
    except Exception as exc:
        print(f"Upload error: {str(exc)}")
        return False


def get_chat_history(limit: int = 10) -> list:
    """Retrieve recent chat history from the workspace."""
    url = f"{BASE_URL}/api/v1/workspace/{WORKSPACE_SLUG}/chats"
    params = {"limit": limit}
    try:
        resp = _retry_request("get", url, params=params)
        if resp.status_code != 200:
            print(f"Failed to fetch chat history. Status {resp.status_code}.")
            return []
        data = resp.json()
        raw_chats = data.get("chats", data) if isinstance(data, dict) else data
        history = []
        for entry in raw_chats:
            if isinstance(entry, dict):
                role = entry.get("role", "")
                content = entry.get("content") or entry.get("message", "")
                if role and content is not None:
                    history.append({"role": role, "content": content})
        if not history:
            print("No chat history found for this workspace.")
        return history
    except Exception as exc:
        print(f"Error retrieving chat history: {str(exc)}")
        return []


if __name__ == "__main__":
    print(f"Active workspace: {WORKSPACE_SLUG}")
    check_health()

    question = "What is NosisTech's data handling policy?"
    print(f"\nQuerying workspace: {question}")
    result = query_workspace(question)
    if result:
        print("\nAnswer:")
        print(result.get("answer", ""))
        sources = result.get("sources", [])
        if sources:
            print("\nSources:")
            for src in sources:
                print(f"  - {src}")
    else:
        print("No answer returned.")

    print("\nLast 5 chat exchanges:")
    history = get_chat_history(limit=5)
    for entry in history:
        role = entry.get("role", "unknown")
        content = entry.get("content", "")
        display_content = (content[:200] + "...") if len(content) > 200 else content
        print(f"  [{role}]: {display_content}")