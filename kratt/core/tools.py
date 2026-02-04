"""
Tool definitions and execution for file search, math, etc.
Allows the model to invoke tools via function calling.
"""

import os
import re
from pathlib import Path
from typing import Any


def search_files(
        pattern: str,
        path: str = ".",
        file_pattern: str = "*",
        max_results: int = 20
) -> str:
    """
    Search for text patterns in files using Python (cross-platform).

    Args:
        pattern (str): Text or regex pattern to search for.
        path (str): Directory path to search in. Defaults to current
                    directory.
        file_pattern (str): File glob pattern (e.g., '*.py', '*.txt').
                            Defaults to all files.
        max_results (int): Maximum number of results to return.
                           Defaults to 20.

    Returns:
        str: Formatted search results or error message.
    """
    try:
        search_path = Path(path).expanduser().resolve()

        if not search_path.is_dir():
            return f"Error: '{path}' is not a valid directory."

        if not pattern.strip():
            return "Error: Search pattern cannot be empty."

        # Compile regex pattern once
        try:
            regex = re.compile(pattern)
        except re.error:
            # If not a valid regex, treat as literal string
            regex = re.compile(re.escape(pattern))

        results = []
        processed_files = 0

        # Use rglob for cross-platform file matching
        for filepath in search_path.rglob(file_pattern):
            if not filepath.is_file():
                continue

            processed_files += 1
            if len(results) >= max_results:
                break

            try:
                with open(filepath, 'r', encoding='utf-8',
                          errors='ignore') as f:
                    for line_num, line in enumerate(f, 1):
                        if regex.search(line):
                            relative_path = filepath.relative_to(
                                search_path)
                            results.append(
                                f"{relative_path}:{line_num}:"
                                f"{line.rstrip()}"
                            )
                            if len(results) >= max_results:
                                break
            except (IOError, OSError):
                # Skip files that can't be read
                pass

        if not results:
            return (
                f"No matches found for pattern '{pattern}' in "
                f"{search_path}"
            )

        formatted = "Search results:\n"
        for i, result in enumerate(results, 1):
            formatted += f"{i}. {result}\n"

        # Count total matches if we hit the limit
        total_matches = len(results)
        if processed_files > 0 and total_matches >= max_results:
            formatted += (
                f"\n(Showing {max_results} results. "
                f"Adjust max_results to see more.)"
            )

        return formatted

    except Exception as e:
        return f"Error during search: {str(e)}"


def find_files(
        name_pattern: str,
        path: str = ".",
        max_results: int = 20
) -> str:
    """
    Find files by name pattern using Python (cross-platform).

    Args:
        name_pattern (str): Filename pattern to search for (glob syntax).
        path (str): Directory path to search in. Defaults to current
                    directory.
        max_results (int): Maximum number of results to return.

    Returns:
        str: Formatted file list or error message.
    """
    try:
        search_path = Path(path).expanduser().resolve()

        if not search_path.is_dir():
            return f"Error: '{path}' is not a valid directory."

        if not name_pattern.strip():
            return "Error: File name pattern cannot be empty."

        results = []

        # Use rglob for recursive pattern matching
        for filepath in search_path.rglob(name_pattern):
            if filepath.is_file():
                results.append(str(filepath))
                if len(results) >= max_results:
                    break

        if not results:
            return (
                f"No files found matching '{name_pattern}' in "
                f"{search_path}"
            )

        formatted = "Found files:\n"
        for i, filepath in enumerate(results, 1):
            formatted += f"{i}. {filepath}\n"

        if len(results) >= max_results:
            formatted += (
                f"\n(Showing {max_results} results. "
                f"Adjust max_results to see more.)"
            )

        return formatted

    except Exception as e:
        return f"Error during search: {str(e)}"


def get_tool_definitions() -> list[dict]:
    """
    Returns the tool definitions for Ollama's function calling.

    These definitions tell the model what tools are available and how
    to use them.
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "search_files",
                "description": (
                    "Search for text patterns in files within a "
                    "directory. Useful for finding code, logs, or "
                    "specific content in files."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": (
                                "Text or regex pattern to search for "
                                "in files. Example: 'def "
                                "function_name', 'error', 'TODO'"
                            )
                        },
                        "path": {
                            "type": "string",
                            "description": (
                                "Directory path to search in. "
                                "Can be relative or absolute. "
                                "Defaults to current directory."
                            )
                        },
                        "file_pattern": {
                            "type": "string",
                            "description": (
                                "File glob pattern to filter by "
                                "(e.g., '*.py', '*.js', '*.txt'). "
                                "Defaults to '*' (all files)."
                            )
                        },
                        "max_results": {
                            "type": "integer",
                            "description": (
                                "Maximum number of results to return. "
                                "Defaults to 20."
                            )
                        }
                    },
                    "required": ["pattern"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "find_files",
                "description": (
                    "Find files by name pattern within a directory. "
                    "Useful for locating specific files or exploring "
                    "directory structure."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name_pattern": {
                            "type": "string",
                            "description": (
                                "Filename pattern to search for "
                                "(supports wildcards). "
                                "Example: '*.py', 'config*', "
                                "'test_*.js'"
                            )
                        },
                        "path": {
                            "type": "string",
                            "description": (
                                "Directory path to search in. "
                                "Can be relative or absolute. "
                                "Defaults to current directory."
                            )
                        },
                        "max_results": {
                            "type": "integer",
                            "description": (
                                "Maximum number of results to return. "
                                "Defaults to 20."
                            )
                        }
                    },
                    "required": ["name_pattern"]
                }
            }
        }
    ]


def execute_tool(tool_name: str, **kwargs: Any) -> str:
    """
    Execute a tool by name with the given arguments.

    Args:
        tool_name (str): Name of the tool to execute.
        **kwargs: Arguments to pass to the tool.

    Returns:
        str: Result of tool execution.
    """
    if tool_name == "search_files":
        return search_files(**kwargs)
    elif tool_name == "find_files":
        return find_files(**kwargs)
    else:
        return f"Unknown tool: {tool_name}"
