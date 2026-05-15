# Post 37: Verification and Validation Agent

## What This Agent Does

This agent acts as an inspection station for AI-generated business claims. It receives a plain-English claim, uses an AI model to extract the important factual parts into structured JSON, and then applies deterministic Python logic to compare that claim against trusted reference values.

The model handles the reading and structuring of the claim, but Python computes the final verdict. Each result is marked PASS, REVIEW, or FAIL so the user can see whether the claim matched the trusted reference, drifted into review territory, or conflicted with the reference data.

## Prerequisites

- Python 3.14.2
- pip
- A running LiteLLM proxy reachable from the value you configure in `.env`

## Setup

```powershell
git clone https://github.com/nosistech/agent-engineering.git
cd agent-engineering/post-37-verification-validation-agent
Copy-Item .env.template .env
# Edit .env and fill in LITELLM_BASE_URL, MODEL_NAME, and LITELLM_API_KEY
pip install -r requirements.txt
python agent.py
```

## How to Switch AI Providers

Change `MODEL_NAME` in your `.env` file to any model name configured in your LiteLLM proxy. No code changes are required.

## What NosisTech Changed from the Original

This is an independent educational rebuild inspired by the architecture of the referenced framework or source project. It is not affiliated with, endorsed by, or presented as a replacement for the original project.

The original source demonstrated verification inside a larger tri-agent analytics pipeline. It also included local model dependencies, provider-specific setup, notebook execution, statistical analysis, chart recommendations, and a problem-solving fallback loop.

NosisTech rebuilt the verification gate as a small LiteLLM-native agent. This version keeps the architecture focused on one lesson: the model extracts the claim, then deterministic Python logic checks that claim against trusted reference data. The rebuild removes local model dependencies, provider-specific SDK setup, heavyweight data analysis libraries, charting logic, and the full tri-agent pipeline.

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.
