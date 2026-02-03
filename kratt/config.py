"""
Configuration constants, default settings, and settings persistence for Kratt.

This module defines default models, system prompts, hotkey bindings,
RAG (Retrieval-Augmented Generation) parameters, and handles loading/saving
user settings to a JSON file.
"""

from pynput import keyboard
import json
from pathlib import Path
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
- Keep responses scannable.

TOOLS:
- You have access to file system tools. Use them when asked to search or locate files.

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

CONFIG_DIR = Path.home() / ".config" / "kratt"
SETTINGS_FILE = CONFIG_DIR / "settings.json"


def get_default_settings() -> dict:
    """Returns a dictionary of the default application settings."""
    return {
        "main_model": DEFAULT_MAIN_MODEL,
        "vision_model": DEFAULT_VISION_MODEL,
        "system_prompt": DEFAULT_SYSTEM_PROMPT,
    }


def load_settings() -> dict:
    """
    Loads user settings from the JSON file.

    If the file doesn't exist or is invalid, returns default settings.
    Merges loaded settings with defaults to handle missing keys.
    """
    defaults = get_default_settings()
    if not SETTINGS_FILE.is_file():
        return defaults

    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            user_settings = json.load(f)

        # Merge with defaults to ensure all keys are present
        defaults.update(user_settings)
        return defaults
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading settings: {e}. Using defaults.")
        return get_default_settings()


def save_settings(settings: dict) -> None:
    """
    Saves the provided settings dictionary to the JSON file.

    Args:
        settings: The dictionary of settings to save.
    """
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
    except IOError as e:
        print(f"Error saving settings: {e}")