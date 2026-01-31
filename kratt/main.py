"""
Application entry point.

Initializes the Qt Application, styling fixes for Linux,
and the global hotkey listener.
"""

import sys
from PySide6.QtWidgets import QApplication
from kratt.ui.main_window import MainWindow
from kratt.core.hotkey_manager import HotkeyManager
from kratt.config import HOTKEY


def main() -> None:
    app = QApplication(sys.argv)

    # Force tooltip styling for better visibility
    app.setStyleSheet("""
        QToolTip {
            background-color: #333333;
            color: #ffffff;
            border: 1px solid #555555;
        }
    """)

    window = MainWindow()

    # Initialize global hotkey listener
    hotkey_mgr = HotkeyManager(HOTKEY, window.toggle_visibility)

    window.show()
    exit_code = app.exec()
    hotkey_mgr.stop()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()