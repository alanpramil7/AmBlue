from src.services.assistant.graph import researcher
from src.utils.dependency import get_indexer

indexer = get_indexer()


report_structure = """
1. Introduction
- Brief overview of the research topic or question.
- Purpose and scope of the report.

2. Main Body
- For each section (e.g., Section 1, Section 2, Section 3, etc.):
  - Provide a subheading related to the key aspect of the research.
  - Include explanation, findings, and supporting details.

3. Key Takeaways
- Bullet points summarizing the most important insights or findings.

4. Conclusion
- Final summary of the research.
- Implications or relevance of the findings.
"""

# Define the initial state
initial_state = {
    "user_instruction": "What is the TechStack used in cloudcadi?",
}

# Langgraph researcher config
config = {
    "configurable": {
        "enable_web_search": False,
        "report_structure": report_structure,
        "max_search_queries": 3,
    }
}

# Init vector store
# Must add your own documents in the /files directory before running this script
vector_db = indexer.vector_store


def run_assiatant():
    # Run the researcher graph
    for output in researcher.stream(initial_state, config=config):
        for key, value in output.items():
            print(f"Finished running: **{key}**")
            print(value)
