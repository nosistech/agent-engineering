# NosisTech Stateful Data Analyst

## What this agent does

This agent demonstrates the TaskWeaver architecture in a safe, educational form. A planner model receives a fictional analytics request and returns a structured JSON plan. A local allowlisted executor then carries out only the approved action using in-memory pandas DataFrames.

The session state persists across turns inside one run. A follow-up request can reuse a DataFrame loaded in an earlier step, and a missing-column error can be fed back to the planner for one correction cycle. No generated Python code is executed, and no real data is accessed.

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

This is an independent educational rebuild inspired by the architecture of TaskWeaver. It is not affiliated with, endorsed by, certified by, or presented as a replacement for the original project. The goal is to isolate one architectural pattern in a small, reviewable implementation.

- Removed production infrastructure, provider-specific wiring, and framework-specific complexity not needed for this learning build.
- Replaced the original system with a small LiteLLM-compatible educational pattern that can be inspected locally.
- Kept only the architecture needed to demonstrate planner-to-executor handoff, stateful analytics memory, and safe allowlisted operations.

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.
