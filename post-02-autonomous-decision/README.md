# Autonomous Decision-Making Agent

## What this agent does

This agent provides an autonomous triage system for customer support at
NosisTech LLC, a boutique AI governance and cloud security consultancy. When a
customer submits an issue, the agent evaluates the customer tier, active system
alerts, and urgency score. It then computes an escalation score and decides
whether to answer automatically with a large language model or route the issue
to a human support specialist.

Routine, low-risk questions are handled automatically. High-priority or
enterprise-level issues are escalated. The agent prints an audit trail so
operators can understand why each action was taken.

## Prerequisites

- Python 3.11 or higher
- pip
- A running LiteLLM proxy configured with your chosen AI provider

## Setup

1. Clone this repository and navigate to this folder.
2. Create a `.env` file by copying the template:

   ```bash
   cp .env.template .env
   ```

3. Open `.env` and fill in the placeholder values.
4. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

5. Run the agent:

   ```bash
   python agent.py
   ```

## How to switch AI providers

Change `MODEL_NAME` in your `.env` file to any model supported by your LiteLLM
proxy. The agent will use the new provider without code changes.

## What NosisTech changed from the original

- Replaced direct API imports with a LiteLLM-compatible OpenAI SDK client.
- Removed hardcoded secrets, model names, and file paths.
- Added startup environment validation, input sanitization, and rate-limit
  handling.
- Added an auditable escalation trail that prints a structured decision summary.
- Kept all example data fictional and scoped to NosisTech LLC.

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.
