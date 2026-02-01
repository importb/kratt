"""
Tool definitions and execution for file search, math, etc.
Allows the model to invoke tools via function calling.
"""

import os
import subprocess
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
    Search for text in files using grep.

    Args:
        pattern (str): Regex pattern to search for.
        path (str): Directory path to search in. Defaults to current directory.
        file_pattern (str): File glob pattern (e.g., '*.py', '*.txt'). Defaults to all files.
        max_results (int): Maximum number of results to return. Defaults to 20.

    Returns:
        str: Formatted search results or error message.
    """
    try:
        expanded_path = os.path.expanduser(path)

        if not os.path.isdir(expanded_path):
            return f"Error: '{path}' is not a valid directory."

        if not pattern.strip():
            return "Error: Search pattern cannot be empty."

        safe_pattern = re.escape(pattern)

        cmd = [
            "grep",
            "-r",
            "--include=" + file_pattern,
            "-n",
            "-H",
            safe_pattern,
            expanded_path,
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 1:
            return f"No matches found for pattern '{pattern}' in {expanded_path}"

        if result.returncode != 0:
            return f"Search error: {result.stderr.strip()}"

        lines = result.stdout.strip().split("\n")[:max_results]

        if not lines or not lines[0]:
            return f"No matches found for pattern '{pattern}' in {expanded_path}"

        formatted = "Search results:\n"
        for i, line in enumerate(lines, 1):
            formatted += f"{i}. {line}\n"

        if len(result.stdout.strip().split("\n")) > max_results:
            formatted += f"\n(Showing {max_results} of {len(result.stdout.strip().split(chr(10)))} results)"

        return formatted

    except subprocess.TimeoutExpired:
        return "Error: Search timed out (limit 10 seconds)"
    except Exception as e:
        return f"Error during search: {str(e)}"


def find_files(
    name_pattern: str,
    path: str = ".",
    max_results: int = 20
) -> str:
    """
    Find files by name using find command.

    Args:
        name_pattern (str): Filename pattern to search for.
        path (str): Directory path to search in. Defaults to current directory.
        max_results (int): Maximum number of results to return.

    Returns:
        str: Formatted file list or error message.
    """
    try:
        expanded_path = os.path.expanduser(path)

        if not os.path.isdir(expanded_path):
            return f"Error: '{path}' is not a valid directory."

        if not name_pattern.strip():
            return "Error: File name pattern cannot be empty."

        cmd = [
            "find",
            expanded_path,
            "-type", "f",
            "-name", name_pattern,
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            return f"Search error: {result.stderr.strip()}"

        lines = result.stdout.strip().split("\n")
        if not lines or not lines[0]:
            return f"No files found matching '{name_pattern}' in {expanded_path}"

        limited_lines = lines[:max_results]

        formatted = "Found files:\n"
        for i, filepath in enumerate(limited_lines, 1):
            formatted += f"{i}. {filepath}\n"

        if len(lines) > max_results:
            formatted += f"\n(Showing {max_results} of {len(lines)} results)"

        return formatted

    except subprocess.TimeoutExpired:
        return "Error: Search timed out (limit 10 seconds)"
    except Exception as e:
        return f"Error during search: {str(e)}"


def get_tool_definitions() -> list[dict]:
    """
    Returns the tool definitions for Ollama's function calling.

    These definitions tell the model what tools are available and how to use them.
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "search_files",
                "description": (
                    "Search for text patterns in files within a directory using grep. "
                    "Useful for finding code, logs, or specific content in files."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": (
                                "Text or regex pattern to search for in files. "
                                "Example: 'def function_name', 'error', 'TODO'"
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
                                "File glob pattern to filter by (e.g., '*.py', '*.js', '*.txt'). "
                                "Defaults to '*' (all files)."
                            )
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results to return. Defaults to 20."
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
                    "Useful for locating specific files or exploring directory structure."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name_pattern": {
                            "type": "string",
                            "description": (
                                "Filename pattern to search for (supports wildcards). "
                                "Example: '*.py', 'config*', 'test_*.js'"
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
                            "description": "Maximum number of results to return. Defaults to 20."
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