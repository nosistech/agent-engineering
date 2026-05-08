# Async Standup Summarizer

## What this agent does

The Async Standup Summarizer collects individual standup updates from team
members via a structured JSON file, then uses a large language model to
generate a concise three-line summary for each contributor. It then
synthesizes all individual summaries into a single consolidated team report
grouped by Completed This Period, In Progress, and Active Blockers.

This tool is built for distributed or asynchronous teams who want standup
discipline without requiring everyone online at the same time. It works with
any LLM provider reachable through a LiteLLM proxy. Changing the model
requires editing one line in the .env file and nothing else.

## Prerequisites

- Python 3.10 or newer (tested with Python 3.14.2)
- pip
- A running LiteLLM proxy server with your chosen model configured
- A standup_updates.json input file in the required format

## Setup

Copy the environment template and fill in your values: