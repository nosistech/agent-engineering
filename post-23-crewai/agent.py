# (c) 2026 NosisTech LLC. Original implementation.

import os
import sys
from dotenv import load_dotenv

# Disable CrewAI telemetry before any other crewai import
os.environ["CREWAI_TELEMETRY"] = "false"

from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import tool


@tool("Research Tool")
def gather_research(topic: str) -> str:
    """Return a structured bullet list of synthetic research findings about the topic."""
    return (
        f"1. Overview of {topic} in the context of AI governance: "
        f"NosisTech highlights that {topic} is a top concern for 76% of enterprise risk officers.\n"
        f"2. Regulatory landscape: Recent EU and US frameworks classify {topic} under high-risk "
        f"AI applications, requiring impact assessments.\n"
        f"3. Implementation challenges: Organizations cite unclear accountability structures "
        f"and lack of {topic} expertise as primary barriers.\n"
        f"4. Best practices: NosisTech recommends establishing a cross-functional {topic} "
        f"oversight committee and automated monitoring tools.\n"
        f"5. Future outlook: Analysts predict that {topic} will drive 40% of AI governance "
        f"spending by 2028."
    )


def main():
    """Run the three-agent content research and synthesis crew."""
    load_dotenv()

    required_vars = ["LITELLM_BASE_URL", "MODEL_NAME", "LITELLM_API_KEY", "RESEARCH_TOPIC"]
    missing = [v for v in required_vars if not os.getenv(v)]
    if missing:
        print(f"Missing required environment variables: {', '.join(missing)}")
        sys.exit(1)

    model_name = os.getenv("MODEL_NAME")
    print(f"Active model: {model_name}")

    research_topic = os.getenv("RESEARCH_TOPIC").strip()
    if not research_topic:
        print("Error: RESEARCH_TOPIC is empty.")
        sys.exit(1)

    llm = LLM(
        model=model_name,
        base_url=os.getenv("LITELLM_BASE_URL"),
        api_key=os.getenv("LITELLM_API_KEY")
    )

    research_agent = Agent(
        role="Senior Research Analyst",
        goal="Find key facts and context on the given topic",
        backstory=(
            "You are a NosisTech research specialist with a decade of experience in AI governance, "
            "compliance, and emerging tech trends. Your analysis is trusted by enterprise clients."
        ),
        tools=[gather_research],
        llm=llm,
        verbose=True
    )

    writer_agent = Agent(
        role="Content Strategist",
        goal="Produce a clear, structured plain-English summary from research findings",
        backstory=(
            "You are NosisTech's lead communications expert, translating complex technical "
            "research into accessible briefings for executives and clients."
        ),
        llm=llm,
        verbose=True
    )

    quality_agent = Agent(
        role="Editorial Reviewer",
        goal="Check the draft summary for clarity, accuracy, and completeness",
        backstory=(
            "You lead NosisTech's quality assurance team, ensuring every deliverable meets "
            "the highest standards of accuracy and client readiness."
        ),
        llm=llm,
        verbose=True
    )

    research_task = Task(
        description=(
            "Gather key facts and context on the topic: {topic}. "
            "Use your available research tool to produce a structured bullet list of findings."
        ),
        expected_output=(
            "A structured bullet list of at least 5 findings covering overview, "
            "regulations, challenges, best practices, and outlook."
        ),
        agent=research_agent
    )

    writing_task = Task(
        description=(
            "Using the research findings provided, write a two-paragraph plain-English summary "
            "suitable for an executive briefing. Keep it concise and factual."
        ),
        expected_output="A clean two-paragraph summary in plain language, no longer than 150 words total.",
        agent=writer_agent
    )

    quality_task = Task(
        description=(
            "Review the draft summary. Respond with APPROVED if it is clear, accurate, and complete, "
            "or REVISION NEEDED followed by a specific bullet list of what to fix."
        ),
        expected_output="Either 'APPROVED' alone or 'REVISION NEEDED' followed by a bullet list of improvement items.",
        agent=quality_agent
    )

    research_crew = Crew(
        agents=[research_agent, writer_agent, quality_agent],
        tasks=[research_task, writing_task, quality_task],
        process=Process.sequential,
        verbose=True
    )

    try:
        result = research_crew.kickoff(inputs={"topic": research_topic})
        print("\n--- CREW OUTPUT ---")
        print(result)
    except Exception as e:
        print(f"Agent run failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()