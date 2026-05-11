# Market Intelligence Agent

A multi-agent system that researches any company or topic and produces a plain-English intelligence report. Three specialist agents (news, financials, sentiment) gather data, a manager synthesizes the report, and built-in conflict detection flags contradictory findings.

**How it works:** You supply a target (e.g., "NosisTech LLC") via command line or `.env` default. The agents call LiteLLM (must be running) sequentially, each writing to a JSONL memory log. The manager reads all findings, asks the model to detect contradictions, and generates a final report. If the conflict score exceeds your threshold, a standalone warning block appears after the report, not hidden inside it.

## Prerequisites

- Python 3.11 or later
- A running LiteLLM proxy instance (or compatible HTTP endpoint)
- Access credentials for at least one LLM provider configured in LiteLLM

## Setup

1. Clone the repository and navigate to the project folder.
2. Copy `.env.template` to `.env` and fill in real values:
   - `LITELLM_BASE_URL`: The URL of your LiteLLM proxy (e.g., `http://localhost:4000`)
   - `MODEL_NAME`: The model name as known to LiteLLM (e.g., `deepseek-v4-pro` or `gemini/gemini-2.0-flash`)
   - `LITELLM_API_KEY`: Your LiteLLM API key
   - `MEMORY_LOG_PATH`: Where to save the JSONL log (default `outputs/memory_log.jsonl`)
   - `CONFLICT_THRESHOLD`: Float between 0 and 1; conflicts above this value are flagged (default `0.5`)
   - `DEFAULT_TARGET`: Fallback target if none provided via command line
3. Install dependencies:
   pip install -r requirements.txt
4. Run the agent:
   python agent.py "NosisTech LLC"
   Omit the argument to use the default target from `.env`.

## How to switch AI providers

Update `MODEL_NAME` in your `.env` file to any model supported by your LiteLLM configuration. Restart the agent. No code changes required.

## What NosisTech changed from the original

- Replaced vendor SDKs and hardcoded model names with the OpenAI client connected to LiteLLM
- All configuration via environment variables, nothing hardcoded
- Exponential backoff retry on rate limits, up to 3 attempts
- Graceful startup validation with clear missing variable reporting
- Conflict transparency: contradictions above threshold appear in a standalone warning block, not buried in the report
- Memory log directory created automatically if missing
- Input validation on target string

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.