"""
Application entry point.

Initializes the Qt Application, styling fixes for Linux,
and the global hotkey listener.
"""

import sys
from pathlib import Path
from PySide6.QtGui import QFontDatabase, QFont
from PySide6.QtWidgets import QApplication
from kratt.ui.main_window import MainWindow
from kratt.core.hotkey_manager import HotkeyManager
from kratt.config import HOTKEY


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Load GoogleSansFlex from resources
    font_path = Path(__file__).parent / "resources" / "GoogleSansFlex.ttf"
    font_family = "Sans Serif"
    font_id = QFontDatabase.addApplicationFont(str(font_path))
    if font_id != -1:
        families = QFontDatabase.applicationFontFamilies(font_id)
        if families:
            font_family = families[0]
            app.setFont(QFont(font_family, 10))

    # Force tooltip styling for better visibility
    app.setStyleSheet(f"""
        QToolTip {{
            font-family: '{font_family}';
            background-color: #1a1510;
            color: #e0d5c5;
            border: 1px solid #2e2820;
            border-radius: 8px;
            padding: 6px 4px;
            font-size: 10px;
        }}
        QWidget {{
            font-family: '{font_family}';
        }}
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
