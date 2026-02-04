"""
Unit tests for UI components and main window functionality.

Tests for:
- Chat bubble rendering and styling
- Main window interactions and state management
- Settings dialog configuration
- File attachment and image handling
"""

import pytest
from unittest.mock import MagicMock, patch
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from kratt.ui.main_window import MainWindow
from kratt.ui.chat_bubble import ChatBubble
from kratt.ui.settings_dialog import SettingsDialog


@pytest.fixture
def qapp():
    """Provide QApplication instance for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def main_window(qapp, mocker):
    """
    Provide a configured MainWindow instance for testing.

    Mocks external dependencies like Ollama settings.
    """
    mocker.patch(
        "kratt.ui.main_window.load_settings",
        return_value={
            "main_model": "test_model",
            "vision_model": "test_vision",
            "system_prompt": "Test system prompt",
        },
    )
    window = MainWindow()
    return window


class TestChatBubble:
    """Test cases for chat message bubble rendering."""

    def test_chat_bubble_user_message(self, qapp):
        """
        Test that user message bubble renders with correct styling.

        Verifies user-specific UI presentation.
        """
        bubble = ChatBubble("Test message", is_user=True)

        assert bubble.is_user is True
        assert "Test message" in bubble.label.text()

    def test_chat_bubble_ai_message(self, qapp):
        """
        Test that AI message bubble renders with correct styling.

        Verifies AI-specific UI presentation.
        """
        bubble = ChatBubble("AI response", is_user=False)

        assert bubble.is_user is False
        assert "AI response" in bubble.label.text()

    def test_chat_bubble_with_image_attachment(self, qapp):
        """
        Test that chat bubble handles image attachments correctly.

        Verifies image preview functionality.
        """
        bubble = ChatBubble("Message with image", is_user=True, image_path="missing.png")

        # Image label should be created even if file is missing
        assert bubble.image_label is not None

    def test_chat_bubble_metadata_display(self, qapp):
        """
        Test that AI bubble displays generation metadata.

        Verifies display of performance metrics.
        """
        bubble = ChatBubble("Response", is_user=False)
        bubble.set_metadata(duration=1.5, token_count=10, model_name="test_model")

        # Metadata should be visible and contain stats
        assert not bubble.metadata_label.isHidden()
        assert "1.50s" in bubble.metadata_label.text() or "1.5s" in bubble.metadata_label.text()

    def test_chat_bubble_update_text_streaming(self, qapp):
        """
        Test that chat bubble text can be updated for streaming responses.

        Verifies dynamic text updating during generation.
        """
        bubble = ChatBubble("Initial", is_user=False)
        bubble.update_text("Updated text")

        assert "Updated text" in bubble.label.text()


class TestMainWindow:
    """Test cases for main application window functionality."""

    def test_main_window_initialization(self, main_window):
        """
        Test that main window initializes with correct default state.

        Verifies initial configuration and UI setup.
        """
        assert main_window.is_processing is False
        assert len(main_window.history) >= 1
        assert main_window.txt_input is not None

    def test_main_window_send_message_adds_to_history(self, main_window, mocker):
        """
        Test that sending a message adds it to chat history.

        Verifies message recording and history updates.
        """
        mocker.patch(
            "kratt.ui.main_window.OllamaWorker"
        )

        main_window.txt_input.setText("Test message")
        main_window.send_message()

        # Should have system prompt + user message
        user_messages = [h for h in main_window.history if h["role"] == "user"]
        assert len(user_messages) == 1
        assert user_messages[0]["content"] == "Test message"

    def test_main_window_disables_input_during_processing(self, main_window, mocker):
        """
        Test that input controls are disabled during message processing.

        Verifies proper UI state management.
        """
        mocker.patch("kratt.ui.main_window.OllamaWorker")

        main_window.txt_input.setText("Message")
        main_window.send_message()

        assert main_window.is_processing is True
        assert not main_window.txt_input.isEnabled()
        assert not main_window.btn_attach.isEnabled()

    def test_main_window_stream_update_appends_tokens(self, main_window):
        """
        Test that streaming updates append tokens to response buffer.

        Verifies incremental token accumulation.
        """
        main_window.current_ai_bubble = ChatBubble("", is_user=False)
        main_window.chat_layout.addWidget(main_window.current_ai_bubble)

        main_window._update_stream("Hello ")
        main_window._update_stream("World")

        assert main_window.full_response_buffer == "Hello World"

    def test_main_window_finalize_stream_saves_response(self, main_window):
        """
        Test that stream finalization saves response to history.

        Verifies response persistence.
        """
        main_window.current_ai_bubble = ChatBubble("", is_user=False)
        main_window.chat_layout.addWidget(main_window.current_ai_bubble)
        main_window.full_response_buffer = "Final response"

        main_window._finalize_stream(duration=1.0, token_count=10)

        # Response should be in history
        assistant_messages = [
            h for h in main_window.history if h["role"] == "assistant"
        ]
        assert any("Final response" in h["content"] for h in assistant_messages)

    def test_main_window_new_chat_clears_history(self, main_window):
        """
        Test that new chat resets conversation history.

        Verifies history clearing functionality.
        """
        # Add messages to history
        main_window.history.append({"role": "user", "content": "test"})

        main_window.new_chat()

        # Should only have system message
        assert len(main_window.history) == 1
        assert main_window.history[0]["role"] == "system"

    def test_main_window_toggle_web_search(self, main_window):
        """
        Test that web search toggle can be enabled/disabled.

        Verifies web search state management.
        """
        assert main_window.is_web_enabled is False

        main_window._toggle_web_search()

        assert main_window.is_web_enabled is True

    def test_main_window_disables_web_when_image_attached(self, main_window, mocker):
        """
        Test that web search is disabled when image is attached.

        Verifies incompatibility handling between features.
        """
        mocker.patch(
            "PySide6.QtWidgets.QFileDialog.getOpenFileName",
            return_value=("/path/to/image.png", ""),
        )

        main_window.is_web_enabled = True
        main_window._select_or_clear_file()

        # Web search should be disabled
        assert main_window.is_web_enabled is False

    def test_main_window_force_stop_cancels_generation(self, main_window, mocker):
        """
        Test that force stop can cancel ongoing generation.

        Verifies generation interruption.
        """
        mock_worker = MagicMock()
        main_window.worker = mock_worker
        main_window.is_processing = True
        main_window.current_ai_bubble = ChatBubble("", is_user=False)
        main_window.chat_layout.addWidget(main_window.current_ai_bubble)

        main_window._force_stop()

        mock_worker.request_stop.assert_called_once()


class TestSettingsDialog:
    """Test cases for settings configuration dialog."""

    def test_settings_dialog_loads_current_settings(self, qapp, mocker):
        """
        Test that settings dialog loads current configuration.

        Verifies settings initialization.
        """
        mocker.patch(
            "ollama.list",
            return_value={
                "models": [
                    {"name": "test_model"},
                    {"name": "vision_model"},
                ]
            },
        )

        settings = {"main_model": "test_model", "vision_model": "vision_model"}
        dialog = SettingsDialog(settings)

        retrieved = dialog.get_settings()
        assert retrieved["main_model"] == "test_model"

    def test_settings_dialog_populates_models_from_ollama(self, qapp, mocker):
        """
        Test that settings dialog fetches available models from Ollama.

        Verifies Ollama integration.
        """
        mocker.patch(
            "ollama.list",
            return_value={"models": [
                {"name": "model1"},
                {"name": "model2"},
            ]},
        )

        dialog = SettingsDialog({})

        # Models should be available in combo boxes
        assert dialog.combo_text_model.count() >= 2

    def test_settings_dialog_handles_ollama_connection_error(self, qapp, mocker):
        """
        Test that settings dialog handles Ollama connection failures.

        Verifies graceful error handling.
        """
        mocker.patch("ollama.list", side_effect=Exception("Connection failed"))

        dialog = SettingsDialog({})

        # Dialog should still be usable
        assert dialog is not None

    def test_settings_dialog_updates_system_prompt(self, qapp, mocker):
        """
        Test that system prompt can be updated in settings.

        Verifies prompt modification functionality.
        """
        mocker.patch("ollama.list", return_value={"models": []})

        dialog = SettingsDialog({})
        new_prompt = "New system prompt"
        dialog.txt_prompt.setPlainText(new_prompt)

        settings = dialog.get_settings()
        assert settings["system_prompt"] == new_prompt


class TestMainWindowIntegration:
    """Integration tests for main window components working together."""

    def test_workflow_send_message_to_response(self, main_window, mocker):
        """
        Test complete workflow from sending message to receiving response.

        Verifies end-to-end message flow.
        """
        mocker.patch("kratt.ui.main_window.OllamaWorker")

        # Send message
        main_window.txt_input.setText("Hello AI")
        main_window.send_message()

        # Verify processing state
        assert main_window.is_processing is True
        assert main_window.txt_input.text() == ""

        # Simulate response
        main_window._update_stream("Response ")
        main_window._update_stream("text")
        main_window._finalize_stream(1.0, 2)

        # Verify final state
        assert main_window.is_processing is False
        assert "Response text" in main_window.full_response_buffer

    def test_workflow_new_chat_resets_state(self, main_window, mocker):
        """
        Test that new chat properly resets application state.

        Verifies complete state reset.
        """
        mocker.patch("kratt.ui.main_window.OllamaWorker")

        # Simulate message history
        main_window.history.append({"role": "user", "content": "test"})
        main_window.full_response_buffer = "response"

        main_window.new_chat()

        assert len(main_window.history) == 1
        assert main_window.full_response_buffer == ""
