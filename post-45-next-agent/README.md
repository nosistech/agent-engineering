# NosisTech Next Action Planner

## What this agent does

This agent demonstrates the SWE-agent architectural pattern in a safe, educational form. Instead of giving an AI model unrestricted access to a real computer, it provides a tiny simulated Agent-Computer Interface, or ACI. The model receives a fictional software issue, selects one action per turn from a small tool registry, observes the result, and repeats until it can produce a patch plan, request human review, or be blocked entirely.

The build uses three fictional scenarios to show three possible outcomes: PLAN_READY, NEEDS_REVIEW, and BLOCKED. No real files are read or written. No real commands are executed. The entire repository exists in memory as a Python dictionary.

## Prerequisites

- Python 3.14.2 or compatible
- pip
- A running LiteLLM proxy reachable at the URL you configure

## Setup

Copy the environment template and fill in your values:

```text
copy .env.template .env
```

Install dependencies:

```text
pip install -r requirements.txt
```

Run the agent:

```text
python agent.py
```

## How to switch AI providers

Open `.env` and change `MODEL_NAME` to any model string your LiteLLM proxy supports. To test more than one provider in a single run, separate model names with commas. No code changes are needed.

## Educational use and liability note

This project is an educational rebuild for learning and architectural review. It is not legal, compliance, security, financial, or professional advice. It is not a production system, certification, audit result, or guarantee of any outcome. For real environments, consult qualified professionals and validate independently.

## What NosisTech changed from the original

This is an independent educational rebuild inspired by the architecture of SWE-agent. It is not affiliated with, endorsed by, certified by, or presented as a replacement for the original project. The goal is to isolate one architectural pattern in a small, reviewable implementation.

- Removed production infrastructure, provider-specific wiring, and framework-specific complexity not needed for this learning build.
- Replaced the original system with a small LiteLLM-compatible educational pattern that can be inspected locally.
- Kept only the architecture needed to demonstrate a controlled Agent-Computer Interface loop.

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.

