import logging
from typing import Annotated, AsyncGenerator, List, Sequence

from langchain_core.documents import Document
from langchain_core.runnables import RunnableConfig
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import MemorySaver

# LangGraph and LLM imports for building the state graph.
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import BaseMessage, add_messages
from typing_extensions import TypedDict

from src.utils.dependency import get_indexer
from src.utils.logger import get_logger

# Initialize logger for the AgentService.
logger = get_logger("AgentService", logging.INFO)


# Define the structure of the state that the graph will use.
class State(TypedDict):
    # The "messages" key holds a list of conversation messages.
    messages: Annotated[Sequence[BaseMessage], add_messages]

class AgentService:
    """
    AgentService integrates document retrieval with a LangGraph streaming response.
    Given a user query, it retrieves relevant documents from the vector store, constructs
    a conversation context, and streams out the LLM response in real-time via LangGraph.
    """

    def __init__(self):
        # Initialize the vector store indexer dependency.
        self.indexer = get_indexer()

        # Set up a memory saver for checkpointing the state graph.
        self.memory = MemorySaver()

        # Create a state graph builder with the defined state structure.
        self.graph_builder = StateGraph(State)

        # Initialize the language model instance.
        # self.llm = ChatOllama(model="deepseek-r1:14b")
        self.llm = ChatGroq(model="deepseek-r1-distill-llama-70b")
        # self.llm = ChatOllama(model="llama3.2")

        # Define the chatbot node function for the graph.
        def chatbot_node(state: State) -> State:
            """
            Node function that invokes the language model using the provided conversation messages.
            It takes the current state, calls the LLM with the messages, and returns the updated state.
            """
            logger.info("Invoking LLM in chatbot node with state messages.")
            # Call the LLM synchronously using the current conversation messages.
            logger.info(f"Message sent to model: {state['messages'][-3:]}")
            response = self.llm.invoke(state["messages"][-3:])
            # Return the response wrapped in a dictionary under "messages".
            return {"messages": [response]}

        # Add the chatbot node to the state graph.
        self.graph_builder.add_node("chatbot", chatbot_node)
        # Create an edge from the graph's start node to the chatbot node.
        self.graph_builder.add_edge(START, "chatbot")
        # Create an edge from the chatbot node to the graph's end node.
        self.graph_builder.add_edge("chatbot", END)
        # Compile the state graph with the memory checkpoint.
        self.graph = self.graph_builder.compile(checkpointer=self.memory)

    def _retrieve_docs(self, query: str) -> List[Document]:
        """
        Retrieve documents relevant to the user query using the vector store retriever.

        Args:
            query (str): The user's query string.

        Returns:
            List[Document]: A list of retrieved Document objects.
        """
        logger.info(f"Retrieving documents for query: {query}")

        # Define search parameters (for example, retrieve the top 5 relevant docs).
        search_kwargs = {"k": 5}

        # Ensure that the vector store has been initialized.
        if not self.indexer.vector_store:
            raise RuntimeError("Vector store not initialized.")

        # Create a retriever from the vector store using similarity search.
        retriever = self.indexer.vector_store.as_retriever(
            search_type="similarity", search_kwargs=search_kwargs
        )

        # Retrieve documents for the given query.
        docs = retriever.invoke(query)

        for i, doc in enumerate(docs):
            logger.info(
                f"----------Documument {i}---------------------\n {doc.page_content}"
            )

        logger.info(f"Retrieved {len(docs)} documents for query: {query}")
        return docs

    async def stream_response(self, user_input: str) -> AsyncGenerator[str, None]:
        """
        Asynchronously streams the LLM's response from the state graph based on the user's input.
        It first retrieves relevant documents, builds the conversation context, and then streams
        the language model’s response in a non-blocking manner.

        Args:
            user_input (str): The user's input query.

        Yields:
            str: Chunks of the response content as they are generated.
        """
        # Retrieve documents that are relevant to the user query.
        docs = self._retrieve_docs(user_input)

        # Start building the conversation messages.
        messages = []
        if docs:
            # Combine the retrieved document contents to form context.
            context = "\n\n".join([doc.page_content for doc in docs])
            system_message = {
                "role": "system",
                "content": f"Use the following context to answer the question:\n{context}",
            }
            messages.append(system_message)

        # Append the user's input message.
        messages.append({"role": "user", "content": user_input})

        # Initialize the state for the LangGraph with the conversation messages.
        state: State = {"messages": messages}

        # Define a configuration for the graph execution.
        config: RunnableConfig = {"configurable": {"thread_id": "1"}}

        logger.info("Starting to stream response from the state graph.")

        # Stream the response asynchronously using the state graph's astream method.
        think_tag_open = False
        async for msg, metadata in self.graph.astream(
            state, config, stream_mode="messages"
        ):
            # If the streamed message has content, yield it.
            if msg.content == "<think>":
                think_tag_open = True
            elif msg.content == "</think>":
                think_tag_open = False
            elif not think_tag_open:
                print(msg.content)
                yield msg.content
