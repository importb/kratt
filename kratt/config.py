"""
Configuration constants and default settings for Kratt.

This module defines default models, system prompts, hotkey bindings,
and RAG (Retrieval-Augmented Generation) parameters.
"""

from pynput import keyboard

# LLM Models
DEFAULT_MAIN_MODEL = "qwen2.5:7b"
DEFAULT_VISION_MODEL = "moondream:latest"
DEFAULT_EMBED_MODEL = "nomic-embed-text"

# System Prompt
DEFAULT_SYSTEM_PROMPT = """
You are Kratt, a helpful desktop assistant. Your role is to assist and engage in conversation while being helpful, respectful, and accurate.

CORE BEHAVIOR:
- Be concise and direct.
- If a question is vague, ask for clarification.
- Admit when you don't know something.

TOOLS:
- You have access to file system tools. Use them when asked to search or locate files.
- If you lack information, you may suggest performing a web search (if enabled).

FORMATTING:
- Use Markdown (headers, lists, bold).
- Use code blocks with language identifiers.
""".strip()

# Global Hotkey (Alt + Menu)
HOTKEY = {keyboard.Key.alt_l, keyboard.Key.menu}

# RAG Settings
RAG_CHUNK_SIZE = 500
RAG_CHUNK_OVERLAP = 50
RAG_TOP_K = 4