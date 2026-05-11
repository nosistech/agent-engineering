# Physical World Sensing Agent

## What it does

Monitors a commercial office building by reading simulated sensor data across
multiple physical zones. For each zone it measures temperature, CO2, and
occupancy. Using proportional control logic with deadband hysteresis built in
pure Python, the agent decides what HVAC and ventilation commands to issue. It
then calls an AI model via LiteLLM to generate a plain-English facility status
report a non-technical facilities manager can read and act on. Every cycle is
logged to a structured JSONL file for audit purposes.

## Prerequisites

- Python 3.11 or higher
- A running LiteLLM proxy (or any OpenAI-compatible endpoint)
- An API key for your chosen model provider

## Setup

1. Clone the repository and navigate to this folder.
2. Install dependencies:
   pip install -r requirements.txt
3. Copy .env.template to .env and fill in your values.
4. Adjust zone_config.yaml to match your facility zones and targets.
5. Run the agent:
   python agent.py

## How to switch providers

Change MODEL_NAME in your .env file to any LiteLLM-supported model identifier.
The agent routes through LiteLLM with no code changes required. Tested with
deepseek-v4-pro and gemini/gemini-2.0-flash.

## What NosisTech changed from the original

- Stripped all local ML model loading (torch, transformers). Replaced with
  direct LiteLLM calls via the OpenAI SDK.
- Replaced hardcoded zone configuration dictionary with an external YAML file.
  Path is set in .env, not hardcoded.
- Added proper deadband hysteresis so minor temperature fluctuations do not
  trigger unnecessary HVAC cycles.
- Added structured JSONL logging for every simulation cycle.
- Removed vision agent and audio agent. This build focuses solely on the
  physical sensor and building control logic.
- Added graceful failure handling, rate limit retries with exponential backoff,
  and environment variable validation on startup.
- All configuration in .env. Zero hardcoded secrets, paths, or model names.

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.