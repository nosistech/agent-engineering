# Prompt Injection Defense Agent

Pattern #64 in the NosisTech Agent Engineering Series.

## What this agent does

This agent demonstrates a small middleware pattern for prompt injection defense.

It checks incoming text before that text would be sent to a main AI model. The demo looks for suspicious phrases, assigns a simple risk score, returns `SAFE`, `WARNING`, or `BLOCK`, redacts matched phrases, and asks the model to explain the result.

This is an educational security demo only. It should not be treated as a complete security system.

## Architecture

The agent has four steps:

1. A rule scanner looks for common prompt injection phrases.
2. A decision function turns the matches into a risk score and verdict.
3. A sanitizer redacts suspicious phrases from the text.
4. An LLM explanation layer summarizes the decision in plain English.

The important pattern is:

```text
incoming text
rule scanner
SAFE, WARNING, or BLOCK
sanitized text
model explanation
```

## Setup

Install dependencies:

```bash
pip install openai python-dotenv
```

Copy the environment template:

```bash
cp .env.template .env
```

Edit `.env` for your own LiteLLM-compatible endpoint:

```bash
LITELLM_BASE_URL=YOUR_LITELLM_BASE_URL
MODEL_NAME=YOUR_MODEL_NAME
LITELLM_API_KEY=YOUR_LITELLM_API_KEY
```

Run:

```bash
python agent.py
```

## Demo cases

The script runs three built-in examples:

- a normal support question
- a direct injection attempt
- a retrieved document with a hidden instruction

## License

MIT License, Copyright 2026 NosisTech LLC.
