# 🧪 Guía de Setup para Pruebas del Algoritmo Align-Press v2

Esta guía te explica paso a paso cómo preparar archivos y configurar el sistema para comenzar a probar el algoritmo de detección de logos.

## 📁 Estructura de Archivos Requerida

```
align-press-v2/
├── datasets/
│   ├── calibration/
│   │   └── platen_50x60/
│   │       ├── pattern_image.jpg         # Imagen de calibración con patrón
│   │       ├── calibration.json         # Datos de calibración (generado)
│   │       └── quality_metrics.json     # Métricas de calidad (generado)
│   ├── templates/
│   │   ├── main_logo.png               # Template principal del logo
│   │   ├── variations/                 # Variaciones del template (opcional)
│   │   │   ├── main_logo_rot_+15deg.png
│   │   │   ├── main_logo_rot_-15deg.png
│   │   │   └── main_logo_scale_0.95.png
│   │   └── source_images/              # Imágenes fuente para extracción
│   │       └── logo_source.jpg
│   └── test_images/
│       ├── correct_position/           # Imágenes con logo en posición correcta
│       │   ├── test_001.jpg
│       │   ├── test_002.jpg
│       │   └── test_003.jpg
│       └── incorrect_position/         # Imágenes con logo mal posicionado
│           ├── test_fail_001.jpg
│           ├── test_fail_002.jpg
│           └── test_fail_003.jpg
├── config/
│   └── platen_50x60_detector.yaml     # Configuración del detector
└── results/
    ├── calibration/                    # Resultados de calibración
    ├── evaluation/                     # Resultados de evaluación
    └── debug/                          # Imágenes de debug
```

## 🎯 Paso 1: Preparar Imagen de Calibración

### Requisitos:
- **Tamaño del platen**: 50cm x 60cm
- **Patrón**: Tablero de ajedrez 9x6 esquinas internas (10x7 cuadros)
- **Tamaño de cuadro**: 25mm x 25mm

### Nombre del archivo:
```
datasets/calibration/platen_50x60/pattern_image.jpg
```

### Cómo crear la imagen:
1. Imprime el patrón desde: https://calib.io/pages/camera-calibration-pattern-generator
2. Configuración: Chessboard, 10x7 squares, 25mm size
3. Coloca el patrón en el centro del platen
4. Toma una foto desde la posición normal de la cámara
5. Asegúrate que todo el patrón sea visible y nítido

### Ejemplo de comando para calibrar:
```bash
python tools/testing/calibrate_from_image.py \
  --image calibration/platen_50x60/pattern_image.jpg \
  --output datasets/calibration/platen_50x60/ \
  --pattern-size 9 6 \
  --square-size-mm 25
```

## 🏷️ Paso 2: Preparar Template del Logo

### 2A. Si tu logo ya tiene transparencia (PNG):

**Nombre del archivo:**
```
datasets/templates/main_logo.png
```

**Requisitos:**
- Formato: PNG con canal alpha
- Resolución: 200-500px de ancho recomendado
- Fondo: Transparente
- Contenido: Solo el logo sin elementos extras

### 2B. Si tu logo NO tiene transparencia:

**Nombre del archivo fuente:**
```
datasets/templates/source_images/logo_source.jpg
```

**Comando para extraer template:**
```bash
# Extracción interactiva (recomendado)
python tools/testing/extract_template.py \
  --input datasets/templates/source_images/logo_source.jpg \
  --output datasets/templates/main_logo.png \
  --interactive \
  --add-transparency contour \
  --enhance

# Extracción manual (si conoces las coordenadas)
python tools/testing/extract_template.py \
  --input datasets/templates/source_images/logo_source.jpg \
  --output datasets/templates/main_logo.png \
  --roi 100 50 200 150 \
  --add-transparency threshold \
  --enhance
```

**Métodos de transparencia disponibles:**
- `contour`: Mejor para logos con bordes definidos
- `threshold`: Mejor para logos simples con colores sólidos
- `grabcut`: Mejor para logos complejos (más lento)

## ⚙️ Paso 3: Configurar el Detector

**Archivo de configuración:**
```
config/platen_50x60_detector.yaml
```

**Contenido básico:**
```yaml
version: 1

plane:
  width_mm: 500.0
  height_mm: 600.0
  mm_per_px: 0.4  # Ajustar según tu calibración

logos:
  - name: "main_logo"
    template_path: "datasets/templates/main_logo.png"
    position_mm: [250.0, 300.0]  # Centro del platen
    roi:
      width_mm: 100.0   # Región de búsqueda
      height_mm: 80.0
      margin_factor: 1.5
    angle_deg: 0.0
    has_transparency: true
    transparency_method: "contour"  # o "threshold", "grabcut"

thresholds:
  position_tolerance_mm: 5.0
  angle_tolerance_deg: 10.0
  min_inliers: 15
  max_reproj_error: 2.0

features:
  feature_type: "ORB"
  max_features: 1000
  edge_threshold: 31
  patch_size: 31
  n_levels: 8
  scale_factor: 1.2

fallback:
  enabled: true
  template_threshold: 0.7
  multi_scale: true
  scales: [0.8, 0.9, 1.0, 1.1, 1.2]
  angles: [-15, -10, -5, 0, 5, 10, 15]
```

**Parámetros importantes a ajustar:**
- `mm_per_px`: Obtenido de la calibración
- `position_mm`: Posición esperada del logo en mm
- `roi.width_mm` y `roi.height_mm`: Región de búsqueda
- `position_tolerance_mm`: Tolerancia de posición aceptable

## 📸 Paso 4: Preparar Imágenes de Prueba

### 4A. Imágenes con posición correcta:
```
datasets/test_images/correct_position/test_001.jpg
datasets/test_images/correct_position/test_002.jpg
datasets/test_images/correct_position/test_003.jpg
```

**Características:**
- Logo en la posición esperada (±5mm de tolerancia)
- Iluminación similar a condiciones reales
- Diferentes ángulos leves del logo (-10° a +10°)

### 4B. Imágenes con posición incorrecta:
```
datasets/test_images/incorrect_position/test_fail_001.jpg
datasets/test_images/incorrect_position/test_fail_002.jpg
datasets/test_images/incorrect_position/test_fail_003.jpg
```

**Características:**
- Logo fuera de la tolerancia de posición
- Logo rotado más de la tolerancia
- Sin logo visible
- Logo parcialmente oculto

## 🚀 Paso 5: Ejecutar Pruebas

### Configurar el entorno de pruebas:
```bash
python tools/testing/setup_testing_environment.py \
  --output datasets/ \
  --platen-type 50x60
```

### Ejecutar evaluación completa:
```bash
python tools/testing/run_full_evaluation.py \
  --config config/platen_50x60_detector.yaml \
  --calibration datasets/calibration/platen_50x60/ \
  --test-images datasets/test_images/ \
  --output results/evaluation/
```

### Comandos individuales para debug:

**1. Probar detección en imagen individual:**
```bash
python -m alignpress.cli detect \
  --config config/platen_50x60_detector.yaml \
  --image datasets/test_images/correct_position/test_001.jpg \
  --output results/debug/single_detection.json \
  --debug
```

**2. Benchmark de rendimiento:**
```bash
python -m alignpress.cli benchmark \
  --config config/platen_50x60_detector.yaml \
  --test-images datasets/test_images/ \
  --iterations 10
```

## 📊 Paso 6: Interpretar Resultados

### Archivos de salida esperados:
```
results/
├── evaluation/
│   ├── evaluation_report.html      # Reporte visual completo
│   ├── summary.json               # Métricas resumidas
│   ├── detailed_results.json      # Resultados detallados
│   └── detection_images/          # Imágenes con detecciones marcadas
├── calibration/
│   └── quality_report.html        # Calidad de calibración
└── debug/
    ├── detection_debug.jpg        # Imagen con debug overlay
    └── feature_matches.jpg        # Coincidencias de features
```

### Métricas clave a revisar:

**En `summary.json`:**
```json
{
  "accuracy": 0.95,              // > 0.90 es bueno
  "precision": 0.92,             // > 0.85 es bueno
  "recall": 0.88,                // > 0.80 es bueno
  "avg_position_error_mm": 2.1,  // < 3.0 es bueno
  "avg_angle_error_deg": 3.5,    // < 5.0 es bueno
  "avg_processing_time_ms": 85   // < 200ms es bueno
}
```

## 🔧 Troubleshooting

### ❌ Error: "Template not found"
**Solución:** Verifica que el archivo `datasets/templates/main_logo.png` existe y la ruta en el config es correcta.

### ❌ Error: "Calibration not found"
**Solución:** Ejecuta primero la calibración:
```bash
python tools/testing/calibrate_from_image.py --image calibration/platen_50x60/pattern_image.jpg --output datasets/calibration/platen_50x60/ --pattern-size 9 6 --square-size-mm 25
```

### ❌ Detección muy lenta (>500ms)
**Posibles causas:**
- Demasiadas features: Reduce `max_features` a 500-800
- ROI muy grande: Reduce `roi.width_mm` y `roi.height_mm`
- Imagen muy grande: Redimensiona imágenes a max 1920x1080

### ❌ Baja precisión de detección (<80%)
**Posibles soluciones:**
1. Mejora el template:
   ```bash
   python tools/testing/extract_template.py --input source.jpg --output template.png --interactive --enhance --add-transparency contour
   ```

2. Ajusta parámetros del detector:
   ```yaml
   thresholds:
     position_tolerance_mm: 10.0  # Aumentar tolerancia
     min_inliers: 10              # Reducir requisito

   features:
     max_features: 1500           # Más features
     edge_threshold: 20           # Más sensible
   ```

3. Genera variaciones del template:
   ```bash
   python tools/testing/extract_template.py --input source.jpg --output template.png --generate-variations --variations-dir datasets/templates/variations/
   ```

### ❌ Template sin transparencia no funciona bien
**Solución:** Usa la herramienta de extracción con background removal:
```bash
python tools/testing/extract_template.py \
  --input datasets/templates/source_images/logo_source.jpg \
  --output datasets/templates/main_logo.png \
  --interactive \
  --add-transparency contour \
  --enhance
```

## 📝 Lista de Verificación

Antes de empezar las pruebas, asegúrate de tener:

- [ ] ✅ Imagen de calibración con patrón de ajedrez
- [ ] ✅ Template del logo (PNG con transparencia preferiblemente)
- [ ] ✅ Archivo de configuración del detector
- [ ] ✅ Al menos 3 imágenes de prueba correctas
- [ ] ✅ Al menos 3 imágenes de prueba incorrectas
- [ ] ✅ Calibración ejecutada y exitosa
- [ ] ✅ Entorno virtual activado
- [ ] ✅ Dependencias instaladas (`pip install -e .`)

## 🎯 Ejemplo Rápido de Setup Completo

```bash
# 1. Crear estructura
python tools/testing/setup_testing_environment.py --output datasets/ --platen-type 50x60

# 2. Calibrar (coloca tu imagen de patrón primero)
python tools/testing/calibrate_from_image.py \
  --image calibration/platen_50x60/pattern_image.jpg \
  --output datasets/calibration/platen_50x60/ \
  --pattern-size 9 6 --square-size-mm 25

# 3. Extraer template (coloca tu imagen fuente primero)
python tools/testing/extract_template.py \
  --input datasets/templates/source_images/logo_source.jpg \
  --output datasets/templates/main_logo.png \
  --interactive --add-transparency contour --enhance

# 4. Ejecutar evaluación (coloca tus imágenes de prueba primero)
python tools/testing/run_full_evaluation.py \
  --config config/platen_50x60_detector.yaml \
  --calibration datasets/calibration/platen_50x60/ \
  --test-images datasets/test_images/ \
  --output results/evaluation/

# 5. Ver resultados
open results/evaluation/evaluation_report.html
```

¡Ahora estás listo para probar el algoritmo! 🚀