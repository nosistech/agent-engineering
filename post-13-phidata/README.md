# Phidata-Pattern Agent (Memory, Knowledge, and Tools)

## What this agent does

This agent is a pure Python implementation of the three foundational pillars
of the Phidata agent architecture: Memory, Knowledge, and Tools, built without
any external agent framework. It acts as a research assistant for NosisTech LLC
analysts.

When you ask a question, the agent first searches an internal knowledge base
loaded from a local text file. If nothing relevant is found, it automatically
falls back to a live DuckDuckGo web search. Every response clearly states
whether the answer came from internal knowledge or a web search. The agent
remembers every conversation across runs, so you never need to repeat context.
All provider configuration is done through environment variables, making it
simple to switch between any model your LiteLLM proxy supports.

## Prerequisites

- Python 3.14 or newer
- A running instance of LiteLLM (local or remote) with an accessible base URL and API key
- An embedding model configured in your LiteLLM proxy
- The dependencies listed in requirements.txt

## Setup

1. Clone or download this project.
2. Copy .env.template to .env and fill in all values:
   - LITELLM_BASE_URL: your LiteLLM proxy address
   - MODEL_NAME: the model name your proxy supports
   - LITELLM_API_KEY: the API key your proxy expects
   - EMBEDDING_MODEL: the embedding model name configured in your proxy
   - KNOWLEDGE_FILE: path to your knowledge text file (defaults to knowledge.txt)
   - DB_PATH: path for the SQLite memory database (defaults to memory.db)
   - SESSION_ID: a unique label for this conversation session
3. Install dependencies:
   pip install -r requirements.txt
4. Run the agent:
   python agent.py

The agent will create a sample knowledge.txt on first run if none is found,
so the demo works immediately without any manual file setup.

## How to switch AI providers

Change only MODEL_NAME in your .env file. The LiteLLM proxy handles routing
to the actual provider. You can use any model your LiteLLM instance supports,
including OpenAI, Anthropic, DeepSeek, Gemini, and local Ollama models,
without touching the code. The embedding model is configured separately via
EMBEDDING_MODEL.

## How the three pillars work

Memory: Conversation history is stored in a SQLite database. Every message is
saved with the session ID and a UTC timestamp. When a new query arrives, the
full history is loaded and included in the prompt, giving the agent long-term
conversational awareness across separate runs.

Knowledge: A local text file is chunked into paragraphs and each chunk is
converted into a vector embedding using the model specified in EMBEDDING_MODEL.
At query time, the user question is embedded and compared against all chunks
using cosine similarity. The highest-scoring chunk above a threshold of 0.75
is used as internal context. No external vector database is required.

Tools: If no relevant information is found in the knowledge base, the agent
automatically runs a DuckDuckGo web search and feeds the retrieved snippet into
the prompt. The response always labels whether the answer came from internal
knowledge or a web search.

## What NosisTech changed from the Phidata original

- Replaced the entire Phidata/Agno framework with standard library modules and
  the LiteLLM client. Zero external agent framework imports.
- Memory uses the sqlite3 standard library instead of SQLAlchemy.
- Knowledge retrieval uses in-memory cosine similarity instead of a vector database.
- Tools are plain Python functions called conditionally, not decorated class instances.
- No hardcoded model names. Everything is driven by environment variables.
- Source transparency added so the user always knows whether the answer came
  from internal knowledge or a live web search.
- Missing environment variables trigger a clean exit with a clear message before
  any API call is attempted.
- Connection failures and rate limit errors are handled with exponential backoff
  and user-friendly messages. No raw stack traces.
- Sample knowledge.txt is created automatically on first run.

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.