import operator
from typing import Annotated, TypedDict


class ResearcherState(TypedDict):
    user_instruction: str
    research_queries: list[str]
    search_summaries: Annotated[list, operator.add]
    current_position: int
    final_answer: str


class ResearcherStateInput(TypedDict):
    user_instruction: str


class ResearcherStateOutput(TypedDict):
    final_answer: str


class QuerySearchState(TypedDict):
    query: str
    web_search_results: list
    retrived_documents: list
    are_documents_relevant: bool
    search_summaries: list[str]


class QuerySearchStateInput(TypedDict):
    query: str


class QuerySearchStateResult(TypedDict):
    query: str
    search_summaries: list[str]
