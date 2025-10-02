"""
Application entry point for Align-Press v2 UI.
"""

import sys
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import QApplication

from alignpress.ui.main_window import MainWindow


def main(config_path: Optional[Path] = None) -> int:
    """
    Run the Align-Press v2 application.

    Args:
        config_path: Optional path to config file

    Returns:
        Exit code
    """
    app = QApplication(sys.argv)
    app.setApplicationName("Align-Press v2")
    app.setOrganizationName("Align-Press")

    window = MainWindow(config_path=config_path)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
