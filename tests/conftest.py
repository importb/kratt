"""
Pytest configuration and fixtures.

Handles mocking of system-level modules (pynput) that require X11 in headless environments.
"""

import sys
import pytest
from enum import Enum
from unittest.mock import MagicMock, patch

class MockKey(Enum):
    """Mock keyboard key enum."""
    alt_l = "alt_l"
    menu = "menu"
    alt_r = "alt_r"
    ctrl_l = "ctrl_l"
    shift_l = "shift_l"


mock_keyboard = MagicMock()
mock_keyboard.Key = MockKey
mock_keyboard.Listener = MagicMock

mock_pynput = MagicMock()
mock_pynput.keyboard = mock_keyboard

sys.modules['pynput.keyboard'] = mock_keyboard
sys.modules['pynput._util'] = MagicMock()
sys.modules['pynput'] = mock_pynput


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
