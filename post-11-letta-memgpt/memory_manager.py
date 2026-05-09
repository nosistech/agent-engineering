# (c) 2026 NosisTech LLC. Original implementation.

import json
import os
from datetime import datetime, timezone


def load_core_memory(path):
    """Load core memory from JSON file, creating it with empty defaults if missing."""
    if not os.path.exists(path):
        default_memory = {
            "name": "",
            "role": "",
            "preference": "",
            "company": "",
        }
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as file_handle:
            json.dump(default_memory, file_handle, indent=2)
        return default_memory

    with open(path, "r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


def save_core_memory(path, data):
    """Write the core memory dict to the JSON file on disk."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as file_handle:
        json.dump(data, file_handle, indent=2)


def append_archival_memory(path, entry_text):
    """Append a timestamped JSONL entry to the archival memory file."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "text": entry_text,
    }
    with open(path, "a", encoding="utf-8") as file_handle:
        file_handle.write(json.dumps(entry) + "\n")


def search_archival_memory(path, query, max_results):
    """Return up to max_results archival entries whose text contains any word from the query."""
    if not os.path.exists(path):
        return []

    query_words = [word for word in query.lower().split() if len(word) > 2]
    if not query_words:
        return []

    matched = []
    with open(path, "r", encoding="utf-8") as file_handle:
        for line in file_handle:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            entry_text_lower = entry.get("text", "").lower()
            if any(word in entry_text_lower for word in query_words):
                matched.append(entry["text"])
                if len(matched) >= max_results:
                    break

    return matched
