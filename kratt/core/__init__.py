"""
Core backend logic (workers, search, hotkeys).
"""

from kratt.core.hotkey_manager import HotkeyManager
from kratt.core.worker import OllamaWorker

__all__ = ["HotkeyManager", "OllamaWorker"]
