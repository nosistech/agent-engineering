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

research_agent = autogen.AssistantAgent(
    name="research_agent",
    system_message="Gather and summarize factual information on AI governance trends in enterprise settings. Keep responses under 200 words.",
    llm_config=llm_config,
)
critic_agent = autogen.AssistantAgent(
    name="critic_agent",
    system_message="Review the previous research response and identify exactly two gaps or weak claims. Keep responses under 150 words.",
    llm_config=llm_config,
)
synthesizer_agent = autogen.AssistantAgent(
    name="synthesizer_agent",
    system_message="Take the research and the critique and produce a final 250-word AI governance briefing for an enterprise client. End the briefing with the exact phrase BRIEFING COMPLETE.",
    llm_config=llm_config,
)

user_proxy = autogen.UserProxyAgent(
    name="user_proxy",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=0,
    code_execution_config=False,
    is_termination_msg=lambda x: "BRIEFING COMPLETE" in x.get("content", ""),
)

groupchat = autogen.GroupChat(
    agents=[user_proxy, research_agent, critic_agent, synthesizer_agent],
    messages=[],
    max_round=6,
    speaker_selection_method="auto",
)
manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config)

user_proxy.initiate_chat(
    manager,
    message="Produce an AI governance briefing for a financial services enterprise considering deploying autonomous agents in client-facing workflows.",
)