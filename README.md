# Agent Engineering

NosisTech AI Agent Engineering Series: practical, small Python examples that
show common AI agent patterns without hiding the important parts behind a large
framework.

The repo is organized as one folder per post. Each example is intentionally
compact: read the local `README.md`, copy the environment template when one is
provided, install that folder's requirements, and run `agent.py`.

## Patterns Included

| Folder | Pattern |
| --- | --- |
| `post-01-tool-invocation-agent` | Tool invocation and chart generation |
| `post-02-autonomous-decision` | Autonomous triage with escalation rules |
| `post-03-market-data` | Market data lookup and summarization |
| `post-04-financial-news` | Financial news briefing |
| `post-05-async-standup-summarizer` | Async team update summarization |
| `post-06-flowise` | No-code Flowise workflow |
| `post-07-praisonai` | Multi-agent research workflow |
| `post-08-memory-augmented-agent` | Persistent memory pattern |
| `post-09-knowledge-retrieval-agent` | Retrieval-augmented generation |
| `post-10-document-intelligence-agent` | OCR, extraction, and review routing |
| `post-11-letta-memgpt` | Letta-style memory manager |
| `post-12-anythingllm` | AnythingLLM API integration |
| `post-13-phidata` | Memory, knowledge, and tool use |
| `post-14-planning-agent` | Plan generation and execution |
| `post-15-data-analysis-agent` | Statistical analysis plus narrative |
| `post-16-marketing-content-assistant` | Multi-role content workflow |
| `post-17-physical-world-sensing-agent` | Sensor simulation and action policy |
| `post-18-langflow` | Langflow exported workflow and API client |
| `post-19-dspy` | DSPy prediction and optimization |
| `post-20-chain-of-agents-orchestrator` | Sequential specialist agents |
| `post-21-conflict-resolution-agent` | Dual-review conflict escalation |
| `post-22-financial-advisory` | Market/news advisory briefing |
| `post-23-crewai` | CrewAI research crew |
| `post-24-autogen` | AutoGen examples |
| `post-25-agency-swarm` | Agency Swarm orchestration |
| `post-28-explainable-agent` | Explainability, confidence, and counterfactuals |
| `post-29-compliance-driven-agent` | Compliance-driven software engineering |
| `post-35-prompt-injection-defense-agent` | Prompt injection screening |
| `post-36-hallucination-detection-agent` | Claim-level hallucination review |
| `post-40-gdpr-ccpa-compliance-agent` | GDPR and CCPA privacy screening |

## Quick Start

```bash
cd post-05-async-standup-summarizer
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.template .env
python agent.py
```

Most examples expect a LiteLLM-compatible endpoint and environment variables
such as `LITELLM_BASE_URL`, `MODEL_NAME`, and `LITELLM_API_KEY`. Check each
post's README because some examples also need data-provider keys or local input
files.

## Repository Notes

- Generated files such as reports, chart images, memory logs, local databases,
  and `.env` files should stay out of version control.
- The examples favor clarity over production architecture. They are meant to
  make agent patterns inspectable, not to be drop-in enterprise systems.
- Some integrations require external tools such as LiteLLM, Langflow,
  AnythingLLM, CrewAI, AutoGen, or Agency Swarm.
