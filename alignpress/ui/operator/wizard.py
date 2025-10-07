"""
Selection wizard for operator mode.

Implements a 3-step wizard: Platen → Style → Size
"""

from typing import Optional, List
from pathlib import Path

from PySide6.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QLabel, QPushButton,
    QRadioButton, QButtonGroup, QWidget, QGroupBox,
    QScrollArea
)
from PySide6.QtCore import Qt, Signal, QSettings
from PySide6.QtGui import QPixmap

from alignpress.core.profile import PlatenProfile, StyleProfile, SizeVariant, ProfileLoader
from alignpress.core.composition import Composition


class SelectionWizard(QWizard):
    """
    Wizard for selecting platen, style, and size.

    Emits composition_created signal when complete.
    """

    composition_created = Signal(Composition)

    def __init__(self, profiles_path: Path, parent: Optional[QWidget] = None) -> None:
        """
        Initialize selection wizard.

        Args:
            profiles_path: Path to profiles directory
            parent: Parent widget
        """
        super().__init__(parent)

        self.profiles_path = profiles_path
        self.loader = ProfileLoader(profiles_path)

        # Settings for remembering last selection
        self.settings = QSettings("Align-Press", "v2")

        # Selected items
        self.selected_platen: Optional[PlatenProfile] = None
        self.selected_style: Optional[StyleProfile] = None
        self.selected_variant: Optional[SizeVariant] = None

        self._setup_wizard()

    def _setup_wizard(self) -> None:
        """Setup wizard pages."""
        self.setWindowTitle("Selección de Trabajo")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)

        # Add pages
        self.platen_page = PlatenSelectionPage(self.loader, self.settings)
        self.style_page = StyleSelectionPage(self.loader, self.settings)
        self.size_page = SizeSelectionPage(self.settings)

        self.addPage(self.platen_page)
        self.addPage(self.style_page)
        self.addPage(self.size_page)

        # Connect page signals
        print("🔌 Connecting platen_page.platen_selected signal...")
        self.platen_page.platen_selected.connect(self._on_platen_selected)
        print("🔌 Connecting style_page.style_selected signal...")
        self.style_page.style_selected.connect(self._on_style_selected)
        print("🔌 Connecting size_page.variant_selected signal...")
        self.size_page.variant_selected.connect(self._on_variant_selected)

        # Connect finish
        print("🔌 Connecting wizard finished signal...")
        self.finished.connect(self._on_wizard_finished)
        print("✅ All signals connected")

        # Sync wizard state with pages (pages may have restored selections before signals were connected)
        if self.platen_page.selected_platen:
            print(f"🔄 Syncing platen from page: {self.platen_page.selected_platen.name}")
            self.selected_platen = self.platen_page.selected_platen
        if self.style_page.selected_style:
            print(f"🔄 Syncing style from page: {self.style_page.selected_style.name}")
            self.selected_style = self.style_page.selected_style

    def _on_platen_selected(self, platen: PlatenProfile) -> None:
        """Handle platen selection."""
        print(f"🔧 Wizard received platen signal: {platen.name}")
        self.selected_platen = platen

    def _on_style_selected(self, style: StyleProfile) -> None:
        """Handle style selection."""
        print(f"🔧 Wizard received style signal: {style.name}")
        self.selected_style = style

    def _on_variant_selected(self, variant: Optional[SizeVariant]) -> None:
        """Handle variant selection."""
        self.selected_variant = variant

    def _on_wizard_finished(self, result: int) -> None:
        """Handle wizard finish."""
        print(f"📋 Wizard finished callback - result: {result}")
        print(f"   Selected platen: {self.selected_platen.name if self.selected_platen else None}")
        print(f"   Selected style: {self.selected_style.name if self.selected_style else None}")
        print(f"   Selected variant: {self.selected_variant.name if self.selected_variant else None}")

        if result == QWizard.DialogCode.Accepted:
            print(f"   ✅ Result is Accepted")
            if self.selected_platen and self.selected_style:
                print(f"   ✅ Have platen and style - creating composition")
                # Create composition
                composition = Composition(
                    platen=self.selected_platen,
                    style=self.selected_style,
                    variant=self.selected_variant
                )

                print(f"   🚀 Emitting composition_created signal")
                self.composition_created.emit(composition)
                print(f"   ✅ Signal emitted")
            else:
                print(f"   ❌ Missing platen or style!")
        else:
            print(f"   ❌ Result is NOT Accepted (rejected/cancelled)")


class PlatenSelectionPage(QWizardPage):
    """Page for selecting platen."""

    platen_selected = Signal(PlatenProfile)

    def __init__(self, loader: ProfileLoader, settings: QSettings) -> None:
        """
        Initialize platen selection page.

        Args:
            loader: Profile loader
            settings: Settings for remembering selection
        """
        super().__init__()

        self.loader = loader
        self.settings = settings
        self.selected_platen: Optional[PlatenProfile] = None

        self._setup_ui()
        self._load_platens()

    def _setup_ui(self) -> None:
        """Setup UI components."""
        self.setTitle("Paso 1: Seleccionar Plancha")
        self.setSubTitle("Seleccione la plancha a utilizar")

        layout = QVBoxLayout()

        # List of platens
        self.platen_list = QListWidget()
        self.platen_list.currentItemChanged.connect(self._on_selection_changed)
        layout.addWidget(self.platen_list)

        # Info panel
        self.info_label = QLabel("Seleccione una plancha para ver detalles")
        self.info_label.setWordWrap(True)
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.info_label)

        self.setLayout(layout)

    def _load_platens(self) -> None:
        """Load available platens."""
        platen_dir = self.loader.base_dir / "planchas"

        if not platen_dir.exists():
            self.info_label.setText(f"Directorio de planchas no encontrado: {platen_dir}")
            return

        # Block signals during initial load
        self.platen_list.blockSignals(True)

        # Load all platen files
        for platen_file in platen_dir.glob("*.yaml"):
            try:
                platen = self.loader.load_platen(platen_file.stem)
                item = QListWidgetItem(platen.name)
                item.setData(Qt.ItemDataRole.UserRole, platen)
                self.platen_list.addItem(item)
            except Exception as e:
                print(f"Error loading platen {platen_file}: {e}")

        # Restore last selection
        last_platen = self.settings.value("last_platen", "")
        if last_platen:
            for i in range(self.platen_list.count()):
                item = self.platen_list.item(i)
                platen = item.data(Qt.ItemDataRole.UserRole)
                if platen.name == last_platen:
                    self.platen_list.setCurrentItem(item)
                    # Manually set selected_platen since signals are blocked
                    self.selected_platen = platen
                    break

        # Unblock signals
        self.platen_list.blockSignals(False)

        # If we had a selection, update the info display (but don't emit signal yet - wizard will connect later)
        if self.selected_platen:
            current = self.platen_list.currentItem()
            if current:
                self._update_info_display(current)

    def _update_info_display(self, item: QListWidgetItem) -> None:
        """Update info display for given item."""
        platen = item.data(Qt.ItemDataRole.UserRole)

        info_text = f"<b>{platen.name}</b><br><br>"
        info_text += f"Dimensiones: {platen.dimensions_mm['width']:.0f}mm × {platen.dimensions_mm['height']:.0f}mm<br>"

        if platen.calibration:
            age_days = platen.calibration.age_days
            if platen.calibration.is_expired:
                info_text += f"<font color='red'>⚠️ Calibración vencida ({age_days} días)</font><br>"
            elif age_days > 23:  # Warning threshold
                info_text += f"<font color='orange'>⚠️ Calibración próxima a vencer ({age_days} días)</font><br>"
            else:
                info_text += f"<font color='green'>✓ Calibración vigente ({age_days} días)</font><br>"
        else:
            info_text += "<font color='red'>⚠️ Sin calibración</font><br>"

        self.info_label.setText(info_text)

    def _on_selection_changed(self, current: QListWidgetItem, previous: QListWidgetItem) -> None:
        """Handle selection change."""
        if current:
            platen = current.data(Qt.ItemDataRole.UserRole)
            self.selected_platen = platen

            # Update info display
            self._update_info_display(current)

            # Save selection
            self.settings.setValue("last_platen", platen.name)

            # Emit signal to wizard
            print(f"📤 PlatenPage emitting signal: {platen.name}")
            self.platen_selected.emit(platen)

            # Enable next button
            self.completeChanged.emit()

    def isComplete(self) -> bool:
        """Check if page is complete."""
        return self.selected_platen is not None


class StyleSelectionPage(QWizardPage):
    """Page for selecting style."""

    style_selected = Signal(StyleProfile)

    def __init__(self, loader: ProfileLoader, settings: QSettings) -> None:
        """
        Initialize style selection page.

        Args:
            loader: Profile loader
            settings: Settings for remembering selection
        """
        super().__init__()

        self.loader = loader
        self.settings = settings
        self.selected_style: Optional[StyleProfile] = None

        self._setup_ui()
        self._load_styles()

    def _setup_ui(self) -> None:
        """Setup UI components."""
        self.setTitle("Paso 2: Seleccionar Estilo")
        self.setSubTitle("Seleccione el estilo de prenda")

        layout = QVBoxLayout()

        # List of styles
        self.style_list = QListWidget()
        self.style_list.currentItemChanged.connect(self._on_selection_changed)
        layout.addWidget(self.style_list)

        # Info panel
        self.info_label = QLabel("Seleccione un estilo para ver detalles")
        self.info_label.setWordWrap(True)
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.info_label)

        self.setLayout(layout)

    def _load_styles(self) -> None:
        """Load available styles."""
        style_dir = self.loader.base_dir / "estilos"

        if not style_dir.exists():
            self.info_label.setText(f"Directorio de estilos no encontrado: {style_dir}")
            return

        # Block signals during initial load
        self.style_list.blockSignals(True)

        # Load all style files
        for style_file in style_dir.glob("*.yaml"):
            try:
                style = self.loader.load_style(style_file.stem)
                item = QListWidgetItem(style.name)
                item.setData(Qt.ItemDataRole.UserRole, style)
                self.style_list.addItem(item)
            except Exception as e:
                print(f"Error loading style {style_file}: {e}")

        # Restore last selection
        last_style = self.settings.value("last_style", "")
        if last_style:
            for i in range(self.style_list.count()):
                item = self.style_list.item(i)
                style = item.data(Qt.ItemDataRole.UserRole)
                if style.name == last_style:
                    self.style_list.setCurrentItem(item)
                    # Manually set selected_style since signals are blocked
                    self.selected_style = style
                    break

        # Unblock signals
        self.style_list.blockSignals(False)

        # If we had a selection, update the info display (but don't emit signal yet - wizard will connect later)
        if self.selected_style:
            current = self.style_list.currentItem()
            if current:
                self._update_info_display(current)

    def _update_info_display(self, item: QListWidgetItem) -> None:
        """Update info display for given item."""
        style = item.data(Qt.ItemDataRole.UserRole)

        info_text = f"<b>{style.name}</b><br><br>"
        info_text += f"Tipo: {style.type}<br>"
        info_text += f"Logos: {len(style.logos)}<br>"

        if style.description:
            info_text += f"<br>{style.description}<br>"

        # List logos
        if style.logos:
            info_text += "<br><b>Logos incluidos:</b><br>"
            for logo in style.logos:
                info_text += f"  • {logo.name} ({logo.position_mm[0]:.0f}, {logo.position_mm[1]:.0f})mm<br>"

        self.info_label.setText(info_text)

    def _on_selection_changed(self, current: QListWidgetItem, previous: QListWidgetItem) -> None:
        """Handle selection change."""
        if current:
            style = current.data(Qt.ItemDataRole.UserRole)
            self.selected_style = style

            # Update info display
            self._update_info_display(current)

            # Save selection
            self.settings.setValue("last_style", style.name)

            # Emit signal
            print(f"📤 StylePage emitting signal: {style.name}")
            self.style_selected.emit(style)

            # Enable next button
            self.completeChanged.emit()

    def isComplete(self) -> bool:
        """Check if page is complete."""
        return self.selected_style is not None


class SizeSelectionPage(QWizardPage):
    """Page for selecting size variant (optional)."""

    variant_selected = Signal(object)  # SizeVariant or None

    def __init__(self, settings: QSettings) -> None:
        """
        Initialize size selection page.

        Args:
            settings: Settings for remembering selection
        """
        super().__init__()

        self.settings = settings
        self.selected_variant: Optional[SizeVariant] = None
        self.loader: Optional[ProfileLoader] = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup UI components."""
        self.setTitle("Paso 3: Seleccionar Talla (Opcional)")
        self.setSubTitle("Seleccione la talla si aplica variantes")

        layout = QVBoxLayout()

        # Radio buttons group
        self.button_group = QButtonGroup()

        # No variant option
        self.no_variant_radio = QRadioButton("Sin variante (usar posiciones base)")
        self.no_variant_radio.setChecked(True)
        self.no_variant_radio.toggled.connect(self._on_variant_toggled)
        self.button_group.addButton(self.no_variant_radio, 0)
        layout.addWidget(self.no_variant_radio)

        # Scroll area for variant options
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        self.variants_layout = QVBoxLayout(scroll_widget)
        scroll.setWidget(scroll_widget)

        layout.addWidget(scroll)

        # Info label
        self.info_label = QLabel("Las variantes permiten ajustar posiciones por talla")
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)

        self.setLayout(layout)

    def initializePage(self) -> None:
        """Initialize page (called when entering)."""
        # Get wizard
        wizard = self.wizard()
        if isinstance(wizard, SelectionWizard):
            self.loader = wizard.loader
            self._load_variants()

    def _load_variants(self) -> None:
        """Load available size variants."""
        if not self.loader:
            return

        # Clear existing variant buttons (except "no variant")
        for i in reversed(range(self.variants_layout.count())):
            widget = self.variants_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        variant_dir = self.loader.base_dir / "variantes"

        if not variant_dir.exists():
            self.info_label.setText("No hay variantes disponibles")
            return

        # Load all variant files
        variants_found = False
        for variant_file in variant_dir.glob("*.yaml"):
            try:
                variant = self.loader.load_variant(variant_file.stem)
                variants_found = True

                radio = QRadioButton(f"{variant.name} ({variant.size})")
                radio.setProperty("variant", variant)
                radio.toggled.connect(self._on_variant_toggled)

                # Add button to group and layout
                button_id = self.button_group.buttons().__len__()
                self.button_group.addButton(radio, button_id)
                self.variants_layout.addWidget(radio)

            except Exception as e:
                print(f"Error loading variant {variant_file}: {e}")

        if not variants_found:
            self.info_label.setText("No se encontraron variantes de talla")
        else:
            # Restore last selection
            last_variant = self.settings.value("last_variant", "")
            if last_variant:
                for button in self.button_group.buttons():
                    variant = button.property("variant")
                    if variant and variant.name == last_variant:
                        button.setChecked(True)
                        break

    def _on_variant_toggled(self, checked: bool) -> None:
        """Handle variant selection."""
        if not checked:
            return

        sender = self.sender()

        if sender == self.no_variant_radio:
            self.selected_variant = None
            self.info_label.setText("Se usarán las posiciones base del estilo")
            self.settings.setValue("last_variant", "")
        else:
            variant = sender.property("variant")
            if variant:
                self.selected_variant = variant

                # Update info
                info_text = f"<b>{variant.name}</b><br>"
                info_text += f"Tamaño: {variant.size}<br><br>"

                info_text += "<b>Offsets aplicados:</b><br>"
                for logo_name, offset in variant.offsets.items():
                    info_text += f"  • {logo_name}: ({offset[0]:+.1f}, {offset[1]:+.1f})mm<br>"

                self.info_label.setText(info_text)

                # Save selection
                self.settings.setValue("last_variant", variant.name)

        # Emit signal
        self.variant_selected.emit(self.selected_variant)

        # Page is always complete (variant is optional)
        self.completeChanged.emit()

    def isComplete(self) -> bool:
        """Check if page is complete."""
        # Always complete (variant is optional)
        return True
