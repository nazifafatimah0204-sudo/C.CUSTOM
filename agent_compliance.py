"""Agent 3 - checks the shipment against customs rules using RAG and screening tools."""
from crewai import Agent, Task

NAME = "Compliance Reviewer"
ICON = "⚖️"
DESCRIPTION = "Checks rules with RAG, validates HS codes, screens restricted goods"


def create_agent(llm, tools):
    return Agent(
        role="Customs Compliance Reviewer",
        goal="Identify regulatory problems and missing information, citing the exact rule from the knowledge base.",
        backstory=(
            "You are a customs compliance officer. You never rely on memory for rules: you search the "
            "regulations knowledge base first and cite the rule ID, for example [DOC-001]."
        ),
        llm=llm,
        tools=[tools["search_regulations"], tools["validate_hs_code"], tools["screen_restricted_goods"]],
        allow_delegation=False,
        verbose=False,
        max_iter=8,
    )


def create_task(agent, context, callback):
    return Task(
        description=(
            "Review the shipment for regulatory issues. "
            "1) Call 'Search Customs Regulations' for up to 3 focused queries (for example: required invoice content, "
            "incoterm and freight consistency, dangerous or restricted goods, valuation). "
            "2) Call 'Validate HS Code' for each distinct HS code found. "
            "3) Call 'Screen Restricted Goods' once, passing all goods descriptions. "
            "Report findings as C1, C2... with severity (CRITICAL / MAJOR / MINOR), the rule ID, and why it matters. "
            "Also list required information that is MISSING (for example Incoterm, signature, importer tax ID)."
        ),
        expected_output="Numbered compliance findings with severity and rule IDs, plus a list of missing required information.",
        agent=agent,
        context=context,
        callback=callback,
    )
