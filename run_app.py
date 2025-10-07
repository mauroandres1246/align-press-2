#!/usr/bin/env python3
"""
Launch script for Align-Press v2 UI.

Usage:
    python run_app.py                    # Launch operator mode
    python run_app.py --technician       # Launch technician mode
    python run_app.py --calibration      # Launch calibration wizard
    python run_app.py --profile-editor   # Launch profile editor
    python run_app.py --debug            # Launch debug view
"""

import sys
import argparse
from pathlib import Path

from PySide6.QtWidgets import QApplication

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Align-Press v2 UI Launcher")
    parser.add_argument(
        "--mode",
        choices=["operator", "technician", "calibration", "profile-editor", "debug"],
        default="operator",
        help="Launch mode"
    )
    parser.add_argument(
        "--calibration",
        action="store_const",
        const="calibration",
        dest="mode",
        help="Launch calibration wizard"
    )
    parser.add_argument(
        "--profile-editor",
        action="store_const",
        const="profile-editor",
        dest="mode",
        help="Launch profile editor"
    )
    parser.add_argument(
        "--debug",
        action="store_const",
        const="debug",
        dest="mode",
        help="Launch debug view"
    )
    parser.add_argument(
        "--technician",
        action="store_const",
        const="technician",
        dest="mode",
        help="Launch technician mode"
    )
    parser.add_argument(
        "--composition",
        type=str,
        help="Path to composition for debug view"
    )

    args = parser.parse_args()

    # Create QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("Align-Press v2")
    app.setOrganizationName("Align-Press")

    # Launch appropriate mode
    if args.mode == "calibration":
        from alignpress.ui.technician import CalibrationWizard
        window = CalibrationWizard()
        window.show()

    elif args.mode == "profile-editor":
        from alignpress.ui.technician import ProfileEditor
        from PySide6.QtWidgets import QMainWindow

        main_window = QMainWindow()
        main_window.setWindowTitle("Profile Editor - Align-Press v2")
        main_window.resize(1200, 800)

        editor = ProfileEditor(profiles_dir=Path("profiles"))
        main_window.setCentralWidget(editor)
        main_window.show()
        window = main_window

    elif args.mode == "debug":
        from alignpress.ui.technician import DebugView
        from alignpress.core.composition import Composition
        from alignpress.core.profile import PlatenProfile, StyleProfile, CalibrationInfo, LogoDefinition
        from datetime import datetime
        import numpy as np
        import cv2
        from PySide6.QtWidgets import QMainWindow

        # Create a demo composition for testing
        # Create a temporary template
        template_dir = Path("tests/fixtures/templates")
        template_dir.mkdir(parents=True, exist_ok=True)
        template_path = template_dir / "demo_template.png"

        if not template_path.exists():
            # Create a simple checkerboard template
            template = np.ones((80, 60, 3), dtype=np.uint8) * 255
            square_size = 10
            for i in range(0, 60, square_size):
                for j in range(0, 80, square_size):
                    if (i // square_size + j // square_size) % 2 == 0:
                        template[i:i+square_size, j:j+square_size] = [0, 0, 0]
            cv2.imwrite(str(template_path), template)

        platen = PlatenProfile(
            version=1,
            name="Demo Platen",
            type="platen",
            dimensions_mm={"width": 300.0, "height": 200.0},
            calibration=CalibrationInfo(
                camera_id=0,
                last_calibrated=datetime.now(),
                homography_path="calibration/demo.npz",
                mm_per_px=0.5
            )
        )

        style = StyleProfile(
            version=1,
            name="Demo Style",
            type="style",
            logos=[
                LogoDefinition(
                    name="demo_logo",
                    template_path=str(template_path),
                    position_mm=[150.0, 100.0],
                    roi={"width_mm": 80.0, "height_mm": 60.0}
                )
            ]
        )

        composition = Composition(platen=platen, style=style)

        main_window = QMainWindow()
        main_window.setWindowTitle("Debug View - Align-Press v2")
        main_window.resize(1400, 900)

        debug_view = DebugView(composition=composition, camera_id=0)
        main_window.setCentralWidget(debug_view)
        main_window.show()

        debug_view.start()
        window = main_window

    else:
        # Operator or Technician mode (full app)
        from alignpress.ui.main_window import MainWindow
        from alignpress.ui.operator import SelectionWizard, LiveViewWidget
        from PySide6.QtWidgets import QWidget, QVBoxLayout, QStackedWidget, QPushButton
        from pathlib import Path

        window = MainWindow()

        # Create a container for operator flow
        operator_container = QWidget()
        operator_layout = QVBoxLayout(operator_container)
        operator_layout.setContentsMargins(0, 0, 0, 0)

        operator_stack = QStackedWidget()
        operator_layout.addWidget(operator_stack)

        # Create welcome screen with button to start wizard
        welcome_screen = QWidget()
        welcome_layout = QVBoxLayout(welcome_screen)
        welcome_layout.addStretch()

        from PySide6.QtWidgets import QLabel
        from PySide6.QtCore import Qt

        title = QLabel("Align-Press v2")
        title.setStyleSheet("font-size: 32pt; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_layout.addWidget(title)

        subtitle = QLabel("Sistema de Alineación de Logos")
        subtitle.setStyleSheet("font-size: 16pt;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_layout.addWidget(subtitle)

        welcome_layout.addSpacing(40)

        start_btn = QPushButton("Iniciar Nuevo Trabajo")
        start_btn.setStyleSheet("font-size: 14pt; padding: 20px;")
        start_btn.setMinimumWidth(300)
        welcome_layout.addWidget(start_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        welcome_layout.addStretch()

        operator_stack.addWidget(welcome_screen)

        # Track current live view
        current_live_view = None

        # Handler for composition created
        def on_composition_created(composition):
            nonlocal current_live_view

            print(f"✅ Composition created: {composition.platen.name} + {composition.style.name}")

            # Create live view
            live_view = LiveViewWidget(composition=composition, camera_id=0)
            operator_stack.addWidget(live_view)
            operator_stack.setCurrentWidget(live_view)
            live_view.start()
            current_live_view = live_view

            print(f"✅ Live view started and shown")

        # When start button clicked, show wizard
        def show_wizard():
            wizard = SelectionWizard(profiles_path=Path("profiles"))
            wizard.composition_created.connect(on_composition_created)

            print(f"🔷 Showing wizard...")
            result = wizard.exec()  # Show as modal dialog
            print(f"🔷 Wizard finished with result: {result}")

        start_btn.clicked.connect(show_wizard)

        window.set_operator_view(operator_container)

        # TODO: Setup technical view when ready

        window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
