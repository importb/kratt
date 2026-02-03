"""
LangChain tool wrappers for Kratt.
"""

from langchain_core.tools import tool
from kratt.core.tools import search_files as raw_search_files
from kratt.core.tools import find_files as raw_find_files


@tool
def search_files_tool(
    pattern: str,
    path: str = ".",
    file_pattern: str = "*",
    max_results: int = 20
) -> str:
    """
    Search for text patterns in files using grep.
    Useful for finding code definitions, specific text, or content within files.
    """
    return raw_search_files(pattern, path, file_pattern, max_results)


@tool
def find_files_tool(
    name_pattern: str,
    path: str = ".",
    max_results: int = 20
) -> str:
    """
    Find files by filename pattern (glob) within a directory.
    Useful for locating specific files or exploring project structure.
    """
    return raw_find_files(name_pattern, path, max_results)


def get_langchain_tools():
    """Returns the list of tools available to the agent."""
    return [search_files_tool, find_files_tool]