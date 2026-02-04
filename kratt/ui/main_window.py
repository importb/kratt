"""
Main application window.

Provides the draggable, frameless chat interface with message input,
history management, image attachment, web search toggle, and worker thread coordination.
"""

import os
from pathlib import Path
from PySide6.QtCore import Qt, Signal, QTimer, QSize
from PySide6.QtGui import QColor, QIcon
from PySide6.QtGui import QPixmap, QPainter, QFont
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QLabel,
    QScrollArea,
    QFrame,
    QApplication,
    QGraphicsDropShadowEffect,
    QFileDialog,
    QSystemTrayIcon,
    QMenu,
)
from kratt.config import (
    load_settings,
    save_settings,
)
from kratt.core.worker import OllamaWorker
from kratt.ui.chat_bubble import ChatBubble
from kratt.ui.settings_dialog import SettingsDialog


class MainWindow(QWidget):
    """
    Main draggable, frameless chat window.

    Manages user input, chat history, worker thread execution,
    and UI state during message generation. Supports system tray
    integration for minimized state.
    """

    def __init__(self) -> None:
        """Initialize the main window and set up all components."""
        super().__init__()
        self.old_pos = None
        self.app_settings = load_settings()

        self.history: list[dict] = []
        self.full_response_buffer = ""
        self.current_ai_bubble: ChatBubble | None = None
        self.is_processing = False
        self.is_web_enabled = False
        self.pending_image_path: str | None = None
        self.worker: OllamaWorker | None = None
        self.current_model_used = ""

        self._setup_ui()
        self._setup_tray()
        self.new_chat()

    def _setup_ui(self) -> None:
        """Initialize the UI components, styling, and window flags."""
        self.setWindowTitle("Kratt")
        self.resize(420, 680)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.setLayout(self.main_layout)

        self.container = QFrame()
        self.container.setObjectName("MainContainer")

        win_shadow = QGraphicsDropShadowEffect()
        win_shadow.setBlurRadius(30)
        win_shadow.setColor(QColor(0, 0, 0, 200))
        win_shadow.setOffset(0, 4)
        self.container.setGraphicsEffect(win_shadow)

        self.container_layout = QVBoxLayout()
        self.container_layout.setSpacing(0)
        self.container.setLayout(self.container_layout)
        self.main_layout.addWidget(self.container)

        self._setup_header()
        self._setup_chat_area()
        self._setup_input_area()
        self._center_window()

    def _setup_tray(self) -> None:
        """Set up system tray icon with context menu."""
        self.tray_icon = QSystemTrayIcon(self)

        # Create tray menu
        tray_menu = QMenu()

        action_show = tray_menu.addAction("Show")
        action_show.triggered.connect(self.show_window)

        action_hide = tray_menu.addAction("Hide")
        action_hide.triggered.connect(self.hide)

        tray_menu.addSeparator()

        action_quit = tray_menu.addAction("Quit")
        action_quit.triggered.connect(QApplication.quit)

        self.tray_icon.setContextMenu(tray_menu)

        self._create_tray_icon_pixmap()

        self.tray_icon.activated.connect(self._on_tray_icon_activated)

        self.tray_icon.show()

    def _create_tray_icon_pixmap(self) -> None:
        """Create a simple tray icon pixmap with 'K' letter."""
        pixmap = QPixmap(64, 64)
        pixmap.fill(QColor(230, 126, 34, 255))

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        font = QFont("Sans Serif", 32, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "K")

        painter.end()

        self.tray_icon.setIcon(QIcon(pixmap))

    def _on_tray_icon_activated(self, reason) -> None:
        """Handle tray icon activation (click)."""
        if reason in (
                QSystemTrayIcon.ActivationReason.Trigger,
                QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.show_window()

    def show_window(self) -> None:
        """Show the window and bring it to focus."""
        self.show()
        self.activateWindow()
        self.txt_input.setFocus()

    def _setup_header(self) -> None:
        """Set up the top bar with title, new chat, settings, and close buttons."""
        self.header = QFrame()
        self.header.setObjectName("Header")
        self.header_layout = QHBoxLayout()
        self.header_layout.setContentsMargins(16, 12, 16, 8)
        self.header.setLayout(self.header_layout)

        title = QLabel("Kratt")
        title.setObjectName("WinTitle")

        btn_new_chat = QPushButton("⟳")
        btn_new_chat.setObjectName("HeaderBtn")
        btn_new_chat.setFixedSize(28, 28)
        btn_new_chat.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_new_chat.setToolTip("New chat")
        btn_new_chat.clicked.connect(self.new_chat)

        btn_settings = QPushButton("⚙")
        btn_settings.setObjectName("HeaderBtn")
        btn_settings.setFixedSize(28, 28)
        btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_settings.setToolTip("Settings")
        btn_settings.clicked.connect(self._open_settings)

        btn_close = QPushButton("✕")
        btn_close.setObjectName("CloseBtn")
        btn_close.setFixedSize(28, 28)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self.hide)

        self.header_layout.addWidget(title)
        self.header_layout.addStretch()
        self.header_layout.addWidget(btn_new_chat)
        self.header_layout.addWidget(btn_settings)
        self.header_layout.addWidget(btn_close)
        self.container_layout.addWidget(self.header)

    def _setup_chat_area(self) -> None:
        """Set up the scrollable area where chat bubbles appear."""
        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("ChatScrollArea")
        self.scroll_area.setWidgetResizable(True)

        # Ensure the viewport is transparent
        self.scroll_area.viewport().setAutoFillBackground(False)
        self.scroll_area.viewport().setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.chat_widget = QWidget()
        self.chat_widget.setObjectName("ChatWidget")
        self.chat_widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)

        self.chat_layout = QVBoxLayout()
        self.chat_layout.setContentsMargins(8, 8, 8, 8)
        self.chat_layout.addStretch()
        self.chat_widget.setLayout(self.chat_layout)
        self.scroll_area.setWidget(self.chat_widget)
        self.container_layout.addWidget(self.scroll_area)

    def _get_tinted_icon(self, path: str, color_hex: str) -> QIcon:
        """
        Recolor an SVG icon using composition mode.

        Args:
            path: Path to the SVG file.
            color_hex: Target color as hex string (e.g., '#e67e22').

        Returns:
            QIcon with tinted color.
        """
        pixmap = QPixmap(path)
        painter = QPainter(pixmap)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), QColor(color_hex))
        painter.end()
        return QIcon(pixmap)

    def _setup_input_area(self) -> None:
        """Set up the input field, attachment, web toggle, and send buttons."""
        self.input_frame = QFrame()
        self.input_frame.setObjectName("InputFrame")
        self.input_layout = QHBoxLayout()
        self.input_layout.setContentsMargins(12, 8, 12, 14)
        self.input_layout.setSpacing(8)
        self.input_frame.setLayout(self.input_layout)

        self.res_path = Path(__file__).parent.parent / "resources"

        self.txt_input = QLineEdit()
        self.txt_input.setObjectName("ChatInput")
        self.txt_input.setPlaceholderText("Message Kratt...")
        self.txt_input.returnPressed.connect(self.send_message)

        # Web search button
        self.btn_web = QPushButton()
        self.btn_web.setObjectName("WebBtn")
        self.web_icon_path = str(self.res_path / "globe.svg")
        self.btn_web.setIconSize(QSize(14, 14))
        self.btn_web.setFixedSize(38, 38)
        self.btn_web.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_web.clicked.connect(self._toggle_web_search)

        # Image attachment button
        self.btn_attach = QPushButton()
        self.btn_attach.setObjectName("AttachBtn")
        self.attach_icon_path = str(self.res_path / "attachment.svg")
        self.btn_attach.setIconSize(QSize(14, 14))
        self.btn_attach.setFixedSize(38, 38)
        self.btn_attach.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_attach.clicked.connect(self._select_or_clear_file)

        # Send/Stop button
        self.btn_send = QPushButton()
        self.btn_send.setObjectName("SendBtn")
        send_icon_path = str(self.res_path / "send.svg")
        self.btn_send.setIcon(self._get_tinted_icon(send_icon_path, "#e67e22"))
        self.btn_send.setIconSize(QSize(16, 16))
        self.btn_send.setFixedSize(38, 38)
        self.btn_send.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_send.clicked.connect(self._on_send_button_clicked)

        # Update button styles and icons
        self._update_send_button_style()
        self._update_web_button_style()
        self._update_attach_button_style()

        self.input_layout.addWidget(self.txt_input)
        self.input_layout.addWidget(self.btn_web)
        self.input_layout.addWidget(self.btn_attach)
        self.input_layout.addWidget(self.btn_send)
        self.container_layout.addWidget(self.input_frame)

    def _refresh_style(self, widget: QWidget) -> None:
        """Forces Qt to re-evaluate the stylesheet for a specific widget."""
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def _toggle_web_search(self) -> None:
        """Toggle web search status (disabled while processing)."""
        if self.is_processing:
            return
        self.is_web_enabled = not self.is_web_enabled
        self._update_web_button_style()

    def _update_web_button_style(self) -> None:
        """Update web button appearance based on its enabled state."""
        self.btn_web.setProperty("active", self.is_web_enabled)
        self._refresh_style(self.btn_web)

        if self.is_web_enabled:
            self.btn_web.setIcon(self._get_tinted_icon(self.web_icon_path, "#e67e22"))
            self.btn_web.setToolTip("Web Search (On)")
        else:
            self.btn_web.setIcon(self._get_tinted_icon(self.web_icon_path, "#6b5c4c"))
            self.btn_web.setToolTip("Web Search (Off)")

    def _update_send_button_style(self) -> None:
        """Update send button icon and color based on processing state."""
        send_icon_path = str(self.res_path / "send.svg")
        stop_icon_path = str(self.res_path / "stop.svg")

        self.btn_send.setProperty("processing", self.is_processing)
        self._refresh_style(self.btn_send)

        if self.is_processing:
            self.btn_send.setIcon(self._get_tinted_icon(stop_icon_path, "#ff6b6b"))
            self.btn_send.setToolTip("Force Stop")
        else:
            self.btn_send.setIcon(self._get_tinted_icon(send_icon_path, "#0d0b09"))
            self.btn_send.setToolTip("Send message")

    def _on_send_button_clicked(self) -> None:
        """Handle send button click (send message or stop generation)."""
        if self.is_processing:
            self._force_stop()
        else:
            self.send_message()

    def _force_stop(self) -> None:
        """Signal the worker to stop text generation."""
        if not self.is_processing or self.worker is None:
            return
        self.worker.request_stop()
        if self.current_ai_bubble:
            msg = self.full_response_buffer + " *(stopped)*" if self.full_response_buffer else "*(stopped)*"
            self.current_ai_bubble.update_text(msg)

    def _on_worker_stopped(self) -> None:
        """Handle worker stop signal and finalize the response."""
        if self.full_response_buffer:
            self.history.append({"role": "assistant", "content": self.full_response_buffer})
        self._reset_ui_after_response()

    def _reset_ui_after_response(self) -> None:
        """Re-enable UI controls after generation finishes."""
        self.is_processing = False
        self.txt_input.setEnabled(True)
        self.btn_attach.setEnabled(True)
        self.btn_web.setEnabled(True)
        self._update_send_button_style()
        self.txt_input.setFocus()
        self._scroll_to_bottom()

    def _update_attach_button_style(self) -> None:
        """Update attachment button appearance based on whether a file is attached."""
        has_file = bool(self.pending_image_path)

        self.btn_attach.setProperty("has_file", has_file)
        self._refresh_style(self.btn_attach)

        if has_file:
            self.btn_attach.setIcon(self._get_tinted_icon(self.attach_icon_path, "#e67e22"))
            name = os.path.basename(self.pending_image_path)
            self.btn_attach.setToolTip(f"Attached: {name}\nClick to clear.")
        else:
            self.btn_attach.setIcon(self._get_tinted_icon(self.attach_icon_path, "#6b5c4c"))
            self.btn_attach.setToolTip("Attach image")

    def _select_or_clear_file(self) -> None:
        """
        Handle attachment button logic.

        If a file is attached, clicking clears it.
        Otherwise, opens a file dialog for image selection.
        """
        if self.is_processing:
            return

        if self.pending_image_path:
            self.pending_image_path = None
            self._update_attach_button_style()
            self.txt_input.setFocus()
            return

        start_dir = str(Path.home())
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select image",
            start_dir,
            "Images (*.png *.jpg *.jpeg *.webp *.bmp *.gif)"
        )
        if not file_path:
            return

        self.pending_image_path = os.path.abspath(file_path)
        self._update_attach_button_style()
        self.txt_input.setFocus()

        # Disable web search when an image is attached
        if self.is_web_enabled:
            self.is_web_enabled = False
            self._update_web_button_style()

    def _center_window(self) -> None:
        """Center the window on the primary screen."""
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def mousePressEvent(self, event) -> None:
        """Enable window dragging on left mouse button press."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.windowHandle().startSystemMove()

    def mouseMoveEvent(self, event) -> None:
        pass

    def mouseReleaseEvent(self, event) -> None:
        pass

    def _open_settings(self) -> None:
        """Open the settings dialog (disabled while processing)."""
        if self.is_processing:
            return
        dlg = SettingsDialog(self.app_settings, self)
        if dlg.exec():
            self.app_settings = dlg.get_settings()
            save_settings(self.app_settings)

            # Update system prompt for the current session if the chat is new
            if len(self.history) <= 1:
                self.history[0]["content"] = self.app_settings["system_prompt"]

    def new_chat(self) -> None:
        """Reset conversation history and clear UI for a new chat."""
        if self.is_processing:
            return
        if self.worker is not None:
            if self.worker.isRunning():
                self.worker.wait()
            self.worker.deleteLater()
            self.worker = None

        self.history = [{"role": "system", "content": self.app_settings["system_prompt"]}]
        self.full_response_buffer = ""
        self.current_ai_bubble = None
        self.pending_image_path = None
        self.current_model_used = ""

        self._update_attach_button_style()

        # Remove all chat bubbles (keep only the layout's stretch)
        while self.chat_layout.count() > 1:
            item = self.chat_layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()
        self.txt_input.setFocus()

    def send_message(self) -> None:
        """
        Validate input, update UI, and start the worker thread.

        Creates a user message bubble, disables input, and instantiates
        the OllamaWorker for processing.
        """
        text = self.txt_input.text().strip()
        has_image = bool(self.pending_image_path)

        if (not text and not has_image) or self.is_processing:
            return

        self.txt_input.clear()
        self.is_processing = True
        self.txt_input.setEnabled(False)
        self.btn_attach.setEnabled(False)
        self.btn_web.setEnabled(False)
        self._update_send_button_style()

        # Add user message bubble
        user_bubble = ChatBubble(text, is_user=True, image_path=self.pending_image_path)
        self.chat_layout.addWidget(user_bubble)
        self.history.append({"role": "user", "content": text})

        self.full_response_buffer = ""

        # Create AI response bubble
        self.current_ai_bubble = ChatBubble("", is_user=False)
        self.chat_layout.addWidget(self.current_ai_bubble)
        self._scroll_to_bottom()

        self.current_model_used = (
            self.app_settings["vision_model"] if has_image
            else self.app_settings["main_model"]
        )

        # Instantiate and configure worker thread
        self.worker = OllamaWorker(
            history=self.history,
            model_name=self.app_settings["main_model"],
            vision_model_name=self.app_settings["vision_model"],
            system_prompt=self.app_settings["system_prompt"],
            image_path=self.pending_image_path,
            user_text=text,
            web_search_enabled=self.is_web_enabled
        )
        self.worker.new_token.connect(self._update_stream)
        self.worker.status_update.connect(self._update_status)
        self.worker.finished.connect(self._finalize_stream)
        self.worker.stopped.connect(self._on_worker_stopped)

        self.pending_image_path = None
        self._update_attach_button_style()
        self.worker.start()

    def _update_status(self, status_msg: str) -> None:
        """Update AI bubble with status info (e.g. 'Searching...')."""
        if self.current_ai_bubble:
            self.current_ai_bubble.update_text(status_msg)
            self._scroll_to_bottom()

    def _update_stream(self, token: str) -> None:
        """Append new token to the AI response buffer and update bubble."""
        self.full_response_buffer += token
        self.current_ai_bubble.update_text(self.full_response_buffer + " ▍")
        self._scroll_to_bottom()

    def _finalize_stream(self, duration: float, token_count: int) -> None:
        """Called when generation completes. Display final text and metadata."""
        if self.current_ai_bubble:
            self.current_ai_bubble.update_text(self.full_response_buffer)
            self.current_ai_bubble.set_metadata(duration, token_count, self.current_model_used)
        self.history.append({"role": "assistant", "content": self.full_response_buffer})
        self._reset_ui_after_response()

    def _scroll_to_bottom(self) -> None:
        """Queue a scroll to the bottom of the chat area."""
        QTimer.singleShot(
            0,
            lambda: self.scroll_area.verticalScrollBar().setValue(
                self.scroll_area.verticalScrollBar().maximum()
            )
        )