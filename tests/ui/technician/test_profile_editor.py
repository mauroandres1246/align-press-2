"""Tests for profile editor."""

import pytest
from pathlib import Path
from PySide6.QtWidgets import QApplication

from alignpress.ui.technician.profile_editor import ProfileEditor, CodeEditor, YAMLHighlighter


@pytest.fixture
def qapp():
    """Create QApplication instance."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class TestCodeEditor:
    """Tests for CodeEditor."""

    def test_editor_initialization(self, qapp):
        """Test editor initializes correctly."""
        editor = CodeEditor()

        assert editor is not None
        assert editor.line_number_area is not None

    def test_editor_has_monospace_font(self, qapp):
        """Test editor uses monospace font."""
        editor = CodeEditor()

        font = editor.font()
        assert font.family() in ["Courier New", "Monospace"]

    def test_line_number_area_width(self, qapp):
        """Test line number area width calculation."""
        editor = CodeEditor()

        width = editor.lineNumberAreaWidth()
        assert width > 0


class TestYAMLHighlighter:
    """Tests for YAMLHighlighter."""

    def test_highlighter_initialization(self, qapp):
        """Test highlighter initializes correctly."""
        editor = CodeEditor()
        highlighter = YAMLHighlighter(editor.document())

        assert highlighter is not None
        assert len(highlighter.formats) > 0

    def test_highlighter_has_formats(self, qapp):
        """Test highlighter has all required formats."""
        editor = CodeEditor()
        highlighter = YAMLHighlighter(editor.document())

        assert "key" in highlighter.formats
        assert "string" in highlighter.formats
        assert "number" in highlighter.formats
        assert "comment" in highlighter.formats
        assert "boolean" in highlighter.formats


class TestProfileEditor:
    """Tests for ProfileEditor."""

    def test_editor_initialization(self, qapp, tmp_path):
        """Test editor initializes correctly."""
        editor = ProfileEditor(profiles_dir=tmp_path)

        assert editor is not None
        assert editor.profiles_dir == tmp_path
        assert editor.current_file is None
        assert editor.highlighter is not None

    def test_editor_has_all_components(self, qapp, tmp_path):
        """Test editor has all UI components."""
        editor = ProfileEditor(profiles_dir=tmp_path)

        assert editor.file_type_combo is not None
        assert editor.file_tree is not None
        assert editor.editor is not None
        assert editor.status_label is not None

    def test_file_type_combo_has_options(self, qapp, tmp_path):
        """Test file type combo has YAML and JSON."""
        editor = ProfileEditor(profiles_dir=tmp_path)

        assert editor.file_type_combo.count() == 2
        assert editor.file_type_combo.itemText(0) == "YAML"
        assert editor.file_type_combo.itemText(1) == "JSON"

    def test_new_profile_creates_template(self, qapp, tmp_path, qtbot):
        """Test new profile creates template content."""
        editor = ProfileEditor(profiles_dir=tmp_path)

        # Mock the dialog to select "Platen Profile"
        def mock_get_item(parent, title, label, items, current, editable):
            return items[0], True  # Return "Platen Profile"

        from PySide6.QtWidgets import QInputDialog
        original = QInputDialog.getItem
        QInputDialog.getItem = mock_get_item

        try:
            editor._new_profile()

            # Check that editor has content
            content = editor.editor.toPlainText()
            assert "version:" in content
            assert "name:" in content
            assert "Platen Profile" in content or "New Platen" in content

        finally:
            QInputDialog.getItem = original

    def test_validate_profile_with_valid_yaml(self, qapp, tmp_path):
        """Test validation with valid YAML."""
        editor = ProfileEditor(profiles_dir=tmp_path)

        valid_yaml = """
version: 1
name: "Test Profile"
type: platen
"""

        editor.editor.setPlainText(valid_yaml)
        editor._validate_profile()

        # Should show success
        assert "Valid" in editor.status_label.text() or "✅" in editor.status_label.text()

    def test_validate_profile_with_invalid_yaml(self, qapp, tmp_path):
        """Test validation with invalid YAML."""
        editor = ProfileEditor(profiles_dir=tmp_path)

        invalid_yaml = """
version: 1
name: "Test Profile
  indentation error
"""

        editor.editor.setPlainText(invalid_yaml)
        editor._validate_profile()

        # Should show error
        assert "Error" in editor.status_label.text() or "❌" in editor.status_label.text()

    def test_load_profile_tree(self, qapp, tmp_path):
        """Test loading profile directory tree."""
        # Create mock directory structure
        platens_dir = tmp_path / "platens"
        platens_dir.mkdir()
        (platens_dir / "platen1.yaml").write_text("version: 1\nname: platen1")

        styles_dir = tmp_path / "styles"
        styles_dir.mkdir()
        (styles_dir / "style1.yaml").write_text("version: 1\nname: style1")

        editor = ProfileEditor(profiles_dir=tmp_path)

        # Check tree has items
        assert editor.file_tree.topLevelItemCount() == 2  # Platens and Styles
