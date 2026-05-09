# MIT License, Copyright 2025 Packt
import os
import json
import tempfile
import logging
import time
from typing import Optional, List, Dict, Any
import openai
from dotenv import load_dotenv

load_dotenv()

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
REQUIRED_ENV_VARS = [
    "LITELLM_BASE_URL",
    "MODEL_NAME",
    "LITELLM_API_KEY",
]
MEMORY_FILE_PATH = os.getenv("MEMORY_FILE_PATH", "memory.json")
PRIORITY_KEYWORDS = os.getenv(
    "PRIORITY_KEYWORDS", "urgent,critical,emergency"
).split(",")

# ----------------------------------------------------------------------
# Logging
# ----------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("memory_agent")


# ----------------------------------------------------------------------
# MemoryStore
# ----------------------------------------------------------------------
class MemoryStore:
    """
    Persists interaction records to a JSON file with atomic writes.
    """

    def __init__(self) -> None:
        """Load memory from file or start with empty list."""
        self._file_path = MEMORY_FILE_PATH
        self._records: List[Dict[str, Any]] = []
        if os.path.exists(self._file_path):
            try:
                with open(self._file_path, "r", encoding="utf-8") as f:
                    self._records = json.load(f)
                logger.info("Loaded %d records from %s", len(self._records), self._file_path)
            except (json.JSONDecodeError, OSError):
                logger.warning("Could not read memory file; starting fresh.")
                self._records = []
        else:
            logger.info("No existing memory file; starting fresh.")

    def save(self, interaction: Dict[str, Any]) -> None:
        """
        Append an interaction record and atomically persist the full list.
        """
        self._records.append(interaction)
        fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(self._file_path) or ".")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as tf:
                json.dump(self._records, tf, indent=2, ensure_ascii=False)
            os.replace(temp_path, self._file_path)
        except OSError as e:
            os.unlink(temp_path)
            raise e

    def retrieve(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Find the most relevant past interaction based on word overlap.
        Returns the highest-scoring record or None.
        """
        if not self._records:
            return None
        query_words = set(query.lower().split())
        best_score = 0
        best_record = None
        for rec in self._records:
            rec_words = set(rec.get("user_input", "").lower().split())
            score = len(query_words & rec_words)
            if score > best_score:
                best_score = score
                best_record = rec
        if best_record:
            logger.info(
                "Prior context found (score=%d, timestamp=%s)",
                best_score,
                best_record.get("timestamp", "unknown"),
            )
        return best_record


# ----------------------------------------------------------------------
# PlanningAgent
# ----------------------------------------------------------------------
class PlanningAgent:
    """
    Breaks a high-level goal into sequential subtasks and executes them.
    """

    def __init__(self, llm_client: openai.OpenAI) -> None:
        """Accept the LiteLLM client and read model name from environment."""
        self._client = llm_client
        self._model = os.getenv("MODEL_NAME")

    def plan(self, goal: str) -> List[str]:
        """
        Ask the LLM for a numbered list of subtasks to achieve the goal.
        Returns a list of task strings.
        """
        system_prompt = (
            "You are a business planning assistant. Given a goal, produce a "
            "numbered list of sequential subtasks required to achieve it. "
            "Return only the numbered list, one task per line, with no extra commentary."
        )
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": goal},
            ],
            temperature=0.2,
        )
        content = response.choices[0].message.content.strip()
        tasks = []
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            for sep in (".", ")", "-"):
                idx = line.find(sep)
                if idx > 0 and line[:idx].isdigit():
                    task = line[idx + 1:].strip()
                    if task:
                        tasks.append(task)
                    break
        logger.info("Planning produced %d subtasks", len(tasks))
        return tasks

    def execute(self, task_list: List[str]) -> None:
        """
        Log and execute each task in sequential order.
        """
        for i, task in enumerate(task_list, 1):
            logger.info("Executing task %d: %s", i, task)
            logger.info("Completed task %d", i)


# ----------------------------------------------------------------------
# DecisionAgent
# ----------------------------------------------------------------------
class DecisionAgent:
    """
    Evaluates user input across priority, complexity, and memory to pick a strategy:
    AUTONOMOUS (score 3-4), GUIDED (score 5), ESCALATE (score 6).
    """

    def __init__(self, llm_client: openai.OpenAI, memory: MemoryStore) -> None:
        """Accept the LiteLLM client and a MemoryStore instance."""
        self._client = llm_client
        self._model = os.getenv("MODEL_NAME")
        self._memory = memory
        self._priority_keywords = [kw.strip().lower() for kw in PRIORITY_KEYWORDS]

    def score_request(self, user_input: str) -> tuple[int, Optional[Dict[str, Any]]]:
        """
        Compute a total score (3-6) based on priority, complexity, and memory.
        Returns (total_score, memory_record).
        """
        input_lower = user_input.lower()
        priority_score = 2 if any(
            kw in input_lower for kw in self._priority_keywords
        ) else 1

        word_count = len(user_input.split())
        complexity_score = 2 if word_count > 20 else 1

        memory_record = self._memory.retrieve(user_input)
        memory_score = 1 if memory_record else 2

        total = priority_score + complexity_score + memory_score
        return total, memory_record

    def decide(self, user_input: str) -> str:
        """
        Map the total score to a strategy string.
        """
        total, _ = self.score_request(user_input)
        if total <= 4:
            strategy = "AUTONOMOUS"
        elif total == 5:
            strategy = "GUIDED"
        else:
            strategy = "ESCALATE"
        logger.info(
            "Decision: strategy=%s (score=%d for input: '%s')",
            strategy, total, user_input[:80],
        )
        return strategy

    def respond(self, user_input: str) -> str:
        """
        Full response pipeline: decide strategy, build prompt, call LLM, log and save.
        """
        strategy = self.decide(user_input)
        total_score, memory_record = self.score_request(user_input)

        memory_context = ""
        if memory_record:
            memory_context = (
                "Previous interaction ("
                + memory_record["timestamp"]
                + "): User said: '"
                + memory_record["user_input"]
                + "' Agent responded: '"
                + memory_record["agent_response"]
                + "'"
            )

        system_prompt = (
            "You are a business assistant for NosisTech LLC. "
            "Your response strategy is: " + strategy + ". "
        )
        if strategy == "ESCALATE":
            system_prompt += (
                "Inform the user that the request has been escalated to a human "
                "manager who will follow up shortly. "
            )
        system_prompt += (
            "Use the following past interaction context if helpful: " + memory_context
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ]

        max_retries = 3
        agent_response = ""
        for attempt in range(max_retries):
            try:
                response = self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    temperature=0.5,
                )
                agent_response = response.choices[0].message.content.strip()
                break
            except openai.RateLimitError:
                if attempt == max_retries - 1:
                    raise
                wait = 2 ** (attempt + 1)
                logger.warning("Rate limited; retrying in %d seconds...", wait)
                time.sleep(wait)
            except openai.OpenAIError as e:
                logger.error("LLM call failed: %s", str(e))
                raise

        if strategy == "ESCALATE":
            logger.info(
                "ESCALATED: timestamp=%s input='%s' score=%d",
                time.strftime("%Y-%m-%dT%H:%M:%S"),
                user_input[:80],
                total_score,
            )

        interaction = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "user_input": user_input,
            "agent_response": agent_response,
            "strategy_used": strategy,
        }
        self._memory.save(interaction)

        return agent_response


# ----------------------------------------------------------------------
# Startup helpers
# ----------------------------------------------------------------------
def check_environment() -> None:
    """Verify all required env vars are set; exit with clear message if not."""
    missing = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
    if missing:
        print("ERROR: Missing required environment variables:")
        for var in missing:
            print("  - " + var)
        print("Please set them in .env and try again.")
        exit(1)


def validate_input(text: str) -> str:
    """Reject empty or too long inputs; return the string otherwise."""
    if not text or not text.strip():
        raise ValueError("Input cannot be empty.")
    if len(text) > 2000:
        raise ValueError("Input exceeds maximum length of 2000 characters.")
    return text.strip()


def setup_llm_client() -> openai.OpenAI:
    """Create an OpenAI client pointed at the LiteLLM proxy."""
    base_url = os.getenv("LITELLM_BASE_URL")
    api_key = os.getenv("LITELLM_API_KEY")
    return openai.OpenAI(
        base_url=base_url,
        api_key=api_key,
    )


# ----------------------------------------------------------------------
# Main demonstration
# ----------------------------------------------------------------------
def main() -> None:
    """Run a planning demo and two decision demonstration scenarios."""
    check_environment()

    model = os.getenv("MODEL_NAME")
    print("Active model: " + model)

    try:
        client = setup_llm_client()
    except Exception as e:
        logger.error("Failed to initialize LLM client: %s", str(e))
        exit(1)

    memory = MemoryStore()

    # Planning demonstration
    plan_agent = PlanningAgent(client)
    goal = "Launch a client onboarding workflow for NosisTech LLC"
    logger.info("Planning for goal: %s", goal)
    try:
        tasks = plan_agent.plan(goal)
        plan_agent.execute(tasks)
    except Exception as e:
        logger.error("Planning failed: %s", str(e))

    # Decision demonstrations
    decision_agent = DecisionAgent(client, memory)

    # Case 1: Routine request, should score AUTONOMOUS
    input1 = "Please send the welcome packet to new client Apex Dynamics."
    logger.info("Decision demo 1: %s", input1)
    try:
        response1 = decision_agent.respond(input1)
        logger.info("Agent response: %s", response1)
    except Exception as e:
        logger.error("Decision demo 1 failed: %s", str(e))

    # Case 2: Urgent multi-word request, should score ESCALATE
    input2 = (
        "urgent: The compliance audit for NosisTech's government contract is "
        "failing and we have only two days to fix the encryption settings "
        "before the deadline. This is critical."
    )
    logger.info("Decision demo 2: %s", input2)
    try:
        response2 = decision_agent.respond(input2)
        logger.info("Agent response: %s", response2)
    except Exception as e:
        logger.error("Decision demo 2 failed: %s", str(e))


if __name__ == "__main__":
    main()
