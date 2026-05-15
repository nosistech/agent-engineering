# OpenHands Sandbox Planner

## What this agent does

The OpenHands Sandbox Planner is an educational demo inspired by OpenHands architecture. It accepts fictional software task descriptions, runs them through a local deterministic safety gate, and calls a LiteLLM-routed model only for tasks that are safe to plan or require review planning.

This demo does not execute code, run shell commands, does not read or write project files beyond loading its own .env configuration. Every action in the output refers to a pretend tool name. The purpose is to study task classification, simulated tool selection, simulated observations, and review-gated planning.

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

This is an independent educational demo inspired by the architecture of OpenHands. It is not affiliated with, endorsed by, certified by, or presented as a replacement for the original project. The goal is to isolate one architectural pattern in a small, reviewable implementation.

- Removed production infrastructure, provider-specific wiring, enterprise features, and framework-specific complexity not needed for this learning build.
- Replaced real sandbox execution with a small LiteLLM-compatible simulated engineering loop that can be inspected locally.
- Kept only the architecture needed to demonstrate task classification, pretend tool selection, simulated observations, and review-gated planning.

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.
