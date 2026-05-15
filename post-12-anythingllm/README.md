# AnythingLLM Integration Client

## What This Client Does

This Python client gives any NosisTech agent programmatic access to a
self-hosted AnythingLLM instance. AnythingLLM is a private document
intelligence platform that stores internal documents in a searchable
vector database and answers questions by retrieving exact relevant
passages before generating a response. Privacy depends on how your
AnythingLLM instance, vector database, and model provider are configured.

The client performs three operations: confirms the instance is reachable,
sends natural language questions to a named workspace and returns the
answer with source citations, and retrieves recent chat history from a
workspace thread.

## Prerequisites

- Python 3.10 or higher (tested with 3.14)
- pip for installing dependencies
- A running AnythingLLM instance with a configured workspace and a valid API key

## Setup

1. Clone this repository or download the files into a folder.
2. Copy .env.template to .env:
   cp .env.template .env
3. Edit .env and fill in your values:
   - ANYTHINGLLM_BASE_URL: the URL where your AnythingLLM is running
   - ANYTHINGLLM_API_KEY: your API key from the instance settings
   - ANYTHINGLLM_WORKSPACE: the slug of the workspace you want to query
4. Install dependencies:
   pip install -r requirements.txt
5. Run the agent:
   python agent.py

## How to Point This Client at a Different AnythingLLM Instance

Change only the three variables in your .env file. No code changes required.

## What NosisTech Added Beyond the AnythingLLM Default API Examples

- Validates all environment variables on startup and names exactly what is missing
- Exponential backoff on rate limit responses
- No stack traces or sensitive values ever printed
- Source citations formatted for immediate human reading
- Clear note when no citations were returned so the operator knows the confidence level
- Smaller client surface focused on health check, workspace query, and chat history

## What NosisTech Changed from the Original

This is an independent educational rebuild inspired by the architecture of the referenced framework or source project. It is not affiliated with, endorsed by, or presented as a replacement for the original project.

- Removed production infrastructure, provider-specific wiring, and framework-specific complexity not needed for this learning build.
- Replaced the original system with a small LiteLLM-compatible educational pattern that can be inspected locally.
- Kept only the architecture needed to demonstrate the specific agent pattern in this post.

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.
