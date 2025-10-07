#!/usr/bin/env python3
"""
Quick test to verify all UI components can be imported.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

print("🔍 Verificando imports de UI components...\n")

# Test imports
try:
    print("✓ Importando QApplication...")
    from PySide6.QtWidgets import QApplication

    print("✓ Importando CalibrationWizard...")
    from alignpress.ui.technician import CalibrationWizard

    print("✓ Importando ProfileEditor...")
    from alignpress.ui.technician import ProfileEditor

    print("✓ Importando DebugView...")
    from alignpress.ui.technician import DebugView

    print("✓ Importando Operator components...")
    from alignpress.ui.operator import SelectionWizard, LiveViewWidget, ValidationChecklistDialog

    print("✓ Importando Widgets...")
    from alignpress.ui.widgets import CameraWidget, MetricsPanel

    print("\n✅ Todos los imports funcionan correctamente!")
    print("\n📝 Puedes lanzar la aplicación con:")
    print("   python run_app.py --calibration       # Wizard de calibración")
    print("   python run_app.py --profile-editor    # Editor de profiles")
    print("   python run_app.py --debug             # Vista de debug")

except ImportError as e:
    print(f"\n❌ Error de import: {e}")
    sys.exit(1)
except Exception as e:
    print(f"\n⚠️ Error: {e}")
    sys.exit(1)
