"""
Pytest configuration and fixtures.

Handles mocking of system-level modules (pynput, keyboard) that require
input device access or display servers.
"""
import sys
from unittest.mock import MagicMock, patch

# Mock pynput
mock_pynput = MagicMock()
mock_pynput_keyboard = MagicMock()

# Create a mock Key object
mock_key = MagicMock()
mock_key.ctrl_l = "ctrl_l"
mock_key.ctrl_r = "ctrl_r"
mock_key.alt_l = "alt_l"
mock_key.alt_r = "alt_r"
mock_key.shift_l = "shift_l"
mock_key.shift_r = "shift_r"

mock_pynput_keyboard.Key = mock_key
mock_pynput.keyboard = mock_pynput_keyboard

sys.modules['pynput'] = mock_pynput
sys.modules['pynput.keyboard'] = mock_pynput_keyboard

# Mock keyboard
mock_keyboard = MagicMock()
sys.modules['keyboard'] = mock_keyboard


import pytest


@pytest.fixture(autouse=True)
def mock_ollama():
    """Mock Ollama client to avoid connection attempts."""
    with patch('ollama.list') as mock_list, \
            patch('ollama.generate') as mock_gen, \
            patch('ollama.chat') as mock_chat:
        mock_list.return_value = {"models": []}
        mock_gen.return_value = {"response": ""}
        mock_chat.return_value = {"message": {"content": ""}}
        yield


@pytest.fixture
def qapp():
    """Provide QApplication instance for Qt tests."""
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app