# Physical World Sensing Agent

## What it does

This project demonstrates a small physical-world agent pattern:

1. Simulate temperature, CO2, and occupancy readings for facility zones.
2. Apply deterministic control rules for HVAC and ventilation.
3. Ask the model to narrate the resulting facility status in plain English.
4. Append the run to a JSONL sensor log for audit history.

The model does not control the building. Python rules decide the commands. The model only explains the current state to a facilities manager.

## Prerequisites

- Python 3.11 or later
- A running LiteLLM endpoint

## Setup

1. Copy `.env.template` to `.env`.
2. Fill in your LiteLLM base URL, model name, API key, zone config path, and sensor log path.
3. Run the agent:

```bash
python agent.py
```

No package install is required. The agent uses only the Python standard library.

## How to switch providers

Edit `MODEL_NAME` in `.env`. Because the agent calls LiteLLM, the code does not need to change when you switch between supported providers.

## What NosisTech changed from the original

This is an independent educational rebuild inspired by the architecture of the referenced framework or source project. It is not affiliated with, endorsed by, or presented as a replacement for the original project.

- Reduced the project to sensor input, rule-based control, model narration, and audit logging.
- Removed proportional control, deadband logic, and CO2 severity tiers.
- Removed numpy, PyYAML, OpenAI SDK, dotenv, and retry scaffolding.
- Kept external `zone_config.yaml` so the building layout remains visible.
- Kept JSONL sensor logging as the audit trail.

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.
