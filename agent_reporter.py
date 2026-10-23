"""Agent 4 - merges everything into the final compliance report."""
from crewai import Agent, Task

NAME = "Report Writer"
ICON = "📝"
DESCRIPTION = "Scores the risk and writes the final compliance report"


def create_agent(llm, tools):
    return Agent(
        role="Compliance Report Writer",
        goal="Write a clear, accurate compliance report that a non-expert can act on.",
        backstory=(
            "You turn technical audit findings into plain-language reports. You remove duplicate findings, "
            "never invent facts, and always calculate the risk score with your tool."
        ),
        llm=llm,
        tools=[tools["calculate_risk_score"]],
        allow_delegation=False,
        verbose=False,
        max_iter=4,
    )


def create_task(agent, context, callback):
    return Task(
        description=(
            "Combine the previous outputs into the final report. Remove duplicate findings, count the remaining issues "
            "by severity, call 'Calculate Risk Score' ONCE, then write the report in Markdown with these sections: "
            "# AI Customs Compliance Report; **Overall status** and score; ## Executive summary (max 3 simple sentences); "
            "## Issues (table with columns ID | Severity | Category | Finding | Recommended action); "
            "## Missing information; ## Regulatory flags (with rule IDs); ## Next steps (numbered). "
            "End with: 'AI-assisted screening, not legal advice. Please verify with a licensed customs broker.'"
        ),
        expected_output="A complete Markdown compliance report.",
        agent=agent,
        context=context,
        callback=callback,
    )
