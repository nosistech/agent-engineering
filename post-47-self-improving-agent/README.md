# NosisTech Self-Improving Agent

## What this agent does

This agent demonstrates a controlled self-improvement loop in a safe, educational form. It reviews fictional support metrics, identifies which KPIs are below target, asks a configured LiteLLM model for a structured improvement hypothesis, and records only approved text-level adaptations.

The agent does not rewrite its own source code, run generated code, access real systems, or deploy changes. It demonstrates the pattern of sensing feedback, critiquing performance, planning an improvement, routing it through an approval gate, and learning through versioned in-memory records.

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

This is an independent educational rebuild inspired by the architecture of Packt Chapter 9 Self-Improving Agent. It is not affiliated with, endorsed by, certified by, or presented as a replacement for the original project. The goal is to isolate one architectural pattern in a small, reviewable implementation.

- Removed production infrastructure, provider-specific wiring, and framework-specific complexity not needed for this learning build.
- Replaced the original system with a small LiteLLM-compatible educational pattern that can be inspected locally.
- Kept only the architecture needed to demonstrate a controlled sense, critique, plan, approve, and learn loop.

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.
