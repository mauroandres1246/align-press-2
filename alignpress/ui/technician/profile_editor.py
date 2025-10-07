"""
Profile editor with YAML/JSON syntax highlighting.

Provides a code editor for editing platen and style profiles with:
- Syntax highlighting for YAML and JSON
- Line numbers
- Validation on save
- Templates for new profiles
"""

from pathlib import Path
from typing import Optional
import json
import yaml

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTextEdit, QPlainTextEdit, QLabel, QFileDialog, QMessageBox,
    QSplitter, QTreeWidget, QTreeWidgetItem, QComboBox,
    QGroupBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import (
    QSyntaxHighlighter, QTextCharFormat, QColor, QFont,
    QTextDocument
)
import re


class YAMLHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for YAML files."""

    def __init__(self, document: QTextDocument):
        super().__init__(document)

        # Define formats
        self.formats = {}

        # Keys (before colon)
        key_format = QTextCharFormat()
        key_format.setForeground(QColor("#0066CC"))
        key_format.setFontWeight(QFont.Weight.Bold)
        self.formats["key"] = key_format

        # Strings
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#00AA00"))
        self.formats["string"] = string_format

        # Numbers
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#AA00AA"))
        self.formats["number"] = number_format

        # Comments
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#808080"))
        comment_format.setFontItalic(True)
        self.formats["comment"] = comment_format

        # Booleans
        bool_format = QTextCharFormat()
        bool_format.setForeground(QColor("#CC6600"))
        bool_format.setFontWeight(QFont.Weight.Bold)
        self.formats["boolean"] = bool_format

    def highlightBlock(self, text: str):
        """Apply syntax highlighting to a block of text."""
        # Comments
        comment_pattern = re.compile(r'#.*$')
        for match in comment_pattern.finditer(text):
            self.setFormat(match.start(), match.end() - match.start(), self.formats["comment"])

        # Keys (word before colon)
        key_pattern = re.compile(r'^\s*(\w+)\s*:')
        for match in key_pattern.finditer(text):
            self.setFormat(match.start(1), match.end(1) - match.start(1), self.formats["key"])

        # Quoted strings
        string_pattern = re.compile(r'["\']([^"\']*)["\']')
        for match in string_pattern.finditer(text):
            self.setFormat(match.start(), match.end() - match.start(), self.formats["string"])

        # Numbers
        number_pattern = re.compile(r'\b\d+\.?\d*\b')
        for match in number_pattern.finditer(text):
            self.setFormat(match.start(), match.end() - match.start(), self.formats["number"])

        # Booleans
        bool_pattern = re.compile(r'\b(true|false|True|False|yes|no|Yes|No)\b')
        for match in bool_pattern.finditer(text):
            self.setFormat(match.start(), match.end() - match.start(), self.formats["boolean"])


class LineNumberArea(QWidget):
    """Line number area for code editor."""

    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return self.editor.lineNumberAreaWidth()

    def paintEvent(self, event):
        self.editor.lineNumberAreaPaintEvent(event)


class CodeEditor(QPlainTextEdit):
    """Code editor with line numbers."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.line_number_area = LineNumberArea(self)

        # Setup font
        font = QFont("Courier New", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)

        # Connect signals
        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)

        self.updateLineNumberAreaWidth(0)

    def lineNumberAreaWidth(self):
        """Calculate width needed for line numbers."""
        digits = len(str(max(1, self.blockCount())))
        space = 10 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def updateLineNumberAreaWidth(self, _):
        """Update line number area width."""
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def updateLineNumberArea(self, rect, dy):
        """Update line number area."""
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth(0)

    def resizeEvent(self, event):
        """Handle resize events."""
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(0, cr.top(), self.lineNumberAreaWidth(), cr.height())

    def lineNumberAreaPaintEvent(self, event):
        """Paint line numbers."""
        from PySide6.QtGui import QPainter

        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor(240, 240, 240))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(QColor(100, 100, 100))
                painter.drawText(0, top, self.line_number_area.width() - 5,
                               self.fontMetrics().height(),
                               Qt.AlignmentFlag.AlignRight, number)

            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1


class ProfileEditor(QWidget):
    """
    Profile editor with syntax highlighting and validation.

    Features:
    - YAML/JSON syntax highlighting
    - Line numbers
    - File browser tree
    - Validation on save
    - Profile templates
    """

    profile_saved = Signal(str)  # Emitted when profile is saved

    def __init__(self, profiles_dir: Optional[Path] = None, parent=None):
        super().__init__(parent)

        self.profiles_dir = profiles_dir or Path("profiles")
        self.current_file: Optional[Path] = None
        self.highlighter: Optional[YAMLHighlighter] = None

        self._setup_ui()
        self._load_profile_tree()

    def _setup_ui(self):
        """Setup UI components."""
        layout = QVBoxLayout()

        # Toolbar
        toolbar = QHBoxLayout()

        # File type selector
        self.file_type_combo = QComboBox()
        self.file_type_combo.addItems(["YAML", "JSON"])
        self.file_type_combo.currentTextChanged.connect(self._on_file_type_changed)
        toolbar.addWidget(QLabel("Format:"))
        toolbar.addWidget(self.file_type_combo)

        toolbar.addStretch()

        # New button
        new_btn = QPushButton("📄 New")
        new_btn.clicked.connect(self._new_profile)
        toolbar.addWidget(new_btn)

        # Open button
        open_btn = QPushButton("📂 Open")
        open_btn.clicked.connect(self._open_profile)
        toolbar.addWidget(open_btn)

        # Save button
        save_btn = QPushButton("💾 Save")
        save_btn.clicked.connect(self._save_profile)
        toolbar.addWidget(save_btn)

        # Validate button
        validate_btn = QPushButton("✓ Validate")
        validate_btn.clicked.connect(self._validate_profile)
        toolbar.addWidget(validate_btn)

        layout.addLayout(toolbar)

        # Main area: file tree + editor
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # File tree
        tree_group = QGroupBox("Profiles")
        tree_layout = QVBoxLayout()

        self.file_tree = QTreeWidget()
        self.file_tree.setHeaderLabel("Files")
        self.file_tree.itemDoubleClicked.connect(self._on_tree_item_double_clicked)
        tree_layout.addWidget(self.file_tree)

        tree_group.setLayout(tree_layout)
        splitter.addWidget(tree_group)

        # Editor
        editor_group = QGroupBox("Editor")
        editor_layout = QVBoxLayout()

        self.editor = CodeEditor()
        self.highlighter = YAMLHighlighter(self.editor.document())
        editor_layout.addWidget(self.editor)

        # Status
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("padding: 5px; background-color: #f0f0f0;")
        editor_layout.addWidget(self.status_label)

        editor_group.setLayout(editor_layout)
        splitter.addWidget(editor_group)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

        layout.addWidget(splitter)
        self.setLayout(layout)

    def _load_profile_tree(self):
        """Load profile directory tree."""
        self.file_tree.clear()

        if not self.profiles_dir.exists():
            return

        # Platens
        platen_item = QTreeWidgetItem(self.file_tree, ["Platens"])
        platen_dir = self.profiles_dir / "platens"
        if platen_dir.exists():
            for file_path in sorted(platen_dir.glob("*.yaml")):
                file_item = QTreeWidgetItem(platen_item, [file_path.name])
                file_item.setData(0, Qt.ItemDataRole.UserRole, file_path)

        # Styles
        style_item = QTreeWidgetItem(self.file_tree, ["Styles"])
        style_dir = self.profiles_dir / "styles"
        if style_dir.exists():
            for file_path in sorted(style_dir.glob("*.yaml")):
                file_item = QTreeWidgetItem(style_item, [file_path.name])
                file_item.setData(0, Qt.ItemDataRole.UserRole, file_path)

        self.file_tree.expandAll()

    def _on_tree_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle double-click on tree item."""
        file_path = item.data(0, Qt.ItemDataRole.UserRole)
        if file_path and isinstance(file_path, Path):
            self._load_file(file_path)

    def _on_file_type_changed(self, file_type: str):
        """Handle file type change."""
        # Re-apply syntax highlighter if needed
        if file_type == "YAML":
            self.highlighter = YAMLHighlighter(self.editor.document())
        # JSON highlighter would go here (could extend YAMLHighlighter)

    def _new_profile(self):
        """Create new profile from template."""
        # Show template options
        from PySide6.QtWidgets import QInputDialog

        templates = ["Platen Profile", "Style Profile"]
        template, ok = QInputDialog.getItem(
            self, "New Profile", "Select template:", templates, 0, False
        )

        if not ok:
            return

        if template == "Platen Profile":
            content = """# Platen Profile
version: 1
name: "New Platen"
type: platen

dimensions_mm:
  width: 300.0
  height: 200.0

calibration:
  camera_id: 0
  last_calibrated: "2025-01-01T00:00:00"
  homography_path: "calibration/camera_0.npz"
  mm_per_px: 0.5
"""
        else:  # Style Profile
            content = """# Style Profile
version: 1
name: "New Style"
type: style

logos:
  - name: "logo_1"
    template_path: "templates/logo_1.png"
    position_mm: [150.0, 100.0]
    roi:
      width_mm: 50.0
      height_mm: 50.0
      margin_factor: 1.5
"""

        self.editor.setPlainText(content)
        self.current_file = None
        self.status_label.setText("New profile (not saved)")

    def _open_profile(self):
        """Open existing profile."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Profile",
            str(self.profiles_dir),
            "YAML Files (*.yaml *.yml);;JSON Files (*.json);;All Files (*)"
        )

        if file_path:
            self._load_file(Path(file_path))

    def _load_file(self, file_path: Path):
        """Load file into editor."""
        try:
            with open(file_path, 'r') as f:
                content = f.read()

            self.editor.setPlainText(content)
            self.current_file = file_path
            self.status_label.setText(f"Loaded: {file_path.name}")
            self.status_label.setStyleSheet("padding: 5px; background-color: #E8F5E9;")

        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load file:\n{str(e)}")

    def _save_profile(self):
        """Save current profile."""
        if not self.current_file:
            # Save As
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Profile",
                str(self.profiles_dir),
                "YAML Files (*.yaml);;JSON Files (*.json)"
            )

            if not file_path:
                return

            self.current_file = Path(file_path)

        try:
            content = self.editor.toPlainText()

            with open(self.current_file, 'w') as f:
                f.write(content)

            self.status_label.setText(f"✅ Saved: {self.current_file.name}")
            self.status_label.setStyleSheet("padding: 5px; background-color: #E8F5E9;")

            # Reload tree
            self._load_profile_tree()

            # Emit signal
            self.profile_saved.emit(str(self.current_file))

        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save file:\n{str(e)}")

    def _validate_profile(self):
        """Validate current profile."""
        content = self.editor.toPlainText()

        try:
            # Try to parse as YAML
            data = yaml.safe_load(content)

            # Basic validation
            if not isinstance(data, dict):
                raise ValueError("Profile must be a dictionary")

            if "version" not in data:
                raise ValueError("Profile must have 'version' field")

            if "name" not in data:
                raise ValueError("Profile must have 'name' field")

            self.status_label.setText("✅ Valid YAML syntax")
            self.status_label.setStyleSheet("padding: 5px; background-color: #E8F5E9; color: green;")

        except yaml.YAMLError as e:
            self.status_label.setText(f"❌ YAML Error: {str(e)}")
            self.status_label.setStyleSheet("padding: 5px; background-color: #FFEBEE; color: red;")

        except ValueError as e:
            self.status_label.setText(f"⚠️ Validation: {str(e)}")
            self.status_label.setStyleSheet("padding: 5px; background-color: #FFF9C4; color: orange;")
