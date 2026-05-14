# Griptape-Style Governance Pipeline

## What this agent does

This agent rebuilds the core Griptape architectural pattern as a small LiteLLM-native Python demo. It routes a fictional enterprise request through a controlled sequence of tasks, retrieves matching policy context, stores supporting material off-prompt in temporary task memory, and asks the model for a structured governance decision.

The output is a decision packet with the local risk level, model decision, human checkpoint flag, reason, and policy memory reference. The demo is intentionally small so the architecture is visible: pipeline discipline, local tools, task memory, and provider-agnostic model access.

## Prerequisites

- Python 3.14.2
- pip
- A running LiteLLM proxy
- A model configured in LiteLLM

## Setup

1. Copy `.env.template` to `.env`.
2. Fill in the environment-specific values in `.env`.
3. Install dependencies:

```text
pip install -r requirements.txt
```

4. Run the agent:

```text
python agent.py
```

## How to switch AI providers

Change `MODEL_NAME` in `.env` to the model name configured in your LiteLLM proxy. Nothing else in the code needs to change.

## What NosisTech changed from the original

Griptape provides a full framework with agents, pipelines, workflows, tasks, drivers, tools, memory, and retrieval components. This rebuild keeps the architectural lesson and removes the framework dependency. The result is a small Python implementation that uses plain functions for tasks, a local list for the pipeline, an in-memory dictionary for task memory, and the OpenAI-compatible client routed through LiteLLM.

The original framework supports many production patterns. This demo focuses only on the part needed for Post 32: disciplined task flow, bounded tool behavior, off-prompt task references, and model-agnostic execution.

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.
