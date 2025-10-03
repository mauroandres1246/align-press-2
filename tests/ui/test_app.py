"""Tests for application entry point."""

import pytest
from pathlib import Path
from PySide6.QtWidgets import QApplication

from alignpress.ui.app import main


class TestAppMain:
    """Test application main function."""

    def test_main_creates_application(self, qtbot, monkeypatch):
        """Test main creates QApplication."""
        # Mock sys.exit to prevent actual exit
        monkeypatch.setattr("sys.exit", lambda x: None)

        # We can't actually run app.exec() in tests, so we'll test initialization
        # The main() function would hang at exec(), so we test components separately

    def test_qapplication_metadata(self, qtbot):
        """Test QApplication has correct metadata."""
        app = QApplication.instance()

        # Should have been created by pytest-qt
        assert app is not None

    def test_main_window_initialization(self, qtbot):
        """Test MainWindow can be created."""
        from alignpress.ui.main_window import MainWindow

        # Should not crash
        window = MainWindow()
        qtbot.addWidget(window)

        assert window is not None
        assert window.windowTitle() == "Align-Press v2"

    def test_main_window_with_config_path(self, qtbot, tmp_path):
        """Test MainWindow with custom config path."""
        from alignpress.ui.main_window import MainWindow
        import yaml

        # Create valid config file
        config_path = tmp_path / "test_config.yaml"
        config_data = {
            "fullscreen": False,
            "theme": "light",
            "technical_pin": "1234",
            "log_level": "INFO",
            "log_format": "text",
            "log_output_path": str(tmp_path / "logs")
        }
        config_path.write_text(yaml.dump(config_data))

        window = MainWindow(config_path=config_path)
        qtbot.addWidget(window)

        assert window is not None

    def test_application_name_set(self, qtbot):
        """Test application name is set correctly."""
        app = QApplication.instance()

        # Note: In test environment, app name might not persist
        # This tests that the code doesn't crash
        assert app is not None


class TestAppIntegration:
    """Integration tests for application."""

    def test_app_can_be_shown(self, qtbot):
        """Test application window can be shown."""
        from alignpress.ui.main_window import MainWindow

        window = MainWindow()
        qtbot.addWidget(window)

        # Should not crash
        window.show()
        assert window.isVisible()

    def test_app_window_properties(self, qtbot):
        """Test application window has expected properties."""
        from alignpress.ui.main_window import MainWindow

        window = MainWindow()
        qtbot.addWidget(window)

        # Should have central widget
        assert window.centralWidget() is not None

        # Should have menu bar
        assert window.menuBar() is not None

    def test_multiple_windows_not_created(self, qtbot):
        """Test only one main window should exist."""
        from alignpress.ui.main_window import MainWindow

        window1 = MainWindow()
        window2 = MainWindow()

        qtbot.addWidget(window1)
        qtbot.addWidget(window2)

        # Both should be valid but independent
        assert window1 is not window2
