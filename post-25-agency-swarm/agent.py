# MIT License, Copyright 2025 VRSEN / Agency Swarm contributors
import os
from dotenv import load_dotenv
load_dotenv()
import openai
from agency_swarm import Agent, Agency


def require_env(*names: str) -> None:
    missing = [name for name in names if not os.getenv(name)]
    if missing:
        raise SystemExit(
            "Missing required environment variables: "
            + ", ".join(missing)
            + ". Copy .env.template to .env and fill in the values."
        )


require_env("OPENAI_API_KEY", "MODEL")

openai.api_key = os.environ["OPENAI_API_KEY"]
MODEL = os.environ["MODEL"]

researcher = Agent(
    name="ResearcherAgent",
    description="Researches topics and provides structured 3-point research briefs",
    instructions=(
        "You are a research assistant. Given a topic, respond with exactly "
        "a 3-point structured research brief. Return only the brief, no additional commentary."
    ),
    model=MODEL,
    temperature=0.7,
)

writer = Agent(
    name="WriterAgent",
    description="Writes a 150-word summary based on a research brief",
    instructions=(
        "You are a writer. You will receive a research brief. Write a formatted "
        "150-word summary capturing the key points. Output only the summary, no extra commentary."
    ),
    model=MODEL,
    temperature=0.7,
)

ceo = Agent(
    name="CEOAgent",
    description="CEO agent that coordinates research and writing for content pipeline",
    instructions=(
        "You are a CEO. When a user asks about a topic:\n"
        "1. Send the topic to ResearcherAgent, asking for a 3-point research brief.\n"
        "2. Receive the brief, then send it to WriterAgent, asking for a 150-word summary.\n"
        "3. Combine the research brief and the summary into a final synthesis that includes both the points and the summary.\n"
        "Output the synthesis directly when done."
    ),
    model=MODEL,
    temperature=0.7,
)

agency = Agency(
    agency_chart=[
        ceo,
        [ceo, researcher],
        [ceo, writer],
    ],
)

if __name__ == "__main__":
    topic = "AI governance trends in 2025"
    final_output = agency.get_completion(topic)
    print(final_output)
