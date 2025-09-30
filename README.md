# Align-Press v2

Sistema de Detección y Alineación de Logos para Prensas Textiles.

Pipeline robusto OpenCV + ORB para Raspberry Pi con UI operador/técnico.

## 🎯 Estado del Proyecto

```
[██████████░░░░░░░░░░] 50% Completado

✅ Fase 0: Refactoring del Detector    [██████████] 100%
✅ Fase 1: CLI Tools & Infrastructure  [██████████] 100%
⏸️ Fase 2: Core Business Logic         [░░░░░░░░░░]   0%
⏸️ Fase 3: UI Operador (MVP)           [░░░░░░░░░░]   0%
⏸️ Fase 4: UI Técnico                  [░░░░░░░░░░]   0%
📅 Fase 5: Deployment Raspberry Pi     [░░░░░░░░░░]   0%
```

**Componentes completados:**
- ✅ Detector ORB + RANSAC con fallback template matching
- ✅ Utilidades geométricas y de procesamiento de imagen
- ✅ Schemas Pydantic v2 para validación robusta
- ✅ CLI completo (test, calibrate, validate, benchmark)
- ✅ Configuration management centralizado
- ✅ Structured logging con structlog
- ✅ JSON schemas para validación de configuraciones
- ✅ Tests de integración completos
- ✅ Documentación exhaustiva CLI tools

## 🚀 Instalación Rápida

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Validar instalación
python3 tools/validate_setup.py

# 3. Generar templates de prueba
python3 tools/create_test_templates.py

# 4. Probar el CLI principal
python3 -m alignpress.cli.main --help

# 5. Probar el detector con imagen
python -m alignpress.cli test \
  --config config/platen_50x60_detector.yaml \
  --image test_image.jpg \
  --save-debug debug_output.jpg \
  --save-json results.json

# 6. Validar configuraciones
python3 -m alignpress.cli.main validate config/ --recursive

# 🎯 TESTING CON TU PLANCHA REAL (50cm x 60cm)
# Script simplificado para tu setup específico
python3 tools/testing/quick_test_your_platen.py
```

## 🧪 Testing con Plancha Real

Para probar el sistema con tu plancha de **50cm x 60cm**:

```bash
# Opción 1: Script rápido simplificado
python3 tools/testing/quick_test_your_platen.py

# Opción 2: Workflow completo automatizado
python3 tools/testing/complete_testing_workflow.py \
  --calibration-image datasets/calibration/platen_with_chessboard.jpg \
  --logo-image datasets/real_templates/logo_source.jpg \
  --pattern-size 9 6 \
  --square-size-mm 25.0 \
  --logo-position-mm 250 300
```

**Imágenes requeridas:**
1. **Calibración**: Foto de tu plancha con patrón de ajedrez 9x6 (cuadros de 25mm)
2. **Logo template**: Imagen clara del logo a detectar
3. **Testing**: Fotos con logo en diferentes posiciones

Ver detalles completos en [`tools/testing/README.md`](tools/testing/README.md)

## 📁 Estructura del Proyecto

```
align-press-v2/
├── alignpress/               # 📦 Código fuente
│   ├── core/                 #   🧠 Lógica de negocio
│   │   ├── detector.py       #     🎯 Detector principal (ORB+RANSAC)
│   │   └── schemas.py        #     📋 Validación Pydantic
│   ├── utils/                #   🔧 Utilidades compartidas
│   │   ├── geometry.py       #     📐 Funciones geométricas
│   │   └── image_utils.py    #     🖼️ Procesamiento de imagen
│   ├── cli/                  #   💻 Herramientas CLI
│   │   └── test_detector.py  #     🧪 Testing del detector
│   ├── ui/                   #   🖥️ Interfaz PySide6 (futuro)
│   └── hardware/             #   🔌 Abstracciones hardware (futuro)
├── config/                   # ⚙️ Configuración principal
├── profiles/                 # 📝 Perfiles de planchas/estilos
├── templates/                # 🖼️ Imágenes de referencia
├── tests/                    # 🧪 Testing automatizado
└── tools/                    # 🛠️ Scripts auxiliares
```

## 🎮 Uso

### CLI Tools Completos

```bash
# Ayuda del CLI principal
python3 -m alignpress.cli.main --help

# Test con imagen estática
python3 -m alignpress.cli.main test \
  --config config/example_detector.yaml \
  --image datasets/test_001.jpg \
  --save-debug output/debug_001.jpg \
  --verbose

# Test con cámara en vivo
python3 -m alignpress.cli.main test \
  --config config/example_detector.yaml \
  --camera 0 \
  --show \
  --fps 30

# Calibración de cámara
python3 -m alignpress.cli.main calibrate \
  --camera 0 \
  --pattern-size 9 6 \
  --square-size-mm 25.0 \
  --output calibration/camera_0.json

# Validar configuraciones
python3 -m alignpress.cli.main validate \
  config/ --recursive

# Benchmark de rendimiento
python3 -m alignpress.cli.main benchmark \
  --config config/example_detector.yaml \
  --dataset datasets/ \
  --samples 50
```

### Ejecutar Tests

```bash
# Tests unitarios
pytest tests/unit/

# Tests con cobertura
pytest --cov=alignpress

# Tests rápidos (sin los marcados como 'slow')
pytest -m "not slow"
```

## 📖 Documentación

- **[SETUP.md](SETUP.md)** - Guía detallada de instalación y configuración
- **[align_press_dev_plan.md](align_press_dev_plan.md)** - Plan completo de desarrollo y arquitectura
- **[config/](config/)** - Ejemplos de configuración
- **[tests/](tests/)** - Tests unitarios y fixtures

## 🏗️ Arquitectura

### Principios de Diseño

1. **Separación de responsabilidades**: Core (sin UI) → CLI → UI
2. **Testeable**: Cada módulo tiene tests unitarios independientes
3. **Configurable**: YAML para humanos, JSON para máquinas
4. **Escalable**: Preparado para 2 cámaras + Arduino
5. **Portable**: Desktop (dev) → Raspberry Pi (prod)

### Tecnologías

- **OpenCV**: Procesamiento de imagen y detección de features
- **ORB**: Feature detector (libre de patentes, rápido)
- **RANSAC**: Verificación geométrica robusta
- **Pydantic**: Validación y serialización de datos
- **Rich**: CLI con formato elegante
- **pytest**: Testing framework

## 🛠️ Desarrollo

### Estructura de Commits

```
[T0.5] Añadir schemas Pydantic para validación

- PlaneConfigSchema con validación de dimensiones
- LogoSpecSchema con verificación de paths
- Tests unitarios para schemas
```

### Testing

```bash
# Ejecutar todos los tests
pytest

# Test específico
pytest tests/unit/test_geometry.py::TestAngleDeg::test_angle_deg_quadrants

# Con cobertura HTML
pytest --cov=alignpress --cov-report=html
```

## 🚀 Próximos Pasos

1. **✅ Fase 1 Completada**: CLI tools y infrastructure 100% funcional
2. **🎯 Iniciar Fase 2**: Core business logic (profiles, compositions, job cards)
3. **🎮 Preparar Fase 3**: UI operador MVP con PySide6
4. **🔧 Fase 4**: Interfaz técnica avanzada
5. **🚀 Fase 5**: Deployment en Raspberry Pi

## 🐛 Troubleshooting

Revisa **[SETUP.md](SETUP.md)** para soluciones a problemas comunes.

## 📊 Métricas

- **Tests**: 50+ tests unitarios
- **Cobertura**: >85% en módulos core
- **Dependencias**: Mínimas y bien definidas
- **Documentación**: Completa y actualizada

---

**Creado con ❤️ siguiendo las mejores prácticas de desarrollo Python**