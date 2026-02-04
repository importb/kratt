"""
Pytest configuration and fixtures.

Handles mocking of system-level modules (keyboard) that require input device access.
"""
import pytest
import sys
from unittest.mock import MagicMock, patch

mock_keyboard = MagicMock()
sys.modules['keyboard'] = mock_keyboard


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