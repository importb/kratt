"""
Settings dialog.

Allows model selection (fetched from Ollama) and system prompt customization.
"""

import ollama
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QComboBox,
    QTextEdit,
    QDialogButtonBox,
    QFormLayout,
)


class SettingsDialog(QDialog):
    def __init__(self, current_settings: dict, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(500, 400)
        self._apply_stylesheet()

        self.settings = current_settings.copy()
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        form_layout = QFormLayout()
        form_layout.setSpacing(15)

        self.combo_text_model = QComboBox()
        self.combo_vision_model = QComboBox()
        self._populate_models()

        form_layout.addRow("Text Model:", self.combo_text_model)
        form_layout.addRow("Image Model:", self.combo_vision_model)
        self.layout.addLayout(form_layout)

        self.layout.addWidget(QLabel("System Prompt:"))
        self.txt_prompt = QTextEdit()
        self.txt_prompt.setPlainText(self.settings.get("system_prompt", ""))
        self.layout.addWidget(self.txt_prompt)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        btn_cancel = buttons.button(QDialogButtonBox.Cancel)
        if btn_cancel:
            btn_cancel.setStyleSheet("background-color: #555; color: #ddd;")

        self.layout.addWidget(buttons)

    def _apply_stylesheet(self) -> None:
        self.setStyleSheet("""
            QDialog { background-color: #2b2b2b; color: #e0e0e0; }
            QLabel { color: #e0e0e0; font-size: 14px; }
            QComboBox {
                background-color: #3d3d3d; color: white; border: 1px solid #555;
                padding: 5px; border-radius: 4px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background-color: #3d3d3d; color: white; selection-background-color: #e67e22;
                border: 1px solid #555; outline: none;
            }
            QTextEdit {
                background-color: #3d3d3d; color: white; border: 1px solid #555;
                border-radius: 4px; font-family: Segoe UI, sans-serif;
            }
            QPushButton {
                background-color: #e67e22; color: white; border: none;
                padding: 8px 16px; border-radius: 4px;
            }
            QPushButton:hover { background-color: #d35400; } 
        """)

    def _populate_models(self) -> None:
        """Fetches available models from the local Ollama instance."""
        try:
            models_info = ollama.list()
            model_list = []

            # Handle API variations
            models_data = models_info.get("models", []) if isinstance(models_info, dict) else getattr(models_info, "models", [])

            for m in models_data:
                name = m.get("name") if isinstance(m, dict) else getattr(m, "name", None)
                if not name:
                    name = m.get("model") if isinstance(m, dict) else getattr(m, "model", None)
                if name:
                    model_list.append(name)

            model_list.sort()
            self.combo_text_model.addItems(model_list)
            self.combo_vision_model.addItems(model_list)

            # Set current selections
            idx_text = self.combo_text_model.findText(self.settings.get("main_model", ""))
            if idx_text >= 0: self.combo_text_model.setCurrentIndex(idx_text)

            idx_vis = self.combo_vision_model.findText(self.settings.get("vision_model", ""))
            if idx_vis >= 0: self.combo_vision_model.setCurrentIndex(idx_vis)

        except Exception as e:
            # Fallback if Ollama is unreachable
            print(f"Ollama connection error: {e}")
            curr_main = self.settings.get("main_model", "phi4-mini")
            curr_vis = self.settings.get("vision_model", "moondream:latest")
            self.combo_text_model.addItem(curr_main)
            self.combo_vision_model.addItem(curr_vis)

    def get_settings(self) -> dict:
        return {
            "main_model": self.combo_text_model.currentText(),
            "vision_model": self.combo_vision_model.currentText(),
            "system_prompt": self.txt_prompt.toPlainText().strip(),
        }