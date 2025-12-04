import asyncio
import logging

from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

from src.core.config import MODEL_NAME

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def dynamic_persona_provider(context: ReadonlyContext) -> str:
    """Generates system instruction dynamically based on Session State.
        Source: ADK Docs - State Injection

    Args:
        context (ReadonlyContext): The read-only context provided by the runner.

    Returns:
        str: The generated system instruction.
    """
    use_role = context.state.get("user:role", "Intern")
    current_topic = context.state.get("current_topic", "General Chat")

    return (
        f"You are a strict Senior Tech Lead. "
        f"You are currently mentoring a user with the rank of '{use_role}'. "
        f"The current discussion topic is locked to: '{current_topic}'. "
        f"If the user asks about anything else, politely refuse and steer back to {current_topic}. "
        f"Keep answers concise and technical."
    )

root_agent = LlmAgent(
    name="TechLeadAgent",
    model=MODEL_NAME,
    instruction=dynamic_persona_provider,
    output_key="last_mentor_advice"
)

async def main() -> None:
    session_service = InMemorySessionService()
    app_name = "EnterpriseApp"

    runner = Runner(
        agent=root_agent,
        app_name=app_name,
        session_service=session_service
    )

    user_id = "dev_001"
    session_id = "session_alpha"

    initial_state = {
        "user:role": "Junior Developer",
        "current_topic": "Memory Management"
    }

    print(f"--- INITIALIZING SESSION: {initial_state} ---")

    session = await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
        state=initial_state
    )
    logger.info(f"Session created successfully: {session.id} for user {user_id}")

    prompts = [
        "Hi, can you help me with Python?",
        "Okay, tell me about Stack and Heap."
    ]

    for prompt in prompts:
        print(f"\nUSER: {prompt}")

        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=Content(parts=[Part(text=prompt)])
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        print(f"MENTOR: {part.text}", end="", flush=True)
        print()

    updated_session = await session_service.get_session(
        app_name=app_name, user_id=user_id, session_id=session_id
    )

    if updated_session is not None:
        saved_advice = updated_session.state.get("last_mentor_advice")
        if saved_advice:
            logger.info(f"State 'last_mentor_advice': {str(saved_advice)[:50]}...")
        else:
            logger.warning("State 'last_mentor_advice' is empty!")


if __name__=="__main__":
    asyncio.run(main=main())
