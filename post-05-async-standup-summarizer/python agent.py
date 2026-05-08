## How to switch AI providers

Edit MODEL_NAME in your .env file. No other change is needed. The agent
routes all calls through LiteLLM, so any provider your proxy supports works
identically.

## What this agent does not handle

- Live integrations with Slack, Teams, or any chat platform
- Scheduled or automated execution
- Reading from shared workspaces or databases
- Real-time notifications or follow-up actions
- Multi-file input (single JSON file only)

(c) 2026 NosisTech LLC. Licensed under CC BY 4.0. Use freely, just credit us.