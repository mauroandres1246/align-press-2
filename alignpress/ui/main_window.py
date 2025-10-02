"""
Main window for Align-Press v2 UI.

This module provides the main application window with support for both
operator and technical modes.
"""

from typing import Optional
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QStackedWidget,
    QMessageBox, QInputDialog, QLineEdit
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction

from alignpress.utils.config_loader import ConfigLoader
from alignpress.core.schemas import AppConfigSchema


class MainWindow(QMainWindow):
    """
    Main application window.

    Supports switching between operator and technical modes with PIN authentication.
    """

    mode_changed = Signal(str)  # Emitted when mode changes: "operator" or "technical"

    def __init__(self, config_path: Optional[Path] = None) -> None:
        """
        Initialize main window.

        Args:
            config_path: Path to app.yaml config file. If None, uses default.
        """
        super().__init__()

        # Load configuration
        loader = ConfigLoader()
        self.config = loader.load_app_config(config_path)

        # Current mode
        self.current_mode = "operator"

        # Setup UI
        self._setup_ui()
        self._setup_menu()
        self._apply_theme()

    def _setup_ui(self) -> None:
        """Setup main UI components."""
        self.setWindowTitle("Align-Press v2")

        # Set window size from config or default
        if self.config.fullscreen:
            self.showFullScreen()
        else:
            self.resize(1024, 768)

        # Central widget with stacked layout for different screens
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Stacked widget for different views
        self.stacked_widget = QStackedWidget()
        self.layout.addWidget(self.stacked_widget)

        # Placeholder widgets (will be replaced in subsequent tasks)
        self.operator_view = QWidget()
        self.technical_view = QWidget()

        self.stacked_widget.addWidget(self.operator_view)
        self.stacked_widget.addWidget(self.technical_view)

        # Start in operator view
        self.stacked_widget.setCurrentWidget(self.operator_view)

    def _setup_menu(self) -> None:
        """Setup menu bar."""
        menubar = self.menuBar()

        # View menu
        view_menu = menubar.addMenu("&Vista")

        # Switch to technical mode action
        self.technical_action = QAction("Modo &Técnico", self)
        self.technical_action.setShortcut("Ctrl+T")
        self.technical_action.triggered.connect(self._switch_to_technical)
        view_menu.addAction(self.technical_action)

        # Switch to operator mode action
        self.operator_action = QAction("Modo &Operador", self)
        self.operator_action.setShortcut("Ctrl+O")
        self.operator_action.triggered.connect(self._switch_to_operator)
        self.operator_action.setEnabled(False)
        view_menu.addAction(self.operator_action)

        view_menu.addSeparator()

        # Toggle fullscreen action
        self.fullscreen_action = QAction("Pantalla &Completa", self)
        self.fullscreen_action.setShortcut("F11")
        self.fullscreen_action.setCheckable(True)
        self.fullscreen_action.setChecked(self.config.fullscreen)
        self.fullscreen_action.triggered.connect(self._toggle_fullscreen)
        view_menu.addAction(self.fullscreen_action)

        view_menu.addSeparator()

        # Exit action
        exit_action = QAction("&Salir", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        view_menu.addAction(exit_action)

    def _apply_theme(self) -> None:
        """Apply theme from config."""
        theme = self.config.ui_theme

        if theme == "dark":
            self._apply_dark_theme()
        else:
            self._apply_light_theme()

    def _apply_dark_theme(self) -> None:
        """Apply dark theme stylesheet."""
        # Basic dark theme
        stylesheet = """
        QMainWindow, QWidget {
            background-color: #2b2b2b;
            color: #ffffff;
        }
        QMenuBar {
            background-color: #3c3c3c;
            color: #ffffff;
        }
        QMenuBar::item:selected {
            background-color: #5c5c5c;
        }
        QMenu {
            background-color: #3c3c3c;
            color: #ffffff;
        }
        QMenu::item:selected {
            background-color: #5c5c5c;
        }
        """
        self.setStyleSheet(stylesheet)

    def _apply_light_theme(self) -> None:
        """Apply light theme (default Qt theme)."""
        self.setStyleSheet("")

    def _switch_to_technical(self) -> None:
        """Switch to technical mode with PIN authentication."""
        # Request PIN
        pin, ok = QInputDialog.getText(
            self,
            "Modo Técnico",
            "Ingrese PIN de técnico:",
            QLineEdit.EchoMode.Password
        )

        if not ok:
            return

        # Validate PIN
        if pin == self.config.technical_pin:
            self.current_mode = "technical"
            self.stacked_widget.setCurrentWidget(self.technical_view)

            # Update menu state
            self.technical_action.setEnabled(False)
            self.operator_action.setEnabled(True)

            self.mode_changed.emit("technical")
        else:
            QMessageBox.warning(
                self,
                "Error de Autenticación",
                "PIN incorrecto. Acceso denegado."
            )

    def _switch_to_operator(self) -> None:
        """Switch to operator mode."""
        self.current_mode = "operator"
        self.stacked_widget.setCurrentWidget(self.operator_view)

        # Update menu state
        self.technical_action.setEnabled(True)
        self.operator_action.setEnabled(False)

        self.mode_changed.emit("operator")

    def _toggle_fullscreen(self) -> None:
        """Toggle fullscreen mode."""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def get_current_mode(self) -> str:
        """
        Get current mode.

        Returns:
            Current mode: "operator" or "technical"
        """
        return self.current_mode

    def set_operator_view(self, widget: QWidget) -> None:
        """
        Set the operator view widget.

        Args:
            widget: Widget to use as operator view
        """
        old_widget = self.operator_view
        self.stacked_widget.removeWidget(old_widget)
        self.operator_view = widget
        self.stacked_widget.insertWidget(0, widget)

        if self.current_mode == "operator":
            self.stacked_widget.setCurrentWidget(widget)

    def set_technical_view(self, widget: QWidget) -> None:
        """
        Set the technical view widget.

        Args:
            widget: Widget to use as technical view
        """
        old_widget = self.technical_view
        self.stacked_widget.removeWidget(old_widget)
        self.technical_view = widget
        self.stacked_widget.insertWidget(1, widget)

        if self.current_mode == "technical":
            self.stacked_widget.setCurrentWidget(widget)
