# NosisTech Micro Research Agent

## What This Agent Does

This educational agent demonstrates the core research loop behind GPT Researcher without accessing the internet. It accepts a fictional research question, asks a language model to produce a small research plan, matches that plan against local fictional source packets, and asks the model to write a cautious summary grounded only in those packets.

The build teaches the plan, gather, publish architecture in one readable Python file. It does not scrape websites, search the live internet, process real documents, or claim that its output is accurate, complete, or professionally reliable.

## Prerequisites

- Python 3.14.2 tested
- pip
- A running LiteLLM proxy reachable from your environment
- A valid API key for your chosen model provider, configured through LiteLLM

## Setup

Clone this repository, copy `.env.template` to `.env`, and fill in your environment-specific values.

Install dependencies:

    pip install -r requirements.txt

Run the agent:

    python agent.py

## How to Switch AI Providers

Change `MODEL_NAME` in your `.env` file to any model your LiteLLM proxy supports. No code changes are needed.

## Educational Use and Liability Note

This project is an educational rebuild for learning and architectural review. It is not legal, compliance, security, financial, academic, or professional advice. It is not a production system, certification, audit result, research assurance tool, or guarantee of any outcome. For real environments, consult qualified professionals and validate independently. Do not use this project to process sensitive, confidential, personal, legal, financial, or security incident data.

## What NosisTech Changed from the Original

This is an independent educational rebuild inspired by the architecture of GPT Researcher. It is not affiliated with, endorsed by, certified by, or presented as a replacement for the original project. The goal is to isolate one architectural pattern in a small, reviewable implementation.

- Removed live web search, scraping, browser automation, frontend, backend, LangChain, LangGraph, vector stores, and deployment infrastructure.
- Replaced the original research system with a small LiteLLM-compatible educational pattern that uses fictional local source packets.
- Kept only the architecture needed to demonstrate the plan, gather, publish research loop.

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.
