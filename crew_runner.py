"""Builds the crew and runs it in a background thread so the UI can show live progress."""
import time
import warnings

from crewai import Crew, Process

import agent_compliance
import agent_extractor
import agent_reporter
import agent_validator
from config import get_llm
from tools import build_tools

# Harmless pydantic notice about callbacks; hide it so logs stay clean
warnings.filterwarnings("ignore", message="function callbacks cannot be serialized")

AGENT_MODULES = [agent_extractor, agent_validator, agent_compliance, agent_reporter]


def friendly_error(e: Exception) -> str:
    msg = str(e)
    low = msg.lower()
    if "429" in msg or "rate limit" in low or "rate_limit" in low or "tokens per" in low:
        return ("Groq rate limit reached (free plans allow about 8,000 tokens per minute). "
                "Wait 1-2 minutes, increase the cool-down in the sidebar, reduce the characters per document, "
                "or upgrade your Groq plan. Details: " + msg[:300])
    if "401" in msg or "invalid_api_key" in low or "invalid api key" in low:
        return "Groq rejected the API key. Check that you pasted it correctly (it starts with gsk_)."
    if "connection error" in low or "failed to connect" in low or "timed out" in low:
        return "Could not reach Groq. Check your internet connection and that the API key is correct, then try again."
    if "413" in msg or "too large" in low:
        return "The request was too large. Reduce 'Max characters per document' in the sidebar. Details: " + msg[:300]
    return msg[:600]


def run_analysis(docs, kb, api_key, model_id, max_chars, cooldown, state):
    """Runs in a worker thread. Never call Streamlit (st.*) in here."""
    try:
        llm = get_llm(api_key, model_id)
        tools = build_tools(docs, kb, state, max_chars)
        n = len(AGENT_MODULES)

        def make_callback(i):
            def callback(output):
                state.finish_task(i, getattr(output, "raw", str(output)))
                if i < n - 1 and cooldown > 0:
                    for left in range(int(cooldown), 0, -1):
                        state.set_status(f"Cooling down {left}s to respect Groq token limits...")
                        time.sleep(1)
            return callback

        agents = [m.create_agent(llm, tools) for m in AGENT_MODULES]
        t1 = agent_extractor.create_task(agents[0], make_callback(0))
        t2 = agent_validator.create_task(agents[1], [t1], make_callback(1))
        t3 = agent_compliance.create_task(agents[2], [t1], make_callback(2))
        t4 = agent_reporter.create_task(agents[3], [t1, t2, t3], make_callback(3))

        crew = Crew(agents=agents, tasks=[t1, t2, t3, t4], process=Process.sequential, verbose=False)
        state.log("Crew started: 4 agents will work one after another")
        result = crew.kickoff()
        state.final = getattr(result, "raw", str(result))
        state.set_status("Finished")
    except Exception as e:  # show a readable message in the UI
        state.error = friendly_error(e)
        state.log("Error: " + state.error[:200])
    finally:
        state.done = True
