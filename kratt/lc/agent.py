"""
Agent construction using LangChain's unified create_agent factory.

Builds a ReAct agent capable of using file system tools.
"""

from langchain_ollama import ChatOllama
from langchain.agents import create_agent
from kratt.lc.tools import get_langchain_tools


def build_agent(model_name: str, system_prompt: str):
    """
    Create an agent capable of using tools via function calling.

    Args:
        model_name: The Ollama model to use.
        system_prompt: The system instruction for the agent.

    Returns:
        A compiled agent runnable (LangChain StateGraph).
    """
    llm = ChatOllama(model=model_name, temperature=0.7)
    tools = get_langchain_tools()

    app = create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt
    )

    return app