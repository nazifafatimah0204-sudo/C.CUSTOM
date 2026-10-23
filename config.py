"""Settings + the Groq LLM connection used by every agent."""
import os

# Turn off CrewAI telemetry/tracing prompts (must be set before crewai is imported)
os.environ["OTEL_SDK_DISABLED"] = "true"
os.environ["CREWAI_TRACING_ENABLED"] = "false"

from crewai import LLM  # noqa: E402

GROQ_BASE_URL = "https://api.groq.com/openai/v1"

# Real Groq model IDs shown in the sidebar
MODELS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "llama-3.3-70b-versatile",
]


def get_llm(api_key: str, model_id: str) -> LLM:
    """Connect CrewAI to Groq through Groq's OpenAI-compatible endpoint.

    NOTE: CrewAI removes one leading 'openai/' from the model name, so we add
    one extra 'openai/' in front. Groq then receives the exact model ID.
    """
    return LLM(
        model="openai/" + model_id,
        custom_openai=True,
        base_url=GROQ_BASE_URL,
        api_key=api_key,
        temperature=0.1,
        max_tokens=1800,
    )
