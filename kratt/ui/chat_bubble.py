"""
Chat bubble widget.

Displays user and AI messages with support for Markdown text,
images, and performance metadata.
"""

import os
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPixmap
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QFrame,
    QVBoxLayout,
    QLabel,
    QGraphicsDropShadowEffect,
)


class ChatBubble(QWidget):
    """
    Styled message container.
    """

    def __init__(
        self, text: str, is_user: bool = False, image_path: str | None = None
    ) -> None:
        super().__init__()
        self.is_user = is_user
        self.max_bubble_width = 340
        self.min_bubble_width = 60
        self.horizontal_margins = 24

        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(2, 5, 2, 5)
        self.setLayout(self.layout)

        self.bubble = QFrame()
        self.bubble_layout = QVBoxLayout()
        self.bubble_layout.setContentsMargins(12, 10, 12, 10)
        self.bubble_layout.setSpacing(6)
        self.bubble.setLayout(self.bubble_layout)

        self._apply_bubble_style()
        self._apply_shadow()

        self.bubble.setMinimumWidth(self.min_bubble_width)
        self.bubble.setMaximumWidth(self.max_bubble_width)

        self.image_label = None
        if image_path:
            self._add_image_preview(image_path)

        self.label = QLabel(text or "")
        self.label.setTextFormat(Qt.TextFormat.MarkdownText)
        self.label.setWordWrap(True)
        self.label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.label.setFont(QFont("Segoe UI", 10))
        self.label.setMaximumWidth(self.max_bubble_width - self.horizontal_margins)
        self.bubble_layout.addWidget(self.label)

        if not self.is_user:
            self.metadata_label = QLabel("")
            self.metadata_label.setFont(QFont("Segoe UI", 7))
            self.metadata_label.setStyleSheet("color: #888;")
            self.metadata_label.hide()
            self.bubble_layout.addWidget(self.metadata_label)

        if is_user:
            self.layout.addStretch()
            self.layout.addWidget(self.bubble)
        else:
            self.layout.addWidget(self.bubble)
            self.layout.addStretch()

    def _apply_bubble_style(self) -> None:
        """Sets background color and corner radius."""
        color = "#e67e22" if self.is_user else "#2b2b2b"
        radius_css = "border-radius: 15px;"
        if self.is_user:
            radius_css += "border-bottom-right-radius: 5px;"
        else:
            radius_css += "border-bottom-left-radius: 5px;"

        self.bubble.setStyleSheet(
            f"QFrame {{ background-color: {color}; {radius_css} color: #ffffff; }}"
        )

    def _apply_shadow(self) -> None:
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(2, 2)
        self.bubble.setGraphicsEffect(shadow)

    def _add_image_preview(self, image_path: str) -> None:
        """Adds an image thumbnail to the bubble if the path is valid."""
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet(
            "background-color: rgba(255,255,255,0.04); border-radius: 10px; padding: 4px;"
        )

        image_path = os.path.abspath(os.path.expanduser(image_path))
        if not os.path.isfile(image_path):
            self.image_label.setText(f"(Image not found)\n{image_path}")
            self.bubble_layout.addWidget(self.image_label)
            return

        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            self.image_label.setText(f"(Unsupported)\n{os.path.basename(image_path)}")
        else:
            scaled = pixmap.scaled(
                self.max_bubble_width - self.horizontal_margins,
                1000,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.image_label.setPixmap(scaled)

        self.bubble_layout.addWidget(self.image_label)

    def update_text(self, text: str) -> None:
        self.label.setText(text)

    def set_metadata(self, duration: float, token_count: int, model_name: str = "") -> None:
        """Displays generation stats (speed, time, model)."""
        if not self.is_user and token_count > 0 and duration > 0:
            tokens_per_sec = token_count / duration
            meta_text = f"{duration:.2f}s, {tokens_per_sec:.2f} t/s"
            if model_name:
                meta_text += f", {model_name}"
            self.metadata_label.setText(meta_text)
            self.metadata_label.show()