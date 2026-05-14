# AI Act Risk Categorization Agent

Pattern #49 in the NosisTech Agent Engineering Series.

## What this agent does

This agent demonstrates a simple AI Act risk review pattern with a hypothetical AI system.

It reads four fields:

- name
- purpose
- data used
- deployment context

Then it prints:

- the risk tier assigned by simple rules
- the rule matches
- a short model-generated explanation
- obligations flagged by the demo
- recommended actions
- whether human or legal review is required

This is an educational architecture demo only. It is not legal advice, regulatory advice, compliance certification, or a legal status determination. For certainty, consult qualified legal counsel in the relevant jurisdiction.

## Digital Omnibus note

This demo refers to the May 7, 2026 Digital Omnibus on AI as a provisional political agreement pending formal adoption. It is not treated as final law.

## Architecture

The agent has two layers:

1. A rule layer checks for clear phrases such as hiring, credit scoring, social scoring, chatbots, deepfakes, and AI-generated content.
2. An LLM layer explains the rule result in plain English and reminds the reader that real decisions need qualified review.

The important pattern is simple:

```text
AI system description
rules assign a first risk tier
LLM explains the result
human lawyer decides the real legal answer
```

## Setup

Open the SSH tunnel in one terminal:

```bash
ssh -L 4000:localhost:4000 your-user@your-vps-host
```

Install dependencies:

```bash
pip install openai python-dotenv
```

Copy the environment template:

```bash
cp .env.template .env
```

Edit `.env`:

```bash
LITELLM_BASE_URL=http://localhost:4000
MODEL_NAME=your-model-name
LITELLM_API_KEY=your-key
```

Run:

```bash
python agent.py
```

## Demo input

The built-in demo is a hiring-screening assistant. The rule layer should flag it as High Risk because it involves employment screening.

## Model switching

Change only `MODEL_NAME` in `.env` to test another LiteLLM provider.

## License

MIT License, Copyright 2026 NosisTech LLC.
