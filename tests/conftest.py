"""
Pytest configuration and fixtures.

Handles mocking of system-level modules that require external services.
"""
from unittest.mock import patch

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