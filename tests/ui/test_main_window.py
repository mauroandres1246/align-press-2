"""Tests for MainWindow."""

import pytest
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt

from alignpress.ui.main_window import MainWindow


class TestMainWindow:
    """Test MainWindow functionality."""

    def test_main_window_initialization(self, qtbot):
        """Test that MainWindow initializes correctly."""
        window = MainWindow()
        qtbot.addWidget(window)

        assert window.windowTitle() == "Align-Press v2"
        assert window.current_mode == "operator"
        assert window.stacked_widget is not None

    def test_main_window_has_menu_bar(self, qtbot):
        """Test that MainWindow has a menu bar."""
        window = MainWindow()
        qtbot.addWidget(window)

        menubar = window.menuBar()
        assert menubar is not None

        # Check that "Vista" menu exists
        actions = menubar.actions()
        menu_titles = [action.text() for action in actions]
        assert "&Vista" in menu_titles

    def test_mode_starts_as_operator(self, qtbot):
        """Test that window starts in operator mode."""
        window = MainWindow()
        qtbot.addWidget(window)

        assert window.get_current_mode() == "operator"
        assert window.stacked_widget.currentWidget() == window.operator_view

    def test_switch_to_technical_wrong_pin(self, qtbot, monkeypatch):
        """Test switching to technical mode with wrong PIN."""
        window = MainWindow()
        qtbot.addWidget(window)

        # Mock QInputDialog to return wrong PIN
        monkeypatch.setattr(
            "PySide6.QtWidgets.QInputDialog.getText",
            lambda *args, **kwargs: ("wrong_pin", True)
        )

        # Mock QMessageBox to avoid showing actual dialog
        message_shown = []
        monkeypatch.setattr(
            "PySide6.QtWidgets.QMessageBox.warning",
            lambda *args, **kwargs: message_shown.append(True)
        )

        # Try to switch
        window._switch_to_technical()

        # Should still be in operator mode
        assert window.get_current_mode() == "operator"
        assert len(message_shown) == 1

    def test_switch_to_technical_correct_pin(self, qtbot, monkeypatch):
        """Test switching to technical mode with correct PIN."""
        window = MainWindow()
        qtbot.addWidget(window)

        # Mock QInputDialog to return correct PIN
        correct_pin = window.config.technical_pin
        monkeypatch.setattr(
            "PySide6.QtWidgets.QInputDialog.getText",
            lambda *args, **kwargs: (correct_pin, True)
        )

        # Switch to technical mode
        window._switch_to_technical()

        # Should be in technical mode now
        assert window.get_current_mode() == "technical"
        assert window.stacked_widget.currentWidget() == window.technical_view

    def test_switch_back_to_operator(self, qtbot, monkeypatch):
        """Test switching back to operator mode."""
        window = MainWindow()
        qtbot.addWidget(window)

        # First switch to technical
        correct_pin = window.config.technical_pin
        monkeypatch.setattr(
            "PySide6.QtWidgets.QInputDialog.getText",
            lambda *args, **kwargs: (correct_pin, True)
        )
        window._switch_to_technical()

        # Then switch back to operator
        window._switch_to_operator()

        assert window.get_current_mode() == "operator"
        assert window.stacked_widget.currentWidget() == window.operator_view

    def test_mode_changed_signal(self, qtbot, monkeypatch):
        """Test that mode_changed signal is emitted."""
        window = MainWindow()
        qtbot.addWidget(window)

        # Track signal emissions
        signals_received = []

        def on_mode_changed(mode):
            signals_received.append(mode)

        window.mode_changed.connect(on_mode_changed)

        # Mock PIN input
        correct_pin = window.config.technical_pin
        monkeypatch.setattr(
            "PySide6.QtWidgets.QInputDialog.getText",
            lambda *args, **kwargs: (correct_pin, True)
        )

        # Switch to technical
        window._switch_to_technical()
        assert "technical" in signals_received

        # Switch back to operator
        window._switch_to_operator()
        assert "operator" in signals_received

    def test_set_operator_view(self, qtbot):
        """Test setting custom operator view widget."""
        window = MainWindow()
        qtbot.addWidget(window)

        custom_widget = QWidget()
        window.set_operator_view(custom_widget)

        assert window.operator_view == custom_widget
        assert window.stacked_widget.currentWidget() == custom_widget

    def test_set_technical_view(self, qtbot, monkeypatch):
        """Test setting custom technical view widget."""
        window = MainWindow()
        qtbot.addWidget(window)

        # Switch to technical mode first
        correct_pin = window.config.technical_pin
        monkeypatch.setattr(
            "PySide6.QtWidgets.QInputDialog.getText",
            lambda *args, **kwargs: (correct_pin, True)
        )
        window._switch_to_technical()

        custom_widget = QWidget()
        window.set_technical_view(custom_widget)

        assert window.technical_view == custom_widget
        assert window.stacked_widget.currentWidget() == custom_widget

    def test_toggle_fullscreen(self, qtbot):
        """Test toggling fullscreen mode."""
        window = MainWindow()
        qtbot.addWidget(window)

        initial_fullscreen = window.isFullScreen()

        # Toggle fullscreen
        window._toggle_fullscreen()
        qtbot.wait(100)  # Wait for window state to update

        # State should have changed
        assert window.isFullScreen() != initial_fullscreen

    def test_menu_actions_enabled_state(self, qtbot):
        """Test menu actions are in correct enabled state."""
        window = MainWindow()
        qtbot.addWidget(window)

        # In operator mode
        assert window.technical_action.isEnabled() is True
        assert window.operator_action.isEnabled() is False
