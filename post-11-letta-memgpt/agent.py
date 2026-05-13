# (c) 2026 NosisTech LLC. Original implementation inspired by Letta (Apache 2.0): github.com/letta-ai/letta

import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from memory_manager import (
    append_archival_memory,
    load_core_memory,
    save_core_memory,
    search_archival_memory,
)

load_dotenv()

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def load_config():
    required = ["LITELLM_BASE_URL", "MODEL_NAME", "LITELLM_API_KEY"]
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        print("Missing required environment variable(s): " + ", ".join(missing))
        sys.exit(1)

    return {
        "base_url": os.getenv("LITELLM_BASE_URL"),
        "model": os.getenv("MODEL_NAME"),
        "api_key": os.getenv("LITELLM_API_KEY"),
        "agent_name": os.getenv("AGENT_NAME", "Nosis"),
        "max_results": int(os.getenv("MAX_ARCHIVAL_RESULTS", "3")),
        "core_path": os.getenv("CORE_MEMORY_PATH", "data/core_memory.json"),
        "archival_path": os.getenv("ARCHIVAL_MEMORY_PATH", "data/archival_memory.jsonl"),
    }


def build_system_prompt(config, core_memory, archival_entries):
    core_block = "\n".join(
        f"{key}: {value}" for key, value in core_memory.items() if value
    ) or "No facts stored yet."
    archival_block = "\n---\n".join(archival_entries) if archival_entries else "None found."

    return (
        f"You are {config['agent_name']}, a memory-augmented AI assistant built by NosisTech LLC.\n"
        "You have core memory for key user facts and archival memory for past interactions.\n\n"
        "When you learn a new important fact about the user, append it to your reply "
        "using this exact format on its own line:\n"
        "MEMORY_UPDATE: [the fact to remember]\n\n"
        "Only use MEMORY_UPDATE for genuinely new long-term facts. Do not repeat facts "
        "already present in core memory.\n\n"
        f"Core memory:\n{core_block}\n\n"
        f"Relevant past interactions:\n{archival_block}"
    )


def parse_reply(reply_text):
    visible_lines = []
    updates = []

    for line in reply_text.splitlines():
        if line.startswith("MEMORY_UPDATE:"):
            fact = line[len("MEMORY_UPDATE:"):].strip()
            if fact:
                updates.append(fact)
        else:
            visible_lines.append(line)

    visible_reply = "\n".join(visible_lines).strip()
    if not visible_reply and updates:
        visible_reply = "Got it. I'll remember that."
    return visible_reply, updates


def update_core_memory(fact, core_memory):
    if ":" not in fact:
        return False

    key, value = fact.split(":", 1)
    key = key.strip().lower()
    value = value.strip()
    if key in {"name", "role", "preference", "company"} and value:
        core_memory[key] = value
        return True
    return False


def call_llm(client, config, messages):
    wait_seconds = 5
    for attempt in range(1, 4):
        try:
            response = client.chat.completions.create(
                model=config["model"],
                messages=messages,
                temperature=0.7,
            )
            return response.choices[0].message.content
        except Exception as error:
            message = str(error).lower()
            temporary = "429" in message or "rate" in message or "timeout" in message or "connection" in message
            if temporary and attempt < 3:
                print(f"Temporary model issue. Retrying in {wait_seconds}s...")
                time.sleep(wait_seconds)
                wait_seconds *= 2
                continue
            print("Unable to reach the language model. Check your LiteLLM proxy and try again.")
            return None


def handle_turn(user_input, client, config, core_memory):
    archival_entries = search_archival_memory(
        config["archival_path"], user_input, config["max_results"]
    )
    messages = [
        {"role": "system", "content": build_system_prompt(config, core_memory, archival_entries)},
        {"role": "user", "content": user_input},
    ]
    reply_text = call_llm(client, config, messages)
    if reply_text is None:
        return None

    visible_reply, memory_updates = parse_reply(reply_text)
    core_changed = False
    for fact in memory_updates:
        append_archival_memory(config["archival_path"], fact)
        core_changed = update_core_memory(fact, core_memory) or core_changed

    if core_changed:
        save_core_memory(config["core_path"], core_memory)

    interaction = f"User: {user_input}\nAssistant: {visible_reply}"
    append_archival_memory(config["archival_path"], interaction)
    return visible_reply


def main():
    config = load_config()
    client = OpenAI(
        base_url=config["base_url"],
        api_key=config["api_key"],
        timeout=60,
    )

    Path(config["core_path"]).parent.mkdir(parents=True, exist_ok=True)
    core_memory = load_core_memory(config["core_path"])

    print(f"Active model: {config['model']}")
    print(f"\nHello, I am {config['agent_name']}, your memory-augmented assistant by NosisTech LLC.")
    print("I remember facts between sessions and search my own memory before every reply.")
    print("Type 'exit' or 'quit' to end the session.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            print("Goodbye.")
            break

        reply = handle_turn(user_input, client, config, core_memory)
        if reply:
            print(f"\n{config['agent_name']}: {reply}\n")


if __name__ == "__main__":
    main()
