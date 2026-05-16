# NosisTech General Problem Solver

## What this agent does

This agent demonstrates a trust-then-escalate reasoning pattern. It checks fictional business claims against a small trusted reference table and accepts claims that match within a narrow tolerance.

When a claim conflicts with the trusted record, the General Problem Solver takes over. It breaks the discrepancy into smaller questions, looks for an analogy, proposes a testable hypothesis, scores confidence, and records one lesson from the reasoning cycle.

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

This is an independent educational rebuild inspired by the architecture of Packt Chapter 8 General Problem Solver. It is not affiliated with, endorsed by, certified by, or presented as a replacement for the original project. The goal is to isolate one architectural pattern in a small, reviewable implementation.

- Removed production infrastructure, provider-specific wiring, and framework-specific complexity not needed for this learning build.
- Replaced the original system with a small LiteLLM-compatible educational pattern that can be inspected locally.
- Kept only the architecture needed to demonstrate trust-then-escalate routing into a General Problem Solver cycle.

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.
