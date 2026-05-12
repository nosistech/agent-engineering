# Post 24 - AutoGen Framework - NosisTech LLC
import os
from dotenv import load_dotenv
import autogen

load_dotenv()

llm_config = {
    "config_list": [
        {
            "model": os.environ["MODEL_NAME"],
            "api_key": os.environ["LITELLM_API_KEY"],
            "base_url": os.environ["LITELLM_BASE_URL"],
        }
    ],
    "cache_seed": None,
}

if not os.path.exists("coding"):
    os.makedirs("coding")

executor = autogen.UserProxyAgent(
    name="executor",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=5,
    code_execution_config={"work_dir": "coding", "use_docker": False},
    is_termination_msg=lambda x: "EXECUTION COMPLETE" in x.get("content", ""),
)

coder = autogen.AssistantAgent(
    name="coder",
    system_message=(
        "You are a Python programmer. When given a data task, write a complete Python script in a single code block. "
        "After the executor runs your code and returns output, review the output. If it is correct, respond with a summary "
        "of what the script did followed by the exact phrase EXECUTION COMPLETE. If there is an error, diagnose it, "
        "rewrite the script, and try again."
    ),
    llm_config=llm_config,
)

executor.initiate_chat(
    coder,
    message=(
        "Write a Python script that takes this string: '14, 7, 23, 9, 41, 5, 18, 33, 2, 27' "
        "and calculates the mean, median, and standard deviation. Print a formatted summary with labels "
        "for each result. Do not use any external libraries. Use only the Python standard library."
    ),
)