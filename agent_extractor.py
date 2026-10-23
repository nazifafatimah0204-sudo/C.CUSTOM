"""Agent 1 - reads every document and pulls out the key fields."""
from crewai import Agent, Task

NAME = "Document Extractor"
ICON = "🔍"
DESCRIPTION = "Reads each document and extracts the key fields"


def create_agent(llm, tools):
    return Agent(
        role="Customs Document Extraction Specialist",
        goal="Extract the key fields from every customs document accurately, without guessing.",
        backstory=(
            "You are a customs broker's assistant who reads invoices, packing lists and bills of lading "
            "all day. You only report what is written in the documents and write MISSING for anything absent."
        ),
        llm=llm,
        tools=[tools["inspect_documents"]],
        allow_delegation=False,
        verbose=False,
        max_iter=4,
    )


def create_task(agent, callback):
    return Task(
        description=(
            "Call the 'Inspect Documents' tool ONCE with document_name='all'. Then, for EACH document, list: "
            "document type, reference number, date, shipper/seller, consignee/buyer, notify party, goods description, "
            "HS codes, quantities, package count, gross and net weight, volume, currency and total value, Incoterm, "
            "country of origin, ports/vessel, container numbers, freight terms, signature present (yes/no). "
            "Write MISSING for anything not found. Keep the answer compact and factual, no opinions."
        ),
        expected_output="One compact block of extracted fields per document, with MISSING markers.",
        agent=agent,
        callback=callback,
    )
