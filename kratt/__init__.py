"""
Kratt - A lightweight desktop AI assistant.

Provides a chat interface for local LLMs via Ollama, featuring
vision capabilities and web search integration.
"""

__version__ = "0.1.0"
__author__ = "Rainer Vana"

from kratt.config import (
    DEFAULT_MAIN_MODEL,
    DEFAULT_VISION_MODEL,
    DEFAULT_SYSTEM_PROMPT,
)

__all__ = [
    "DEFAULT_MAIN_MODEL",
    "DEFAULT_VISION_MODEL",
    "DEFAULT_SYSTEM_PROMPT",
]