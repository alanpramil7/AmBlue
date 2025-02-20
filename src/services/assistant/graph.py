import datetime
from typing import Literal

from langchain_core.runnables.config import RunnableConfig
from langgraph.graph import START, END, StateGraph
from langgraph.constants import Send

from src.services.assistant.config import Configuration
from src.services.assistant.prompts import (
    RELEVANCE_EVALUATOR_PROMPT,
    RESEARCH_QUERY_WRITER_PROMPT,
    REPORT_WRITER_PROMPT,
    SUMMARIZER_PROMPT,
)
from src.services.assistant.state import (
    QuerySearchState,
    QuerySearchStateInput,
    QuerySearchStateResult,
    ResearcherState,
    ResearcherStateInput,
    ResearcherStateOutput,
)
from src.services.assistant.utils import (
    Evaluation,
    Queries,
    format_docs_with_metadata,
    invoke_ollama,
    invoke_groq
)
from src.utils.dependency import get_indexer
from src.utils.logger import logger

BATCH_SIZE = 3
indexer = get_indexer()


def generate_researcher_queries(state: ResearcherState, config: RunnableConfig):
    logger.info("Generating researcher querry")
    user_instructions = state["user_instruction"]
    max_queries = config["configurable"].get("max_search_queries", 3)

    query_writter_prompt = RESEARCH_QUERY_WRITER_PROMPT.format(
        max_queries=max_queries, date=datetime.datetime.now().strftime("%Y/%m/%d %H:%M")
    )

    result = invoke_groq(
        # model="deepseek-r1:14b",
        system_prompt=query_writter_prompt,
        user_prompt=f"Generate research queries for this user instruction: {user_instructions}",
        output_format=Queries,
    )
    logger.info(f"Research Queries: \n {result.queries}")

    return {"research_queries": result.queries}


def search_querries(state: ResearcherState):
    logger.info("Generating Search Queries")
    current_position = state.get("current_position", 0)

    return {"current_position": current_position + BATCH_SIZE}


def generate_final_answer(state: ResearcherState, config: RunnableConfig):
    report_structure = config["configurable"].get("report_structure", "")
    answer_prompt = REPORT_WRITER_PROMPT.format(
        instruction=state["user_instruction"],
        report_structure=report_structure,
        information="\n\n--\n\n".join(state["search_summaries"]),
    )

    result = invoke_groq(
        # model="deepseek-r1:14b",
        system_prompt=answer_prompt,
        user_prompt=f"Generate a research summary using provided information.",
    )

    return {"final_answer": result}


def retrive_rag_document(state: QuerySearchState):
    logger.info("Retriving docs")
    query = state["query"]
    vector_store = indexer.vector_store
    retrevier = vector_store.as_retriever(
        search_type="similarity", search_kwargs={"k": 3}
    )
    documents = retrevier.invoke(query)

    return {"retrived_documents": documents}


def evaluate_retrived_docs(state: QuerySearchState):
    logger.info("Evaluating retrived docs")
    query = state["query"]
    retrived_docs = state["retrived_documents"]
    # logger.info(f"Retrived Docs: {retrived_docs}")
    evaluation_prompt = RELEVANCE_EVALUATOR_PROMPT.format(
        query=query, documents=format_docs_with_metadata(retrived_docs)
    )

    result = invoke_groq(
        # model="deepseek-r1:14b",
        system_prompt=evaluation_prompt,
        user_prompt=f"Evaluate the relevance of the retrived documets for this query: {query}",
        output_format=Evaluation,
    )
    
    logger.info(f"Is Document relevant: {result.is_relevant}")

    return {"are_documents_relevant": result.is_relevant}


def summarize_query_research(state: QuerySearchState):
    logger.info("Summarizing research")
    query = state["query"]
    information = None
    # if state['are_documents_relevant']:
    #     information = state["retrived_documents"]
    # else:
    #     print("Documents are not relvant")
    information = state["retrived_documents"]

    summary_prompt = SUMMARIZER_PROMPT.format(query=query, docmuents=information)

    summary = invoke_groq(
        # model="deepseek-r1:14b",
        system_prompt=summary_prompt,
        user_prompt=f"Generate a research summary fir this quey: {query}",
    )

    return {"search_summaries": [summary]}


def initiate_query_research(state: ResearcherState):
    logger.info("Initiating query research")
    # Get the next batch of queries
    queries = state["research_queries"]
    current_position = state["current_position"]
    batch_end = min(current_position, len(queries))
    current_batch = queries[current_position - BATCH_SIZE : batch_end]

    # Return the batch of queries to process
    return [Send("search_and_summarize_query", {"query": s}) for s in current_batch]


def check_more_queries(
    state: ResearcherState,
) -> Literal["search_querries", "generate_final_answer"]:
    """Check if there are more queries to process"""
    logger.info("Check for more queries")
    current_position = state.get("current_position", 0)
    if current_position < len(state["research_queries"]):
        return "search_querries"
    return "generate_final_answer"


query_search_subgraph = StateGraph(
    QuerySearchState, input=QuerySearchStateInput, output=QuerySearchStateResult
)

query_search_subgraph.add_node(retrive_rag_document)
query_search_subgraph.add_node(evaluate_retrived_docs)
query_search_subgraph.add_node(summarize_query_research)

query_search_subgraph.add_edge(START, "retrive_rag_document")
query_search_subgraph.add_edge("retrive_rag_document", "evaluate_retrived_docs")
query_search_subgraph.add_edge("evaluate_retrived_docs", "summarize_query_research")
query_search_subgraph.add_edge("summarize_query_research", END)

researcher_graph = StateGraph(
    ResearcherState,
    input=ResearcherStateInput,
    output=ResearcherStateOutput,
    config_schema=Configuration,
)

researcher_graph.add_node(generate_researcher_queries)
researcher_graph.add_node(search_querries)
researcher_graph.add_node("search_and_summarize_query", query_search_subgraph.compile())
researcher_graph.add_node(generate_final_answer)

researcher_graph.add_edge(START, "generate_researcher_queries")
researcher_graph.add_edge("generate_researcher_queries", "search_querries")
researcher_graph.add_conditional_edges(
    "search_querries", initiate_query_research, ["search_and_summarize_query"]
)
researcher_graph.add_conditional_edges("search_and_summarize_query", check_more_queries)
researcher_graph.add_edge("generate_final_answer", END)

researcher = researcher_graph.compile()
