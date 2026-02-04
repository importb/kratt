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
        self.container.setObjectName("SettingsContainer")

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
        header.setObjectName("Header")
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(16, 12, 16, 8)
        header.setLayout(header_layout)

        title = QLabel("Settings")
        title.setObjectName("WinTitle")

        btn_close = QPushButton("✕")
        btn_close.setObjectName("CloseBtn")
        btn_close.setFixedSize(28, 28)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self.reject)

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(btn_close)
        self.container_layout.addWidget(header)

    def _setup_content(self) -> None:
        content = QFrame()
        content.setObjectName("SettingsContent")
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
        label_text.setObjectName("SettingsLabel")
        label_vision = QLabel("Image Model:")
        label_vision.setObjectName("SettingsLabel")

        form_layout.addRow(label_text, self.combo_text_model)
        form_layout.addRow(label_vision, self.combo_vision_model)
        content_layout.addLayout(form_layout)

        prompt_label = QLabel("System Prompt:")
        prompt_label.setObjectName("SettingsLabel")
        # Add a little top margin adjustment manually or rely on layout spacing
        prompt_label.setStyleSheet("margin-top: 8px;")
        content_layout.addWidget(prompt_label)

        self.txt_prompt = QTextEdit()
        self.txt_prompt.setObjectName("SettingsInput")
        self.txt_prompt.setPlainText(self.settings.get("system_prompt", ""))
        content_layout.addWidget(self.txt_prompt)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("SettingsCancelBtn")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)

        btn_save = QPushButton("Save")
        btn_save.setObjectName("SettingsSaveBtn")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.clicked.connect(self.accept)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        content_layout.addLayout(btn_layout)

        self.container_layout.addWidget(content)

    def _apply_combo_style(self, combo: QComboBox) -> None:
        """
        Applies hacks for Linux/Qt where dropdown popups may inherit
        native OS window borders/backgrounds incorrectly.
        The actual visual styling is now in the external CSS.
        """
        view = QListView()
        combo.setView(view)

        # Explicitly remove the frame to prevent system borders
        view.setFrameShape(QFrame.Shape.NoFrame)
        view.setFrameShadow(QFrame.Shadow.Plain)

        original_showpopup = combo.showPopup

        def custom_showpopup():
            original_showpopup()
            # This logic must stay in Python to target the specific runtime window
            popup_window = view.window()
            # We force this frameless state locally
            popup_window.setWindowFlags(
                popup_window.windowFlags() | Qt.WindowType.FramelessWindowHint
            )
            # Ensure the popup container is dark to match the theme (CSS covers QAbstractItemView, this covers the window container)
            popup_window.setStyleSheet("""
                QMainWindow, QWidget {
                    background-color: #1a1510;
                    border: 0px solid #2e2820;
                    border-radius: 8px;
                    margin: 0px;
                    padding: 0px;
                }
            """)

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
        """Enable window dragging on left mouse button press."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.windowHandle().startSystemMove()

    def mouseMoveEvent(self, event) -> None:
        pass

    def mouseReleaseEvent(self, event) -> None:
        pass
