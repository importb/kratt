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
    Styled message container for the chat interface.
    """

    def __init__(
            self, text: str, is_user: bool = False, image_path: str | None = None
    ) -> None:
        """
        Initialize the chat bubble.

        Args:
            text (str): The message content (supports Markdown).
            is_user (bool): True if message is from the user, False if from AI.
            image_path (str | None): Optional path to an image file to display.
        """
        super().__init__()
        self.is_user = is_user
        self.max_bubble_width = 340
        self.min_bubble_width = 60
        self.horizontal_margins = 24

        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(4, 6, 4, 6)
        self.setLayout(self.layout)

        self.bubble = QFrame()

        if self.is_user:
            self.bubble.setObjectName("UserBubbleFrame")
        else:
            self.bubble.setObjectName("AiBubbleFrame")

        self.bubble_layout = QVBoxLayout()
        self.bubble_layout.setContentsMargins(14, 12, 14, 12)
        self.bubble_layout.setSpacing(8)
        self.bubble.setLayout(self.bubble_layout)

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
        self.label.setFont(QFont("Google Sans Flex", 10))
        self.label.setMaximumWidth(self.max_bubble_width - self.horizontal_margins)

        if self.is_user:
            self.label.setObjectName("UserBubbleText")
        else:
            self.label.setObjectName("AiBubbleText")

        self.bubble_layout.addWidget(self.label)

        if not self.is_user:
            self.metadata_label = QLabel("")
            self.metadata_label.setObjectName("AiMetaText")
            self.metadata_label.setFont(QFont("Google Sans Flex", 7))
            self.metadata_label.hide()
            self.bubble_layout.addWidget(self.metadata_label)

        if is_user:
            self.layout.addStretch()
            self.layout.addWidget(self.bubble)
        else:
            self.layout.addWidget(self.bubble)
            self.layout.addStretch()

    def _apply_shadow(self) -> None:
        """Adds a subtle drop shadow for depth."""
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(12)
        if self.is_user:
            shadow.setColor(QColor(230, 126, 34, 60))
        else:
            shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 2)
        self.bubble.setGraphicsEffect(shadow)

    def _add_image_preview(self, image_path: str) -> None:
        """Adds an image thumbnail to the bubble if the path is valid."""
        self.image_label = QLabel()
        self.image_label.setObjectName("ImagePreview")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

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
        """Updates the content of the bubble (used for streaming responses)."""
        self.label.setText(text)

    def set_metadata(self, duration: float, token_count: int, model_name: str = "") -> None:
        """
        Displays generation stats (speed, time, model) at the bottom of AI bubbles.

        Args:
            duration (float): Time taken in seconds.
            token_count (int): Number of tokens generated.
            model_name (str): The name of the model used.
        """
        if not self.is_user and token_count > 0 and duration > 0:
            tokens_per_sec = token_count / duration
            meta_text = f"{duration:.2f}s · {tokens_per_sec:.1f} t/s"
            if model_name:
                meta_text += f" · {model_name}"
            self.metadata_label.setText(meta_text)
            self.metadata_label.show()
