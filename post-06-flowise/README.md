# Post 6: Flowise - Build AI Agents Without Writing Code

(c) 2026 NosisTech LLC. Original implementation.

## What This Does

Flowise is a visual drag-and-drop platform for building AI agents without
writing code. This folder documents the NosisTech setup: Flowise running
via Docker, connected to a LiteLLM proxy for model-agnostic AI routing.

The demo flow built for this post is a PDF knowledge agent. Upload any
document, ask questions about it, and get answers retrieved directly from
the document content.

## Prerequisites

- Docker Desktop installed and running
- LiteLLM proxy running and accessible
- Google API key for embeddings

## Setup

1. Install and start Flowise via Docker:
docker run -d --name flowise -p 3000:3000 flowiseai/flowise

2. Open your browser at:
http://localhost:3000

3. Create a new Chatflow and add these nodes:
   - LiteLLM (Chat Models)
   - PDF File (Document Loaders)
   - Google Gemini Embedding (Embeddings)
   - In-Memory Vector Store (Vector Stores)
   - Conversational Retrieval QA Chain (Chains)

## How to Configure LiteLLM Connection

In the LiteLLM node enter:
- Base URL: your LiteLLM proxy URL
- API Key: your LITELLM_API_KEY
- Model Name: your configured model name

## How to Switch AI Providers

Change the model name in your LiteLLM configuration file. The Flowise
flow does not need to change. Restart LiteLLM and the new provider
is active immediately.

## Full Write-Up

nosistech.com/flowise-build-ai-agents-without-writing-code/

## What NosisTech Changed from the Original

This is an independent educational rebuild inspired by the architecture of the referenced framework or source project. It is not affiliated with, endorsed by, or presented as a replacement for the original project.

- Removed production infrastructure, provider-specific wiring, and framework-specific complexity not needed for this learning build.
- Replaced the original system with a small LiteLLM-compatible educational pattern that can be inspected locally.
- Kept only the architecture needed to demonstrate the specific agent pattern in this post.

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.