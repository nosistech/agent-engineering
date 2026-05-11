# DSPy Support Ticket Router

## What this agent does
This three-stage demonstration agent reads NosisTech LLC client support emails
and classifies them by category, priority, and whether human escalation is
required. It uses the DSPy framework with any AI model served through a
LiteLLM proxy.

Stage 1 uses a basic Predict module. Stage 2 upgrades to ChainOfThought.
Stage 3 runs a BootstrapFewShot optimizer against labeled examples and
compares the optimized program against the baseline on a held-out test email.

## Prerequisites
- Python 3.11 or later
- A running LiteLLM proxy
- An AI model accessible through the proxy

## Setup
1. Copy .env.template to .env and fill in your values
2. pip install -r requirements.txt
3. python agent.py

## How to switch AI providers
Change MODEL_NAME in your .env file. No code changes required.

## What NosisTech built here
A clean DSPy pipeline with no orchestration frameworks. Includes environment-driven
model selection, graceful failure on unreachable proxy, exponential backoff on
rate limits, and a BootstrapFewShot optimizer that improves classification using
a small set of labeled examples.

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.