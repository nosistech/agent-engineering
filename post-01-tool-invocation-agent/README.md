# Tool Invocation Agent

## What this agent does

This project shows the smallest useful version of tool invocation:

1. A user asks for something.
2. The model chooses one available tool.
3. Python runs that tool.
4. The tool result is printed.

The model does not calculate campaign metrics itself. It only chooses the tool. The trusted Python code reads the CSV and does the math.

## Available tools

- `spend_by_campaign` totals ad spend for each campaign.
- `clicks_by_month` totals clicks for each month.

## Prerequisites

- Python 3.11 or later
- A running LiteLLM endpoint
- A CSV file with `date`, `campaign_name`, `spend`, and `clicks` columns

## Setup

1. Copy `.env.template` to `.env`.
2. Fill in your LiteLLM base URL, model name, API key, and CSV path.
3. Run the default demo:

```bash
python agent.py
```

You can also pass a request:

```bash
python agent.py "Show me clicks by month"
```

No package install is required. The agent uses only the Python standard library.

## How to switch AI providers

Edit `MODEL_NAME` in `.env`. Because the agent calls LiteLLM, the code does not need to change when you switch between supported providers.

## What NosisTech changed from the original

This is an independent educational rebuild inspired by the architecture of the referenced framework or source project. It is not affiliated with, endorsed by, or presented as a replacement for the original project.

- Reduced the project to the core tool-invocation pattern.
- Removed keyword parsing so the model is responsible for choosing the tool.
- Removed pandas, matplotlib, chart files, and output folders.
- Kept the CSV as the trusted data source.
- Kept LiteLLM-compatible configuration through its OpenAI-compatible HTTP endpoint.
- Removed third-party Python dependencies.

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.
