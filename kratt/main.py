"""
Application entry point.

Initializes the Qt Application, styling fixes for Linux,
and the main window with system tray integration.
"""

import sys
from pathlib import Path
from PySide6.QtGui import QFontDatabase, QFont
from PySide6.QtWidgets import QApplication
from kratt.ui.main_window import MainWindow


def load_stylesheet(app: QApplication) -> None:
    """Loads the external QSS/CSS file and applies it to the app."""
    css_path = Path(__file__).parent / "resources" / "style.css"
    if css_path.exists():
        with open(css_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    else:
        print(f"Warning: Stylesheet not found at {css_path}")


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
            # Set default font for the application
            app.setFont(QFont(font_family, 10))

    # Load external CSS styles
    load_stylesheet(app)

    # Force tooltip font styling
    current_style = app.styleSheet()
    app.setStyleSheet(current_style + f"\nQToolTip {{ font-family: '{font_family}'; }}")

    window = MainWindow()
    window.show()
    exit_code = app.exec()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()