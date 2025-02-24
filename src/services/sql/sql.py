from dotenv import load_dotenv
from langchain import hub
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from langchain_openai import AzureChatOpenAI

from src.services.sql.agent import create_react_agent

load_dotenv()

db = SQLDatabase.from_uri(
    "postgresql://postgres:Amadis%40123@192.168.1.93:5432/llm_chat"
)
# llm = ChatGroq(model="deepseek-r1-distill-llama-70b", temperature=0)
# llm = ChatGroq(model="gemma2-9b-it", temperature=0)
# llm = ChatGroq(model="mixtral-8x7b-32768", temperature=0)
# llm = ChatGroq(model="qwen-2.5-coder-32b", temperature=0)
# llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
# llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
# llm = ChatOllama(model="llama3.2", temperature=0)
# llm = ChatOllama(model="llama3-groq-tool-use:70b", temperature=0)
llm = AzureChatOpenAI()

system_message = """You are an agent designed to interact with a SQL database.
Given an input question, create a syntactically correct postgresql query to run, then look at the results of the query and return the answer.
You can order the results by a relevant column to return the most interesting examples in the database.
Never query for all the columns from a specific table, only ask for the relevant columns given the question.
You have access to tools for interacting with the database.
Only use the below tools. Only use the information returned by the below tools to construct your final answer.
You MUST double check your query before executing it. If you get an error while executing a query, rewrite the query and try again.

DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the database.

To start you should ALWAYS look at the tables in the database to see what you can query.
Do NOT skip this step.
Then you should query the schema of the most relevant tables.

**IMPORTANT**
ALWAYS start to look at the avilable tables and and get schema for the tables that relates to user question. Then generate query.\
"""


toolkit = SQLDatabaseToolkit(db=db, llm=llm)
tools = toolkit.get_tools()


print("======= System Message =====")
print(system_message)


agent_executer = create_react_agent(llm, tools, prompt=system_message)

question = "What is the average of total cost?"


def sql_agent():
    """""" ""
    for step in agent_executer.stream(
        {"messages": [{"role": "user", "content": question}]},
        stream_mode="values",
    ):
        step["messages"][-1].pretty_print()
