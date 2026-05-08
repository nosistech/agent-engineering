Autonomous Decision‑Making Agent
What this agent does
This agent provides a fully autonomous triage system for customer support at NosisTech LLC, a boutique AI governance and cloud security consultancy. When a customer submits an issue, the agent immediately evaluates the customer’s tier (standard, premium, enterprise), any active system alerts, and an urgency score. It then computes a mathematical escalation score and decides, without human input, whether to answer the issue automatically using a large language model or to escalate it to a human support specialist.

All routine, low‑risk questions are handled automatically, while high‑priority or enterprise‑level issues are routed to a person. The agent leaves a detailed audit trail for every decision so that non‑technical operators can understand exactly why each action was taken.

Prerequisites
Python 3.11 or higher
pip package manager
A running instance of LiteLLM proxy, configured with your chosen AI provider(s)
Setup
Clone this repository and navigate to the project folder.
Create a .env file by copying the template:
bash

Collapse
Copy
1
cp .env.template .env
Open .env and fill in the placeholder values with your own configuration (see template for required keys).
Install the dependencies:
bash

Collapse
Copy
1
pip install -r requirements.txt
Run the agent:
bash

Collapse
Copy
1
python agent.py
How to switch AI providers
Simply change the MODEL_NAME value in your .env file to any model supported by your LiteLLM proxy (e.g., claude-3-opus-20240229, deepseek-chat, gemini-1.5-pro, gpt-4o). The agent will instantly use the new provider without any code changes.

What NosisTech changed from the original
Replaced direct API imports with a LiteLLM‑compatible openai SDK for provider flexibility.
Removed all hardcoded secrets, model names, and file paths; everything now comes from the .env file.
Added robust environment validation on startup, input sanitisation, and rate‑limit handling.
Introduced an auditable escalation trail that prints a structured summary of every decision.
All example data references NosisTech LLC; no real company or personal information is used.
(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.