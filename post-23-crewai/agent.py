# (c) 2026 NosisTech LLC. Original implementation.

import os
from dotenv import load_dotenv

# Disable CrewAI telemetry before any other crewai import
os.environ["CREWAI_TELEMETRY"] = "false"

from crewai import Agent, Crew, LLM, Process, Task
from crewai.tools import tool


REQUIRED_ENV = ("LITELLM_BASE_URL", "MODEL_NAME", "LITELLM_API_KEY", "RESEARCH_TOPIC")


@tool("Research Tool")
def gather_research(topic: str) -> str:
    """Return structured demo research notes about the topic."""
    return (
        f"1. Overview of {topic} in the context of AI governance: "
        "enterprises need clear ownership, risk review, and deployment standards.\n"
        f"2. Regulatory landscape: {topic} should be mapped against applicable AI, privacy, "
        "security, and sector-specific requirements before rollout.\n"
        f"3. Implementation challenges: {topic} often stalls when accountability, data access, "
        "and review checkpoints are unclear.\n"
        f"4. Best practices: NosisTech would start with role ownership, documented controls, "
        "model monitoring, and escalation paths.\n"
        f"5. Future outlook: {topic} will likely become more important as enterprise AI moves "
        "from pilots into production workflows."
    )


def require_env() -> None:
    missing = [key for key in REQUIRED_ENV if not os.getenv(key)]
    if missing:
        raise SystemExit(f"Missing required environment variables: {', '.join(missing)}")
    if not os.getenv("RESEARCH_TOPIC", "").strip():
        raise SystemExit("Error: RESEARCH_TOPIC is empty.")
    print(f"Active model: {os.getenv('MODEL_NAME')}")


def make_agent(role: str, goal: str, backstory: str, llm: LLM, tools: list | None = None) -> Agent:
    return Agent(role=role, goal=goal, backstory=backstory, tools=tools or [], llm=llm, verbose=True)


def make_task(description: str, expected_output: str, agent: Agent) -> Task:
    return Task(description=description, expected_output=expected_output, agent=agent)


def main() -> None:
    """Run the three-agent content research and synthesis crew."""
    load_dotenv()
    require_env()

    llm = LLM(
        model=os.getenv("MODEL_NAME"),
        base_url=os.getenv("LITELLM_BASE_URL"),
        api_key=os.getenv("LITELLM_API_KEY"),
    )

    agents = [
        make_agent(
            "Senior Research Analyst",
            "Find key facts and context on the given topic",
            "You are a NosisTech research specialist in AI governance, compliance, and emerging tech trends.",
            llm,
            [gather_research],
        ),
        make_agent(
            "Content Strategist",
            "Produce a clear executive summary from research findings",
            "You translate complex technical research into accessible briefings for executives and clients.",
            llm,
        ),
        make_agent(
            "Editorial Reviewer",
            "Check the draft summary for clarity, accuracy, and completeness",
            "You ensure every deliverable meets high standards of accuracy and client readiness.",
            llm,
        ),
    ]

    tasks = [
        make_task(
            "Gather key facts and context on the topic: {topic}. Use your research tool to produce a structured bullet list.",
            "At least 5 findings covering overview, regulations, challenges, best practices, and outlook.",
            agents[0],
        ),
        make_task(
            "Using the research findings, write a concise two-paragraph executive briefing.",
            "A factual two-paragraph summary, no longer than 150 words total.",
            agents[1],
        ),
        make_task(
            "Review the draft summary. Respond with APPROVED or REVISION NEEDED followed by specific fixes.",
            "Either APPROVED alone or REVISION NEEDED followed by a bullet list of improvement items.",
            agents[2],
        ),
    ]

    crew = Crew(
        agents=agents,
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
    )

    try:
        result = crew.kickoff(inputs={"topic": os.getenv("RESEARCH_TOPIC").strip()})
        print("\n--- CREW OUTPUT ---")
        print(result)
    except Exception as e:
        raise SystemExit(f"Agent run failed: {e}") from e


if __name__ == "__main__":
    main()
