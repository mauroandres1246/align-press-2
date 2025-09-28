# Align-Press v2 - Setup Guide

Guía de instalación y configuración para el sistema de detección de logos.

## 🚀 Instalación Rápida

### 1. Clonar o descargar el proyecto

```bash
# Si usas git
git clone <repository-url>
cd align-press-v2

# O simplemente asegúrate de estar en el directorio del proyecto
cd align-press-v2
```

### 2. Crear entorno virtual (recomendado)

```bash
# Crear entorno virtual
python3 -m venv venv

# Activar entorno virtual
# En Linux/Mac:
source venv/bin/activate
# En Windows:
venv\Scripts\activate
```

### 3. Instalar dependencias

```bash
# Instalar dependencias básicas
pip install -r requirements.txt

# O instalar en modo desarrollo (incluye tools de testing)
pip install -e ".[dev]"
```

### 4. Validar instalación

```bash
# Ejecutar script de validación
python3 tools/validate_setup.py
```

Deberías ver algo como:
```
🎉 All validations passed! Project is ready for testing.
```

### 5. Generar templates de prueba

```bash
# Generar imágenes de template sintéticas para testing
python3 tools/create_test_templates.py
```

## 🧪 Testing Básico

### Ejecutar tests unitarios

```bash
# Ejecutar todos los tests
pytest

# Ejecutar tests con cobertura
pytest --cov=alignpress --cov-report=html

# Ejecutar solo tests rápidos (sin los marcados como 'slow')
pytest -m "not slow"
```

### Probar el detector CLI

```bash
# Ayuda del CLI
python3 -m alignpress.cli.test_detector --help

# Ejemplo con imagen estática (necesita templates generados)
python3 -m alignpress.cli.test_detector \
  --config config/example_detector.yaml \
  --image datasets/test_001.jpg \
  --save-debug output/debug_001.jpg \
  --verbose

# Ejemplo con cámara en vivo
python3 -m alignpress.cli.test_detector \
  --config config/example_detector.yaml \
  --camera 0 \
  --show \
  --fps 30
```

## 📁 Estructura del Proyecto

```
align-press-v2/
├── alignpress/               # 📦 Paquete principal
│   ├── core/                 #   🧠 Lógica de negocio
│   │   ├── detector.py       #     🎯 Detector principal
│   │   └── schemas.py        #     📋 Validación con Pydantic
│   ├── utils/                #   🔧 Utilidades
│   │   ├── geometry.py       #     📐 Funciones geométricas
│   │   └── image_utils.py    #     🖼️ Procesamiento de imágenes
│   ├── cli/                  #   💻 Herramientas CLI
│   │   └── test_detector.py  #     🧪 CLI para testing
│   └── ui/                   #   🖥️ Interfaz gráfica (futuro)
├── config/                   # ⚙️ Configuraciones
│   ├── app.yaml              #   🎛️ Config de la aplicación
│   └── example_detector.yaml #   🎯 Config de ejemplo del detector
├── profiles/                 # 📝 Perfiles de planchas/estilos
│   ├── planchas/             #   🔲 Configuraciones de planchas
│   ├── estilos/              #   🎨 Definiciones de estilos
│   └── variantes/            #   📏 Variaciones por talla
├── templates/                # 🖼️ Imágenes de referencia
├── tests/                    # 🧪 Tests automatizados
│   ├── unit/                 #   🔬 Tests unitarios
│   └── conftest.py           #   ⚙️ Configuración de pytest
└── tools/                    # 🛠️ Scripts auxiliares
    ├── validate_setup.py     #   ✅ Validación del setup
    └── create_test_templates.py # 🖼️ Generador de templates
```

## 🎯 Componentes Principales

### 1. **Core Detector** (`alignpress/core/detector.py`)
- Detector principal usando ORB + RANSAC
- Fallback a template matching
- Validación robusta con Pydantic schemas

### 2. **Utilities** (`alignpress/utils/`)
- **Geometry**: Funciones geométricas (ángulos, distancias, etc.)
- **Image Utils**: Procesamiento de imágenes (conversiones, ROI, etc.)

### 3. **CLI Tools** (`alignpress/cli/`)
- Tool de testing con imágenes estáticas y cámara en vivo
- Output detallado con tablas formateadas
- Generación de imágenes debug con overlays

### 4. **Configuration** (`config/`)
- Configuración de la aplicación (paths, UI, logging)
- Configuración del detector (planchas, logos, thresholds)

## 🔧 Configuración

### Configuración del Detector

Edita `config/example_detector.yaml`:

```yaml
version: 1

plane:
  width_mm: 300.0      # Ancho de la plancha en mm
  height_mm: 200.0     # Alto de la plancha en mm
  mm_per_px: 0.5       # Escala: mm por pixel

logos:
  - name: "pecho"
    template_path: "templates/logo_pecho.png"
    position_mm: [150.0, 100.0]  # Posición esperada [x, y]
    roi:
      width_mm: 50.0
      height_mm: 40.0
      margin_factor: 1.2
    angle_deg: 0.0

thresholds:
  position_tolerance_mm: 3.0    # Tolerancia de posición
  angle_tolerance_deg: 5.0      # Tolerancia angular
  min_inliers: 15               # Mínimo inliers RANSAC
  max_reproj_error: 3.0         # Error de reproyección máximo

features:
  feature_type: "ORB"           # ORB, AKAZE, SIFT
  nfeatures: 1500               # Máximo features a detectar
  scale_factor: 1.2
  nlevels: 8

fallback:
  enabled: true
  scales: [0.8, 0.9, 1.0, 1.1, 1.2]
  angles: [-10, -5, 0, 5, 10]
  match_threshold: 0.7
```

## 🐛 Troubleshooting

### Error: "No module named 'cv2'"
```bash
pip install opencv-python
```

### Error: "No module named 'alignpress'"
```bash
# Asegúrate de estar en el directorio correcto
cd align-press-v2

# Instala en modo desarrollo
pip install -e .
```

### Error: "Template file not found"
```bash
# Genera templates de prueba
python3 tools/create_test_templates.py
```

### Tests fallan con "OpenCV not available"
```bash
# Instala opencv
pip install opencv-python

# O ejecuta tests sin los que requieren OpenCV
pytest -k "not image_utils and not detector"
```

## 📈 Próximos Pasos

1. **Generar templates reales** - Reemplazar templates sintéticos con imágenes reales
2. **Calibrar cámara** - Usar el CLI de calibración (cuando esté implementado)
3. **Configurar perfiles** - Crear perfiles específicos para tus planchas/estilos
4. **Testing con datos reales** - Probar con imágenes de tu setup real
5. **UI Development** - Implementar la interfaz gráfica (Fase 3)

## 🆘 Soporte

Si encuentras problemas:

1. Verifica que todas las dependencias estén instaladas
2. Ejecuta `python3 tools/validate_setup.py`
3. Revisa los logs de error
4. Consulta la documentación técnica en `align_press_dev_plan.md`

---

**Estado actual**: ✅ Core implementado - Fase 0 y parte de Fase 1 completadas
**Próximo milestone**: CLI tools completos y tests de integración