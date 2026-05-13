# Knowledge Retrieval Agent (RAG)

## What this agent does

This agent gives an AI model the ability to answer questions using only the content of your private documents. It reads a folder of plain text files, splits them into overlapping text chunks, converts each chunk into a mathematical representation called a vector embedding, and stores those vectors in a local FAISS search index. When you ask a question, the agent converts the question into the same mathematical format, finds the chunks in the index that are closest in meaning, and passes only those chunks to the AI as its allowed source. The AI is instructed strictly to summarize what the documents say, not to add any information from its own training. If the documents do not contain a relevant answer, the agent says so clearly rather than guessing.

## Prerequisites

- Python 3.10 or later (tested with Python 3.14)
- A running LiteLLM proxy instance (github.com/BerriAI/litellm)
- API credentials for at least one LLM provider configured in your LiteLLM proxy
- A docs/ folder containing one or more .txt files as your private knowledge base

## Setup

1. Clone or download this agent into your project folder.

2. Install dependencies:

   pip install -r requirements.txt

3. Copy the environment template and fill in your values:

   cp .env.template .env

4. Edit .env with your actual configuration:

   - LITELLM_BASE_URL: the URL where your LiteLLM proxy is running
   - MODEL_NAME: the chat model name as configured in your LiteLLM proxy
   - EMBEDDING_MODEL_NAME: the embedding model name
   - LITELLM_API_KEY: the API key your LiteLLM proxy expects
   - DOCS_DIR: path to your documents folder (default: docs)
   - CHUNK_SIZE: character count per chunk (default: 1000)
   - CHUNK_OVERLAP: character overlap between adjacent chunks (default: 200)
   - TOP_K_RESULTS: how many chunks to retrieve per question (default: 4)

5. Create a docs/ folder and add your .txt files to it.

6. Run the agent:

   python agent.py

## How to switch AI providers

This agent uses LiteLLM as its unified gateway. To switch providers, update MODEL_NAME and EMBEDDING_MODEL_NAME in your .env file to any model your LiteLLM proxy supports. No code changes required. All major providers are supported: OpenAI, Anthropic, DeepSeek, Gemini, Ollama, and more.

## What NosisTech changed from the original

The original version of this agent relied heavily on the LangChain framework. NosisTech LLC rebuilt it from the ground up to remove that dependency entirely.

- LangChain removed: all langchain, langchain_openai, langchain_community, and langchain_huggingface imports were stripped. The agent uses the openai Python SDK pointed at a LiteLLM proxy for chat, and httpx calls to the LiteLLM embeddings endpoint for retrieval.
- FAISS used directly: the vector index is built with faiss and numpy instead of LangChain's FAISS wrapper.
- Pure Python chunking: the RecursiveCharacterTextSplitter was replaced with a plain Python function.
- All configuration externalized: model names, base URLs, API keys, chunk parameters, and document paths are read from environment variables. Nothing is hardcoded.
- Simple error handling: missing environment variables are reported before any API call, empty knowledge bases halt cleanly, and model request failures are shown without exposing secrets.
- Input validation: empty questions are rejected before any API call is made.
- Provider-agnostic: changing MODEL_NAME or EMBEDDING_MODEL_NAME in .env switches the entire pipeline with no code changes.

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.
