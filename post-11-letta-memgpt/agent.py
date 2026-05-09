# (c) 2026 NosisTech LLC. Original implementation inspired by Letta (Apache 2.0): github.com/letta-ai/letta

import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables before anything else
load_dotenv()

from openai import OpenAI
from memory_manager import (
    load_core_memory,
    save_core_memory,
    append_archival_memory,
    search_archival_memory,
)

# Configuration from environment
LITELLM_BASE_URL = os.getenv("LITELLM_BASE_URL")
MODEL_NAME = os.getenv("MODEL_NAME")
LITELLM_API_KEY = os.getenv("LITELLM_API_KEY")
AGENT_NAME = os.getenv("AGENT_NAME", "Nosis")
MAX_ARCHIVAL_RESULTS = int(os.getenv("MAX_ARCHIVAL_RESULTS", "3"))
CORE_MEMORY_PATH = os.getenv("CORE_MEMORY_PATH", "data/core_memory.json")
ARCHIVAL_MEMORY_PATH = os.getenv("ARCHIVAL_MEMORY_PATH", "data/archival_memory.jsonl")

# Validate required environment variables before making any API call
missing_vars = []
if not LITELLM_BASE_URL:
    missing_vars.append("LITELLM_BASE_URL")
if not MODEL_NAME:
    missing_vars.append("MODEL_NAME")
if not LITELLM_API_KEY:
    missing_vars.append("LITELLM_API_KEY")

if missing_vars:
    print("Missing required environment variable(s):")
    for var in missing_vars:
        print(f"  - {var}")
    print("Please set them in your .env file and try again.")
    sys.exit(1)

# Initialize OpenAI client pointed at LiteLLM proxy
client = OpenAI(
    base_url=LITELLM_BASE_URL,
    api_key=LITELLM_API_KEY,
)


def build_system_prompt(core_memory, archival_entries):
    """Construct the system message with core memory block and relevant past interactions."""
    memory_block = "\n".join(
        f"{key}: {value}" for key, value in core_memory.items() if value
    )
    if not memory_block:
        memory_block = "No facts stored yet."

    past = (
        "\n---\n".join(archival_entries) if archival_entries else "None found."
    )

    system_text = (
        f"You are {AGENT_NAME}, a memory-augmented AI assistant built by NosisTech LLC.\n"
        "You have access to a core memory block containing key facts about the user, "
        "and an archival memory of past interactions.\n\n"
        "When you learn a new important fact about the user, append it to your reply "
        "using this exact format on its own line:\n"
        "MEMORY_UPDATE: [the fact to remember]\n\n"
        "Only use MEMORY_UPDATE when you learn something genuinely new and worth "
        "remembering long-term. Do not fabricate memory updates. Do not update memory "
        "with things already in your core memory block.\n\n"
        f"Your core memory block:\n{memory_block}\n\n"
        f"Relevant past interactions:\n{past}"
    )
    return system_text


def parse_and_process_reply(reply_text):
    """Extract MEMORY_UPDATE lines from the reply and return cleaned reply and update list."""
    lines = reply_text.splitlines()
    cleaned_lines = []
    memory_updates = []

    for line in lines:
        if line.startswith("MEMORY_UPDATE:"):
            fact = line[len("MEMORY_UPDATE:"):].strip()
            if fact:
                memory_updates.append(fact)
            # Omit the MEMORY_UPDATE line from what the user sees
        else:
            cleaned_lines.append(line)

    cleaned_reply = "\n".join(cleaned_lines).strip()
    return cleaned_reply, memory_updates


def update_core_memory_if_relevant(fact, core_memory):
    """Check if a fact contains a recognized core memory key and update the dict."""
    lower_fact = fact.lower()
    for keyword in ["name:", "role:", "preference:", "company:"]:
        if keyword in lower_fact:
            parts = fact.split(":", 1)
            if len(parts) == 2:
                key_part = parts[0].strip().lower()
                value_part = parts[1].strip()
                if key_part in ("name", "role", "preference", "company") and value_part:
                    core_memory[key_part] = value_part
                    return True
    return False


def call_llm_with_retry(messages):
    """Send messages to LiteLLM with exponential backoff on rate limit or connection errors."""
    max_retries = 3
    wait_seconds = 5

    for attempt in range(1, max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                temperature=0.7,
            )
            return response.choices[0].message.content
        except Exception as error:
            error_message = str(error)
            is_rate_limit = "429" in error_message or "rate" in error_message.lower()
            is_connection = (
                "connection" in error_message.lower()
                or "timeout" in error_message.lower()
                or "unreachable" in error_message.lower()
            )

            if (is_rate_limit or is_connection) and attempt < max_retries:
                print(f"Temporary issue reaching the model. Retrying in {wait_seconds}s...")
                time.sleep(wait_seconds)
                wait_seconds *= 2
            elif is_rate_limit and attempt == max_retries:
                print("Rate limit persists after multiple attempts. Please try again in a moment.")
                return None
            elif is_connection and attempt == max_retries:
                print(
                    "Unable to reach the language model. "
                    "Check that your LiteLLM proxy is running and reachable."
                )
                return None
            else:
                print("An unexpected error occurred. Returning to input prompt.")
                return None

    return None


def main():
    """Run the memory-augmented conversational agent loop."""
    print(f"Active model: {MODEL_NAME}")

    # Create data directory if it does not exist
    data_dir = str(Path(CORE_MEMORY_PATH).parent)
    Path(data_dir).mkdir(parents=True, exist_ok=True)

    # Load core memory from disk
    core_memory = load_core_memory(CORE_MEMORY_PATH)

    print(f"\nHello, I am {AGENT_NAME}, your memory-augmented assistant by NosisTech LLC.")
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

        if user_input.lower() in ("exit", "quit"):
            print("Goodbye.")
            break

        # Search archival memory for relevant past context
        archival_entries = search_archival_memory(
            ARCHIVAL_MEMORY_PATH, user_input, MAX_ARCHIVAL_RESULTS
        )

        # Build the prompt with memory context
        system_message = build_system_prompt(core_memory, archival_entries)
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_input},
        ]

        # Call the LLM
        reply_text = call_llm_with_retry(messages)

        if reply_text is None:
            continue

        # Parse reply for memory updates
        cleaned_reply, memory_updates = parse_and_process_reply(reply_text)

        # Process each memory update
        core_memory_changed = False
        for fact in memory_updates:
            append_archival_memory(ARCHIVAL_MEMORY_PATH, fact)
            if update_core_memory_if_relevant(fact, core_memory):
                core_memory_changed = True

        if core_memory_changed:
            save_core_memory(CORE_MEMORY_PATH, core_memory)

        # Append the full interaction to archival memory
        interaction_text = f"User: {user_input}\nAssistant: {cleaned_reply}"
        append_archival_memory(ARCHIVAL_MEMORY_PATH, interaction_text)

        # Print the cleaned reply
        print(f"\n{AGENT_NAME}: {cleaned_reply}\n")


if __name__ == "__main__":
    main()
