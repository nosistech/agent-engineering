# Memory-Augmented Conversational Agent (Letta Pattern)

## What this agent does

This agent demonstrates the core architectural pattern behind Letta (formerly MemGPT): a conversational AI that manages its own memory across sessions without human intervention. Unlike a standard chatbot that forgets everything when the conversation ends, this agent maintains a core memory block of key facts about the user and an archival memory log of past interactions. Before every response, it searches its own memory for relevant context and injects it into the prompt automatically.

When the agent learns something new, it writes that fact to disk and optionally updates its core memory profile. The result is a digital assistant that compounds knowledge over time rather than starting from zero on every conversation. All memory is stored in plain JSON and JSONL files on your machine. No external database, no server, no cloud dependency required.

## Prerequisites

- Python 3.14 (should work with 3.10+)
- A LiteLLM proxy running and reachable (default: http://localhost:4000)
- An API key for your LLM provider configured in the LiteLLM proxy

## Setup

1. Clone the repository containing these files.

2. Create a virtual environment and activate it:
   ```
   python -m venv venv
   source venv/bin/activate      # Linux / macOS
   venv\Scripts\activate         # Windows
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Copy the environment template and fill in your values:
   ```
   cp .env.template .env
   ```
   Open `.env` and set:
   - `LITELLM_BASE_URL`: the base URL of your LiteLLM proxy (e.g., http://localhost:4000)
   - `MODEL_NAME`: the model alias configured in your LiteLLM proxy
   - `LITELLM_API_KEY`: the API key your proxy expects
   - `AGENT_NAME`: what the agent calls itself (default: Nosis)

5. Run the agent:
   ```
   python agent.py
   ```
   The active model name is printed on startup. Type `exit` or `quit` to end the session.

## How to switch AI providers

Because the agent communicates exclusively through your LiteLLM proxy, switching providers requires no code changes:

1. Update the model routing in your LiteLLM configuration.
2. Change `MODEL_NAME` in your `.env` to match the alias you configured.
3. Restart the agent.

The Python code remains identical regardless of whether you are running DeepSeek, Claude, Gemini, or a local Ollama model.

## What NosisTech changed from the original Letta architecture

The upstream Letta project is a production platform with a FastAPI server, PostgreSQL with pgvector, Docker containerization, LangChain tool integrations, and sandboxed code execution. This rebuild strips or replaces those components for a standalone, inspectable implementation:

| Original Letta component | NosisTech replacement |
|---|---|
| FastAPI server | Terminal input loop in agent.py |
| PostgreSQL + pgvector | Local JSON (core) and JSONL (archival) files |
| Docker / containerization | Plain Python with python-dotenv |
| LangChain document loaders | Not needed for this build |
| e2b code interpreter sandbox | Not included |
| Alembic database migrations | No database, no migrations |

Improvements added beyond the original:

- Graceful failure when the LiteLLM endpoint is unreachable (loop continues, no crash)
- Input validation: empty messages prompt again without an API call
- Startup check lists all missing environment variables before any API call is made
- Active model name printed on startup so you always know which provider is running
- Exponential backoff on rate limits: 5, 10, and 20 second waits, up to 3 retries
- MEMORY_UPDATE parser sanitizes whitespace-only entries before writing to disk
- Words under 3 characters excluded from archival search queries to reduce noise
- Core memory auto-updated when a fact contains name:, role:, preference:, or company:
- data/ directory created automatically on first run, no manual setup required

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.
