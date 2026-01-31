"""
Main application window.

Coordinates user input, history management, and the worker thread.
"""

import os
from pathlib import Path
from PySide6.QtCore import Qt, QPoint, Signal, QTimer
from PySide6.QtGui import QColor
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
)

from kratt.config import (
    DEFAULT_MAIN_MODEL,
    DEFAULT_VISION_MODEL,
    DEFAULT_SYSTEM_PROMPT,
)
from kratt.core.worker import OllamaWorker
from kratt.ui.chat_bubble import ChatBubble
from kratt.ui.settings_dialog import SettingsDialog


class MainWindow(QWidget):
    """
    Draggable, frameless main chat window.
    """

    toggle_signal = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.app_settings = {
            "main_model": DEFAULT_MAIN_MODEL,
            "vision_model": DEFAULT_VISION_MODEL,
            "system_prompt": DEFAULT_SYSTEM_PROMPT,
        }

        self.history: list[dict] = []
        self.full_response_buffer = ""
        self.current_ai_bubble: ChatBubble | None = None
        self.is_processing = False
        self.is_web_enabled = False
        self.pending_image_path: str | None = None
        self.worker: OllamaWorker | None = None
        self.current_model_used = ""

        self._setup_ui()
        self._setup_hotkey()
        self.new_chat()

    def _setup_ui(self) -> None:
        self.setWindowTitle("Kratt")
        self.resize(400, 650)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.setStyleSheet("""
            background-color: transparent;
            QToolTip {
                background-color: #3d3d3d;
                color: white;
                border: 1px solid #555;
                padding: 5px;
                border-radius: 3px;
            }
        """)

        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.setLayout(self.main_layout)

        self.container = QFrame()
        self.container.setObjectName("Container")
        self.container.setStyleSheet("""
            QFrame#Container {
                background-color: #1e1e1e;
                border-radius: 12px;
                border: 1px solid #333;
            }
        """)

        win_shadow = QGraphicsDropShadowEffect()
        win_shadow.setBlurRadius(20)
        win_shadow.setColor(QColor(0, 0, 0, 150))
        self.container.setGraphicsEffect(win_shadow)

        self.container_layout = QVBoxLayout()
        self.container.setLayout(self.container_layout)
        self.main_layout.addWidget(self.container)

        self._setup_header()
        self._setup_chat_area()
        self._setup_input_area()
        self._center_window()

    def _setup_header(self) -> None:
        self.header = QFrame()
        self.header_layout = QHBoxLayout()
        self.header_layout.setContentsMargins(10, 5, 10, 5)
        self.header.setLayout(self.header_layout)

        title = QLabel("Kratt")
        title.setStyleSheet("color: #999; font-weight: bold;")

        btn_style = "QPushButton { border: none; color: #666; font-weight: bold; font-size: 14px; } QPushButton:hover { color: #e67e22; }"

        btn_new_chat = QPushButton("⟳")
        btn_new_chat.setFixedSize(24, 24)
        btn_new_chat.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_new_chat.setToolTip("New chat")
        btn_new_chat.clicked.connect(self.new_chat)
        btn_new_chat.setStyleSheet(btn_style)

        btn_settings = QPushButton("⚙")
        btn_settings.setFixedSize(24, 24)
        btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_settings.setToolTip("Settings")
        btn_settings.clicked.connect(self._open_settings)
        btn_settings.setStyleSheet(btn_style)

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(24, 24)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self.close)
        btn_close.setStyleSheet("QPushButton { border: none; color: #666; font-weight: bold; } QPushButton:hover { color: #ff5555; }")

        self.header_layout.addWidget(title)
        self.header_layout.addStretch()
        self.header_layout.addWidget(btn_new_chat)
        self.header_layout.addWidget(btn_settings)
        self.header_layout.addWidget(btn_close)
        self.container_layout.addWidget(self.header)

    def _setup_chat_area(self) -> None:
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { width: 8px; background: #1e1e1e; }
            QScrollBar::handle:vertical { background: #444; border-radius: 4px; }
        """)

        self.chat_widget = QWidget()
        self.chat_widget.setStyleSheet("background-color: #1e1e1e;")
        self.chat_layout = QVBoxLayout()
        self.chat_layout.addStretch()
        self.chat_widget.setLayout(self.chat_layout)
        self.scroll_area.setWidget(self.chat_widget)
        self.container_layout.addWidget(self.scroll_area)

    def _setup_input_area(self) -> None:
        self.input_frame = QFrame()
        self.input_frame.setStyleSheet("background-color: #1e1e1e;")
        self.input_layout = QHBoxLayout()
        self.input_layout.setContentsMargins(10, 10, 10, 10)
        self.input_frame.setLayout(self.input_layout)

        self.txt_input = QLineEdit()
        self.txt_input.setPlaceholderText("Message kratt...")
        self.txt_input.setStyleSheet("""
            QLineEdit {
                background-color: #2b2b2b; color: white; border: 1px solid #3d3d3d;
                border-radius: 18px; padding: 8px 15px; font-size: 13px;
            }
            QLineEdit:focus { border: 1px solid #e67e22; }
        """)
        self.txt_input.returnPressed.connect(self.send_message)

        self.btn_web = QPushButton("🌍")
        self.btn_web.setFixedSize(36, 36)
        self.btn_web.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_web.clicked.connect(self._toggle_web_search)

        self.btn_attach = QPushButton("📁")
        self.btn_attach.setFixedSize(36, 36)
        self.btn_attach.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_attach.clicked.connect(self._select_or_clear_file)

        self.btn_send = QPushButton("➤")
        self.btn_send.setFixedSize(36, 36)
        self.btn_send.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_send.clicked.connect(self._on_send_button_clicked)

        self._update_send_button_style()
        self._update_web_button_style()
        self._update_attach_button_style()

        self.input_layout.addWidget(self.txt_input)
        self.input_layout.addWidget(self.btn_web)
        self.input_layout.addWidget(self.btn_attach)
        self.input_layout.addWidget(self.btn_send)
        self.container_layout.addWidget(self.input_frame)

    def _toggle_web_search(self) -> None:
        if self.is_processing:
            return
        self.is_web_enabled = not self.is_web_enabled
        self._update_web_button_style()

    def _update_web_button_style(self) -> None:
        if self.is_web_enabled:
            self.btn_web.setToolTip("Web Search (On)")
            self.btn_web.setStyleSheet("QPushButton { background-color: #2b5c96; color: white; border-radius: 18px; font-size: 16px; border: 1px solid #4a90e2; }")
        else:
            self.btn_web.setToolTip("Web Search (Off)")
            self.btn_web.setStyleSheet("QPushButton { background-color: #2b2b2b; color: #aaa; border-radius: 18px; font-size: 16px; border: 1px solid #3d3d3d; }")

    def _update_send_button_style(self) -> None:
        if self.is_processing:
            self.btn_send.setText("■")
            self.btn_send.setToolTip("Force Stop")
            self.btn_send.setStyleSheet("QPushButton { background-color: #4a2020; color: #ff5555; border-radius: 18px; font-size: 14px; border: 1px solid #ff5555; }")
        else:
            self.btn_send.setText("➤")
            self.btn_send.setToolTip("Send message")
            self.btn_send.setStyleSheet("QPushButton { background-color: #2b2b2b; color: #e67e22; border-radius: 18px; font-size: 16px; border: 1px solid #3d3d3d; }")

    def _on_send_button_clicked(self) -> None:
        if self.is_processing:
            self._force_stop()
        else:
            self.send_message()

    def _force_stop(self) -> None:
        if not self.is_processing or self.worker is None:
            return
        self.worker.request_stop()
        if self.current_ai_bubble:
            msg = self.full_response_buffer + " *(stopped)*" if self.full_response_buffer else "*(stopped)*"
            self.current_ai_bubble.update_text(msg)

    def _on_worker_stopped(self) -> None:
        if self.full_response_buffer:
            self.history.append({"role": "assistant", "content": self.full_response_buffer})
        self._reset_ui_after_response()

    def _reset_ui_after_response(self) -> None:
        self.is_processing = False
        self.txt_input.setEnabled(True)
        self.btn_attach.setEnabled(True)
        self.btn_web.setEnabled(True)
        self._update_send_button_style()
        self.txt_input.setFocus()
        self._scroll_to_bottom()

    def _update_attach_button_style(self) -> None:
        if self.pending_image_path:
            name = os.path.basename(self.pending_image_path)
            self.btn_attach.setToolTip(f"Attached: {name}\nClick to clear.")
            self.btn_attach.setStyleSheet("QPushButton { background-color: #3d2b1f; color: #e67e22; border-radius: 18px; font-size: 14px; border: 1px solid #e67e22; }")
        else:
            self.btn_attach.setToolTip("Attach image")
            self.btn_attach.setStyleSheet("QPushButton { background-color: #2b2b2b; color: #aaa; border-radius: 18px; font-size: 14px; border: 1px solid #3d3d3d; }")

    def _select_or_clear_file(self) -> None:
        if self.is_processing:
            return

        if self.pending_image_path:
            self.pending_image_path = None
            self._update_attach_button_style()
            self.txt_input.setFocus()
            return

        start_dir = str(Path.home())
        file_path, _ = QFileDialog.getOpenFileName(self, "Select image", start_dir, "Images (*.png *.jpg *.jpeg *.webp *.bmp *.gif)")
        if not file_path:
            return

        self.pending_image_path = os.path.abspath(file_path)
        self._update_attach_button_style()
        self.txt_input.setFocus()
        # Web search incompatible with vision
        if self.is_web_enabled:
            self.is_web_enabled = False
            self._update_web_button_style()

    def _center_window(self) -> None:
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event) -> None:
        if hasattr(self, "old_pos"):
            delta = QPoint(event.globalPosition().toPoint() - self.old_pos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event) -> None:
        if hasattr(self, "old_pos"):
            del self.old_pos

    def _open_settings(self) -> None:
        if self.is_processing:
            return
        dlg = SettingsDialog(self.app_settings, self)
        if dlg.exec():
            self.app_settings = dlg.get_settings()
            if len(self.history) == 1 and self.history[0]["role"] == "system":
                self.history[0]["content"] = self.app_settings["system_prompt"]

    def new_chat(self) -> None:
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
        while self.chat_layout.count() > 1:
            item = self.chat_layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()
        self.txt_input.setFocus()

    def send_message(self) -> None:
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

        user_bubble = ChatBubble(text, is_user=True, image_path=self.pending_image_path)
        self.chat_layout.addWidget(user_bubble)
        self.history.append({"role": "user", "content": text})

        self.current_ai_bubble = ChatBubble("", is_user=False)
        self.chat_layout.addWidget(self.current_ai_bubble)
        self._scroll_to_bottom()

        self.current_model_used = self.app_settings["vision_model"] if has_image else self.app_settings["main_model"]

        self.worker = OllamaWorker(
            history=self.history,
            model_name=self.app_settings["main_model"],
            vision_model_name=self.app_settings["vision_model"],
            system_prompt=self.app_settings["system_prompt"],
            image_path=self.pending_image_path,
            user_text=text,
            web_search_enabled=(self.is_web_enabled and not has_image)
        )
        self.worker.new_token.connect(self._update_stream)
        self.worker.status_update.connect(self._update_status)
        self.worker.finished.connect(self._finalize_stream)
        self.worker.stopped.connect(self._on_worker_stopped)

        self.pending_image_path = None
        self._update_attach_button_style()
        self.worker.start()

    def _update_status(self, status_msg: str) -> None:
        if self.current_ai_bubble:
            self.current_ai_bubble.update_text(status_msg)
            self._scroll_to_bottom()

    def _update_stream(self, token: str) -> None:
        self.full_response_buffer += token
        self.current_ai_bubble.update_text(self.full_response_buffer + " ▍")
        self._scroll_to_bottom()

    def _finalize_stream(self, duration: float, token_count: int) -> None:
        if self.current_ai_bubble:
            self.current_ai_bubble.update_text(self.full_response_buffer)
            self.current_ai_bubble.set_metadata(duration, token_count, self.current_model_used)
        self.history.append({"role": "assistant", "content": self.full_response_buffer})
        self._reset_ui_after_response()

    def _scroll_to_bottom(self) -> None:
        QTimer.singleShot(0, lambda: self.scroll_area.verticalScrollBar().setValue(self.scroll_area.verticalScrollBar().maximum()))

    def _setup_hotkey(self) -> None:
        self.toggle_signal.connect(self.toggle_visibility)

    def toggle_visibility(self) -> None:
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.activateWindow()
            self.txt_input.setFocus()