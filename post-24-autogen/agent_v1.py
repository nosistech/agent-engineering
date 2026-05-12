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

user_proxy = autogen.UserProxyAgent(
    name="user_proxy",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=2,
    is_termination_msg=lambda x: "ANALYSIS COMPLETE" in x.get("content", ""),
    code_execution_config=False,
)

assistant = autogen.AssistantAgent(
    name="assistant",
    system_message=(
        "You are a strategic business analyst. When asked to analyze a company, produce a structured competitive analysis "
        "with three sections: Market Position, Key Risks, and One Strategic Recommendation. End your final response with "
        "the exact phrase ANALYSIS COMPLETE."
    ),
    llm_config=llm_config,
)

user_proxy.initiate_chat(
    assistant,
    message="Produce a competitive analysis for a mid-size SaaS company entering the AI governance market in Latin America.",
)