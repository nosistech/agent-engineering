# (c) 2026 NosisTech LLC. Original implementation.
import os
import sys
import time
import argparse
import yaml
from dotenv import load_dotenv
from openai import OpenAI, APIError, APIConnectionError, APITimeoutError, RateLimitError

load_dotenv()

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def check_required_env_vars():
    """Verify all required environment variables are set before execution."""
    required = ["LITELLM_BASE_URL", "MODEL_NAME", "LITELLM_API_KEY"]
    missing = [var for var in required if not os.getenv(var)]
    if missing:
        print("Missing required environment variables: " + ", ".join(missing))
        print("Please set them in your .env file based on .env.template")
        sys.exit(1)


def load_agent_config():
    """Load and validate agents.yaml, returning researcher and writer definitions."""
    config_path = "agents.yaml"
    if not os.path.exists(config_path):
        print("Configuration file agents.yaml not found. Please create it from the provided template.")
        sys.exit(1)
    try:
        with open(config_path, "r") as config_file:
            config = yaml.safe_load(config_file)
    except yaml.YAMLError as yaml_error:
        print("agents.yaml is not valid YAML. Please check the file format.")
        print("Details: " + str(yaml_error))
        sys.exit(1)

    required_keys = ["role", "goal", "backstory"]
    for agent_name in ["researcher", "writer"]:
        if agent_name not in config:
            print("Missing required agent definition in agents.yaml: " + agent_name)
            sys.exit(1)
        agent_conf = config[agent_name]
        for key in required_keys:
            if key not in agent_conf:
                print("Agent " + agent_name + " is missing required field: " + key)
                sys.exit(1)

    return config["researcher"], config["writer"]


def build_system_prompt(agent_conf):
    """Construct a system prompt string from agent YAML configuration."""
    prompt = "Role: " + agent_conf["role"] + "\n"
    prompt += "Goal: " + agent_conf["goal"] + "\n"
    prompt += "Backstory: " + agent_conf["backstory"] + "\n"
    tools = agent_conf.get("tools", [])
    if tools:
        prompt += "Tools available: " + ", ".join(tools) + "\n"
    return prompt


def run_agent(client, model_name, system_prompt, user_message, max_retries=3):
    """Send a request to the LLM and return the response with exponential backoff on rate limits."""
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.3,
                max_tokens=1200,
            )
            return response.choices[0].message.content.strip()
        except RateLimitError:
            wait_seconds = 2 ** attempt
            print("Rate limit reached. Retrying in " + str(wait_seconds) + " seconds (attempt " + str(attempt + 1) + " of " + str(max_retries) + ")")
            time.sleep(wait_seconds)
        except APIConnectionError:
            print("Could not connect to the LiteLLM endpoint. Please verify your LITELLM_BASE_URL is correct and the proxy is running.")
            sys.exit(1)
        except APITimeoutError:
            print("The LiteLLM request timed out. Please check the upstream model or try a smaller topic.")
            sys.exit(1)
        except APIError as api_error:
            print("API error encountered: " + str(api_error))
            sys.exit(1)

    print("Maximum retry attempts reached due to rate limiting. Please try again later.")
    sys.exit(1)


def main():
    """Run the two-agent researcher and writer workflow."""
    check_required_env_vars()

    model_name = os.getenv("MODEL_NAME")
    base_url = os.getenv("LITELLM_BASE_URL")
    api_key = os.getenv("LITELLM_API_KEY")

    print("Active model: " + model_name + " via LiteLLM", flush=True)

    researcher_conf, writer_conf = load_agent_config()

    parser = argparse.ArgumentParser(description="Run the two-agent researcher and writer workflow.")
    parser.add_argument("topic", nargs="+", help="Topic to research and summarize")
    args = parser.parse_args()
    topic = " ".join(args.topic).strip()

    if not topic:
        print("Error: Topic cannot be empty. Please provide a topic as a command line argument.")
        sys.exit(1)

    client = OpenAI(base_url=base_url, api_key=api_key, timeout=60)

    researcher_prompt = build_system_prompt(researcher_conf)
    print("[RESEARCHER] Starting research on: " + topic, flush=True)
    researcher_output = run_agent(client, model_name, researcher_prompt, topic)
    print("[RESEARCHER] Complete. Handing off to Writer...", flush=True)

    writer_prompt = build_system_prompt(writer_conf)
    print("[WRITER] Creating clear business summary...", flush=True)
    final_summary = run_agent(client, model_name, writer_prompt, researcher_output)

    print("\n===== RESEARCHER FINDINGS =====")
    print(researcher_output)
    print("\n===== FINAL BUSINESS SUMMARY =====")
    print(final_summary)


if __name__ == "__main__":
    main()
