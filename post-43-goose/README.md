# Agent 43 - Goose Action Planner

## What this agent does

This agent is an educational rebuild inspired by the architecture of Goose, an open-source agentic framework by Block, now under the Agentic AI Foundation. It accepts a fictional user task, classifies the task with a deterministic local safety gate, matches it to a small pretend tool registry, and asks a LiteLLM-routed model to produce a structured action plan in JSON format.

The agent does not execute commands, access files beyond its own `.env`, connect to the internet, run shell operations, or interact with real tools. Its purpose is to isolate and demonstrate one architectural pattern: task classification, pretend tool selection, and safety-gated planning in a small Python implementation.

## Prerequisites

- Python 3.14.2, which is the version tested for this rebuild
- pip
- A running LiteLLM proxy available in your own environment

## Setup

1. Copy the environment template to `.env`.
2. Fill in `LITELLM_BASE_URL`, `MODEL_NAME`, and `LITELLM_API_KEY` with values from your own LiteLLM environment.
3. Install dependencies with `pip install -r requirements.txt`.
4. Run the agent with `python agent.py`.

## How to switch AI providers

Change `MODEL_NAME` in your `.env` file to any model string your LiteLLM proxy supports. Nothing else in the code needs to change.

## Educational use and liability note

This project is an educational rebuild for learning and architectural review. It is not legal, compliance, security, financial, or professional advice. It is not a production system, certification, audit result, or guarantee of any outcome. For real environments, consult qualified professionals and validate independently.

## What NosisTech changed from the original

This is an independent educational rebuild inspired by the architecture of Goose. It is not affiliated with, endorsed by, certified by, or presented as a replacement for the original project. The goal is to isolate one architectural pattern in a small, reviewable implementation.

- Removed production infrastructure, provider-specific wiring, and framework-specific complexity not needed for this learning build.
- Replaced the original system with a small LiteLLM-compatible educational pattern that can be inspected locally.
- Kept only the architecture needed to demonstrate task classification, pretend tool selection, and safety-gated planning.

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.
