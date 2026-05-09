# Document Intelligence Agent

## What this agent does

This agent automates document data extraction for business operations. It accepts an image or PDF of a document such as an invoice or contract, reads the text using OCR, and sends that text to an AI model via a LiteLLM proxy to extract specific data fields as structured JSON. A confidence scoring system evaluates OCR quality. High-confidence results are written to a clean output file ready for downstream processing. Low-confidence documents are routed to a human review queue so that no bad data silently enters the system.

An optional AI correction pass attempts to fix common OCR character substitution errors before final extraction, reducing the rate of flagged documents without lowering the acceptance threshold. All configuration including model selection, confidence thresholds, file paths, and extraction fields is controlled from a single .env file with no changes to the code required.

## Prerequisites

- Python 3.10 or later (tested with 3.14)
- pip (Python package manager)
- LiteLLM proxy server running and accessible
- Tesseract OCR engine installed separately: https://github.com/tesseract-ocr/tesseract#installing-tesseract
- Environment variables configured in .env (see Setup)

## Setup

1. Clone or download this repository.
2. Install Python dependencies:
   pip install -r requirements.txt
3. Copy .env.template to .env and fill in your values:
   cp .env.template .env
4. Edit .env with your LiteLLM endpoint, API key, model name, thresholds, file paths, and extraction fields.
5. Ensure the LiteLLM proxy is running and reachable at the LITELLM_BASE_URL you configured.
6. Place your document at the path defined in INPUT_DOCUMENT_PATH.
7. Run the agent:
   python agent.py

## How to switch AI providers

Change the MODEL_NAME value in your .env file. Use any model name supported by your LiteLLM setup such as gpt-4o, gemini/gemini-2.0-flash, or deepseek/deepseek-chat. The base URL and API key stay the same. No changes to agent.py required.

## What NosisTech changed from the original

NosisTech rebuilt this agent from a LangChain-based Packt example to remove all LangChain dependencies and hardcoded values. Changes include:

- Replaced LangChain chains with direct OpenAI SDK calls routed through LiteLLM
- Removed all vector store and embedding code (not required for single-document extraction)
- All configuration including model, endpoints, thresholds, and extraction schema externalized in environment variables
- Added rate-limit resilience with exponential backoff
- Added an AI correction pass for borderline OCR confidence scores
- Improved error handling with user-friendly messages and no stack traces
- Dynamic extraction fields: add or remove fields by editing EXTRACTION_FIELDS in .env without touching agent.py
- Append-only review queue for flagged documents with timestamp and confidence score per entry

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.