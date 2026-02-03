"""
Settings dialog.

Allows model selection (fetched from Ollama) and system prompt customization.
"""

import ollama
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QListView,
    QTextEdit,
    QPushButton,
    QFormLayout,
    QFrame,
    QGraphicsDropShadowEffect,
)


class SettingsDialog(QDialog):
    def __init__(self, current_settings: dict, parent=None) -> None:
        super().__init__(parent)
        self.old_pos = None
        self.setWindowTitle("Settings")
        self.resize(460, 480)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Dialog
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.settings = current_settings.copy()
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.setLayout(self.main_layout)

        self.container = QFrame()
        self.container.setObjectName("Container")
        self.container.setStyleSheet("""
            QFrame#Container {
                background-color: #0d0b09;
                border-radius: 16px;
                border: 1px solid #2a2520;
            }
        """)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 200))
        shadow.setOffset(0, 4)
        self.container.setGraphicsEffect(shadow)

        self.container_layout = QVBoxLayout()
        self.container_layout.setSpacing(0)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container.setLayout(self.container_layout)
        self.main_layout.addWidget(self.container)

        self._setup_header()
        self._setup_content()

    def _setup_header(self) -> None:
        header = QFrame()
        header.setStyleSheet("background-color: transparent;")
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(16, 12, 16, 8)
        header.setLayout(header_layout)

        title = QLabel("Settings")
        title.setStyleSheet("color: #c9a87c; font-weight: 600; font-size: 15px;")

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(28, 28)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self.reject)
        btn_close.setStyleSheet("""
            QPushButton {
                border: none;
                color: #6b5c4c;
                font-weight: bold;
                background: transparent;
                padding: 4px;
                border-radius: 6px;
            }
            QPushButton:hover {
                color: #ff6b6b;
                background-color: #2a1515;
            }
        """)

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(btn_close)
        self.container_layout.addWidget(header)

    def _setup_content(self) -> None:
        content = QFrame()
        content.setStyleSheet("background-color: transparent;")
        content_layout = QVBoxLayout()
        content_layout.setSpacing(16)
        content_layout.setContentsMargins(20, 12, 20, 20)
        content.setLayout(content_layout)

        form_layout = QFormLayout()
        form_layout.setSpacing(12)

        self.combo_text_model = QComboBox()
        self.combo_vision_model = QComboBox()
        self._populate_models()
        self._apply_combo_style(self.combo_text_model)
        self._apply_combo_style(self.combo_vision_model)

        label_text = QLabel("Text Model:")
        label_text.setStyleSheet("color: #c9a87c; font-size: 13px; font-weight: 500;")
        label_vision = QLabel("Image Model:")
        label_vision.setStyleSheet("color: #c9a87c; font-size: 13px; font-weight: 500;")

        form_layout.addRow(label_text, self.combo_text_model)
        form_layout.addRow(label_vision, self.combo_vision_model)
        content_layout.addLayout(form_layout)

        prompt_label = QLabel("System Prompt:")
        prompt_label.setStyleSheet("color: #c9a87c; font-size: 13px; font-weight: 500; margin-top: 8px;")
        content_layout.addWidget(prompt_label)

        self.txt_prompt = QTextEdit()
        self.txt_prompt.setPlainText(self.settings.get("system_prompt", ""))
        self.txt_prompt.setStyleSheet("""
            QTextEdit {
                background-color: #1a1510;
                color: #e0d5c5;
                border: 1px solid #2e2820;
                border-radius: 8px;
                font-family: 'Google Sans Flex', sans-serif;
                font-size: 13px;
                padding: 8px;
            }
            QTextEdit:focus {
                border-color: #7a5c3a;
            }
            QScrollBar:vertical {
                width: 6px;
                background: transparent;
                margin: 4px 2px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background: #3d352c;
                border-radius: 3px;
                min-height: 30px;
                border: none;
            }
            QScrollBar::handle:vertical:hover {
                background: #5c4f40;
                border: none;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
                width: 0px;
                border: none;
                background: transparent;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent;
                border: none;
            }
        """)
        content_layout.addWidget(self.txt_prompt)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #1a1510;
                color: #a08060;
                border: 1px solid #2e2820;
                padding: 10px 20px;
                border-radius: 8px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #252015;
                border-color: #3d352c;
            }
        """)

        btn_save = QPushButton("Save")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.clicked.connect(self.accept)
        btn_save.setStyleSheet("""
            QPushButton {
                background-color: #e67e22;
                color: #0d0b09;
                border: none;
                padding: 10px 20px;
                border-radius: 8px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #f39c12;
            }
            QPushButton:pressed {
                background-color: #d35400;
            }
        """)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        content_layout.addLayout(btn_layout)

        self.container_layout.addWidget(content)

    def _apply_combo_style(self, combo: QComboBox) -> None:
        """
        Applies stylesheet and ensures the popup view is styled correctly.

        Includes a workaround for Linux/Qt where dropdown popups may inherit
        native OS window borders/backgrounds incorrectly.
        """
        view = QListView()
        combo.setView(view)

        # Explicitly remove the frame to prevent system borders
        view.setFrameShape(QFrame.Shape.NoFrame)
        view.setFrameShadow(QFrame.Shadow.Plain)

        # Styling
        combo.setStyleSheet("""
            QComboBox {
                background-color: #1a1510;
                color: #e0d5c5;
                border: 1px solid #2e2820;
                padding: 4px 8px;
                border-radius: 8px;
                font-size: 12px;
            }
            QComboBox:hover {
                border-color: #3d352c;
            }
            QComboBox:focus {
                border-color: #7a5c3a;
                outline: none;
            }
            QComboBox::drop-down {
                border-radius: 8px;
                width: 20px;
                border: none;
            }
            QComboBox::down-arrow {
                width: 0px;
                height: 0px;
                border: none;
            }
            
            QComboBox QFrame {
                border: none;
                background: transparent;
            }

            /* Popup View Styling */
            QComboBox QAbstractItemView {
                background-color: #1a1510;
                color: #e0d5c5;
                border-radius: 8px;
                selection-background-color: #e67e22;
                selection-color: #0d0b09;
                outline: none;
                padding: 1px; /* Minimal padding */
                margin: 0px;
            }
            
            QComboBox QAbstractItemView::item {
                min-height: 14px;
                padding: 2px 4px;
                border-radius: 4px;
                color: #e0d5c5;
                border: none;
                font-size: 11px;
            }
            
            /* Highlight/Hover State */
            QComboBox QAbstractItemView::item:hover,
            QComboBox QAbstractItemView::item:selected {
                background-color: #e67e22;
                color: #0d0b09;
                border: none;
            }

            /* Scrollbar styling */
            QScrollBar:vertical {
                width: 4px;
                background: #1a1510;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #3d352c;
                border-radius: 2px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #5c4f40;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent;
            }
        """)

        original_showpopup = combo.showPopup

        def custom_showpopup():
            original_showpopup()
            popup_window = view.window()
            popup_window.setStyleSheet("""
                QMainWindow, QWidget {
                    background-color: #1a1510;
                    border: 0px solid #2e2820;
                    border-radius: 8px;
                    margin: 0px;
                    padding: 0px;
                }
            """)
            popup_window.setWindowFlags(
                popup_window.windowFlags() | Qt.WindowType.FramelessWindowHint
            )

        combo.showPopup = custom_showpopup

    def _populate_models(self) -> None:
        """
        Fetches available models from the local Ollama instance.
        """
        placeholder = "No model selected..."
        model_names = []

        try:
            models_info = ollama.list()
            # Handle both dictionary and object responses from Ollama client
            models_data = models_info.get("models", []) if isinstance(models_info, dict) else getattr(models_info,
                                                                                                      "models", [])

            for m in models_data:
                name = m.get("name") if isinstance(m, dict) else getattr(m, "name", None)
                if not name:
                    name = m.get("model") if isinstance(m, dict) else getattr(m, "model", None)
                if name:
                    model_names.append(name)

            model_names.sort()

        except Exception as e:
            print(f"Ollama connection error: {e}")
            # Even on error, we might want to let the user see what they had selected before,
            # or just show empty. For now, we rely on the logic below to handle selection.

        # Prepend the placeholder
        final_list = [placeholder] + model_names

        self.combo_text_model.clear()
        self.combo_text_model.addItems(final_list)

        self.combo_vision_model.clear()
        self.combo_vision_model.addItems(final_list)

        # Helper to safely find model index (handling implicit :latest)
        def find_model_index(combo: QComboBox, model_name: str) -> int:
            if not model_name or model_name == placeholder:
                return 0

            # Try exact match
            idx = combo.findText(model_name)
            if idx > 0:
                return idx

            # Try appending :latest if missing (e.g. 'phi4' -> 'phi4:latest')
            if ":" not in model_name:
                idx = combo.findText(f"{model_name}:latest")
                if idx > 0:
                    return idx

            # Try removing :latest if present (e.g. 'phi4:latest' -> 'phi4')
            if model_name.endswith(":latest"):
                short_name = model_name.replace(":latest", "")
                idx = combo.findText(short_name)
                if idx > 0:
                    return idx

            return -1

        # Set Text Model
        current_main = self.settings.get("main_model", "")
        idx_text = find_model_index(self.combo_text_model, current_main)
        # If found (idx > 0), set it. If not found (-1), set to 0 (Placeholder)
        self.combo_text_model.setCurrentIndex(max(0, idx_text))

        # Set Vision Model
        current_vis = self.settings.get("vision_model", "")
        idx_vis = find_model_index(self.combo_vision_model, current_vis)
        self.combo_vision_model.setCurrentIndex(max(0, idx_vis))

    def get_settings(self) -> dict:
        """Returns the dictionary of settings configured in the dialog."""
        return {
            "main_model": self.combo_text_model.currentText(),
            "vision_model": self.combo_vision_model.currentText(),
            "system_prompt": self.txt_prompt.toPlainText().strip(),
        }

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event) -> None:
        if hasattr(self, "old_pos"):
            current_pos = event.globalPosition().toPoint()
            dx = current_pos.x() - self.old_pos.x()
            dy = current_pos.y() - self.old_pos.y()
            self.move(self.x() + dx, self.y() + dy)
            self.old_pos = current_pos

    def mouseReleaseEvent(self, event) -> None:
        if hasattr(self, "old_pos"):
            del self.old_pos