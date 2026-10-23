"""Agent 2 - compares the documents with each other and checks the maths."""
from crewai import Agent, Task

NAME = "Cross-Document Validator"
ICON = "🔗"
DESCRIPTION = "Compares documents against each other and checks arithmetic"


def create_agent(llm, tools):
    return Agent(
        role="Cross-Document Validation Analyst",
        goal="Find every inconsistency between the shipping documents and every arithmetic error.",
        backstory=(
            "You are a meticulous customs auditor. You never trust a single document: you compare parties, "
            "quantities, weights, values and dates across all of them, and you use your tools for every check."
        ),
        llm=llm,
        tools=[tools["compare_field"], tools["check_arithmetic"]],
        allow_delegation=False,
        verbose=False,
        max_iter=8,
    )


def create_task(agent, context, callback):
    return Task(
        description=(
            "Using the extracted data, cross-check the documents. "
            "1) Call 'Compare Field Across Documents' once for each field that appears in two or more documents "
            "(consignee, shipper, package count, gross weight, goods description, reference numbers; max 6 calls). "
            "2) Call 'Check Line Arithmetic' for each invoice line item (max 4 calls) and compare the sum of lines with the invoice total. "
            "3) Check date logic by reasoning: invoice date should be on or before the shipped-on-board date. "
            "Report each discrepancy as V1, V2... with severity (CRITICAL / MAJOR / MINOR), the field, and the value in each document. "
            "End with the count of CRITICAL, MAJOR and MINOR issues."
        ),
        expected_output="A numbered list of discrepancies with severity and values, then severity counts.",
        agent=agent,
        context=context,
        callback=callback,
    )
