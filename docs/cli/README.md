# Align-Press v2 - CLI Tools Documentation

Documentación completa de las herramientas de línea de comandos de Align-Press v2.

## 🎯 CLI Principal Unificado

**Align-Press v2** cuenta con un CLI principal que integra todas las herramientas:

```bash
# CLI principal con todos los subcomandos
python3 -m alignpress.cli.main --help

# O usar los comandos individuales directamente
python3 -m alignpress.cli.test_detector --help
```

## 🎯 Resumen de Herramientas

| Herramienta | Propósito | Estado |
|-------------|-----------|--------|
| `main` | 🎯 CLI principal unificado | ✅ Completado |
| `test_detector` | Testing del detector con imágenes/cámara | ✅ Completado |
| `calibrate` | Calibración interactiva de cámara | ✅ Completado |
| `validate_profile` | Validación de archivos de configuración | ✅ Completado |
| `benchmark` | Análisis de rendimiento del detector | ✅ Completado |

---

## 🎮 CLI Principal (main)

CLI unificado que integra todas las herramientas bajo un solo comando.

### Uso Básico

```bash
# Ayuda principal
python3 -m alignpress.cli.main --help

# Test con imagen
python3 -m alignpress.cli.main test --config config.yaml --image test.jpg

# Calibración de cámara
python3 -m alignpress.cli.main calibrate --camera 0 --pattern-size 9 6 --square-size-mm 25 --output cal.json

# Validar configuraciones
python3 -m alignpress.cli.main validate config/ --recursive

# Benchmark
python3 -m alignpress.cli.main benchmark --config config.yaml --dataset images/
```

---

## 🧪 test_detector

Herramienta principal para probar el detector de logos con imágenes estáticas o cámara en vivo.

### Uso Básico

```bash
# Ayuda completa
python -m alignpress.cli.test_detector --help

# Test con imagen estática
python -m alignpress.cli.test_detector \
  --config config/example_detector.yaml \
  --image datasets/test_001.jpg \
  --save-debug output/debug_001.jpg \
  --verbose

# Test con cámara en vivo
python -m alignpress.cli.test_detector \
  --config config/example_detector.yaml \
  --camera 0 \
  --show \
  --fps 30
```

### Argumentos

#### Requeridos
- `--config, -c`: Ruta al archivo de configuración del detector (YAML/JSON)
- Uno de:
  - `--image, -i`: Ruta a imagen de entrada
  - `--camera`: ID de dispositivo de cámara (normalmente 0)

#### Opcionales
- `--homography`: Ruta a archivo de calibración de homografía
- `--save-debug`: Ruta para guardar imagen con overlays de debug
- `--save-json`: Ruta para guardar resultados en JSON
- `--show`: Mostrar ventana de video en vivo (solo modo cámara)
- `--fps`: FPS objetivo para captura de cámara
- `--verbose, -v`: Salida detallada con métricas
- `--quiet, -q`: Suprimir salida no esencial

### Ejemplos Avanzados

```bash
# Test completo con todas las opciones
python -m alignpress.cli.test_detector \
  --config config/production_detector.yaml \
  --image datasets/test_polo_001.jpg \
  --homography calibration/camera_0/homography.json \
  --save-debug output/debug_polo_001.jpg \
  --save-json output/results_polo_001.json \
  --verbose

# Modo cámara con configuración específica
python -m alignpress.cli.test_detector \
  --config config/polo_detector.yaml \
  --camera 0 \
  --show \
  --fps 25 \
  --save-debug snapshots/ \
  --verbose
```

### Salida

**Modo verbose:**
```
[INFO] Cargando configuración desde config/example.yaml...
[INFO] Detector inicializado: 2 logos, ORB 1500 features
[INFO] Procesando imagen datasets/test_001.jpg...
[OK]   Logo 'pecho' detectado en (148.7, 100.3)mm
       Desviación: 1.4mm (tolerancia: 3.0mm) ✓
       Ángulo: 0.2° (error: 0.2°, tolerancia: 5.0°) ✓
       Inliers: 45/52 (86.5%), reproj_err: 1.2px
[WARN] Logo 'manga_izq' detectado en (52.8, 205.3)mm
       Desviación: 5.8mm (tolerancia: 3.0mm) ✗ AJUSTAR
       Ángulo: 2.1° (error: 2.1°, tolerancia: 5.0°) ✓
       Inliers: 38/48 (79.2%), reproj_err: 2.1px
[SUMMARY] 2/2 logos detectados, 1/2 OK, 1/2 requieren ajuste
```

---

## 📐 calibrate

Herramienta interactiva para calibración de cámara usando patrones de ajedrez.

### Uso Básico

```bash
# Calibración básica
python -m alignpress.cli.calibrate \
  --camera 0 \
  --pattern-size 9 6 \
  --square-size-mm 25.0 \
  --output calibration/camera_0/homography.json

# Calibración sin preview (modo headless)
python -m alignpress.cli.calibrate \
  --camera 0 \
  --pattern-size 9 6 \
  --square-size-mm 25.0 \
  --output calibration/camera_0/homography.json \
  --no-preview
```

### Argumentos

#### Requeridos
- `--camera, -c`: ID de dispositivo de cámara
- `--pattern-size`: Tamaño del patrón de ajedrez (ancho alto) en esquinas internas
- `--square-size-mm`: Tamaño de los cuadros del ajedrez en milímetros
- `--output, -o`: Ruta de salida para archivo de calibración (JSON)

#### Opcionales
- `--no-preview`: Ejecutar sin mostrar ventana de preview
- `--force`: Sobrescribir archivo de calibración existente

### Proceso de Calibración

1. **Preparación**: Imprimir patrón de ajedrez en papel rígido
2. **Captura**: Posicionar patrón en vista de cámara
3. **Detección**: Esperar detección automática del patrón
4. **Múltiples capturas**: Capturar desde diferentes ángulos/posiciones
5. **Cálculo**: Procesamiento automático de homografía y escala
6. **Validación**: Verificación de calidad de calibración

### Controles Interactivos

- **ESPACIO**: Capturar frame cuando el patrón esté detectado
- **Q**: Finalizar calibración y procesar resultados

### Criterios de Calidad

- Error de reproyección < 2.0 píxeles
- Tasa de detección de esquinas > 80%
- Variación de escala < 5%

### Archivo de Salida

```json
{
  "version": 1,
  "timestamp": "2025-09-28T14:30:00Z",
  "camera_id": 0,
  "homography": [[1.0, 0.0, 0.0], ...],
  "mm_per_px": 0.48,
  "pattern_info": {
    "type": "chessboard",
    "size": [9, 6],
    "square_size_mm": 25.0
  },
  "quality_metrics": {
    "reproj_error_px": 0.8,
    "corners_detected": 54,
    "corners_expected": 54
  }
}
```

---

## ✅ validate_profile

Herramienta para validar archivos de configuración contra schemas JSON.

### Uso Básico

```bash
# Validar archivo individual
python -m alignpress.cli.validate_profile \
  profiles/estilos/polo_basico.yaml

# Validar con schema específico
python -m alignpress.cli.validate_profile \
  profiles/estilos/polo_basico.yaml \
  --schema config/schemas/style.schema.json

# Validar directorio recursivamente
python -m alignpress.cli.validate_profile \
  profiles/ \
  --recursive

# Validar con correcciones automáticas
python -m alignpress.cli.validate_profile \
  profiles/ \
  --recursive \
  --fix-common
```

### Argumentos

#### Requeridos
- `path`: Ruta a archivo o directorio de profiles

#### Opcionales
- `--schema`: Ruta a archivo de schema JSON para validación
- `--recursive, -r`: Validar archivos recursivamente en subdirectorios
- `--fix-common`: Intentar corregir automáticamente problemas comunes
- `--quiet, -q`: Suprimir salida no esencial

### Tipos de Validación

#### Validación de Schema
- Estructura de campos
- Tipos de datos
- Rangos numéricos
- Valores de enumeración

#### Validación Semántica
- Archivos de template existen
- Posiciones dentro de plancha
- Calidad de imágenes template
- Referencias entre configuraciones

#### Correcciones Automáticas
- Añadir campo `version` faltante
- Convertir rutas relativas a absolutas
- Corregir formatos de fecha

### Salida

```
📋 Validation Summary
Total: 5 | Valid: 4 | Invalid: 1 | Fixed: 1

Validation Results
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━┳━━━━━━━┓
┃ File               ┃ Status ┃ Errors ┃ Warnings ┃ Fixed ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━╇━━━━━━━┩
│ polo_basico.yaml   │ ✓ VALID│   —    │    1     │   —   │
│ camiseta_basic.yaml│ ✗ INVALID│  2   │    —     │   ✓   │
└────────────────────┴────────┴────────┴──────────┴───────┘
```

---

## 📊 benchmark

Herramienta para análisis de rendimiento del detector sobre conjuntos de datos.

### Uso Básico

```bash
# Benchmark básico
python -m alignpress.cli.benchmark \
  --config config/example_detector.yaml \
  --dataset datasets/test_images/ \
  --output benchmark_results.json

# Benchmark limitado
python -m alignpress.cli.benchmark \
  --config config/example_detector.yaml \
  --dataset datasets/test_images/ \
  --samples 50 \
  --output benchmark_50_samples.json
```

### Argumentos

#### Requeridos
- `--config, -c`: Ruta a archivo de configuración del detector
- `--dataset, -d`: Ruta a directorio de dataset o imagen individual

#### Opcionales
- `--output, -o`: Ruta para guardar resultados de benchmark (JSON)
- `--samples, -s`: Limitar número de muestras a probar
- `--quiet, -q`: Suprimir salida no esencial

### Métricas Medidas

#### Timing
- Tiempo de carga de imagen
- Tiempo de detección
- Tiempo total por imagen
- FPS promedio

#### Memoria
- Uso de memoria base
- Pico de uso durante detección
- Uso promedio por imagen

#### Detección
- Tasa de éxito de detección
- Tiempo por logo
- Precisión de posicionamiento

### Salida

```
Benchmark Summary
Images: 100 | Success: 98 | Failed: 2 | Rate: 98.0%

Performance Metrics
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━┳━━━━━━┳━━━━━━┳━━━━━━━━━┓
┃ Metric             ┃ Mean  ┃ Median ┃ Min  ┃ Max  ┃ Std Dev ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━╇━━━━━━╇━━━━━━╇━━━━━━━━━┩
│ Load Time (ms)     │  15.2 │   14.8 │  8.1 │ 25.3 │     3.4 │
│ Detection Time (ms)│  45.7 │   44.2 │ 32.1 │ 67.8 │     8.2 │
│ Total Time (ms)    │  60.9 │   59.1 │ 42.3 │ 89.1 │    10.1 │
│ FPS                │  16.4 │   16.9 │ 11.2 │ 23.7 │     2.7 │
└────────────────────┴───────┴────────┴──────┴──────┴─────────┘

Memory Usage
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Metric          ┃ Value       ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ Peak Usage (MB) │ 145.2 ± 8.3│
│ Min Usage (MB)  │       128.4│
│ Max Usage (MB)  │       167.9│
└─────────────────┴─────────────┘
```

---

## 🔧 Configuración General

### Variables de Entorno

Los CLI tools soportan sustitución de variables de entorno en archivos de configuración:

```yaml
# En archivo de configuración
log_path: "${LOG_DIR:/tmp/logs}"
camera_id: "${CAMERA_ID:0}"
```

### Archivos de Configuración

Todos los CLI tools aceptan configuraciones en:
- **YAML**: `.yaml`, `.yml`
- **JSON**: `.json`

### Paths Relativos

Los paths en configuraciones se resuelven relativos al directorio actual, excepto cuando se especifica una ruta absoluta.

---

## 📚 Ejemplos de Workflows

### Workflow Completo de Setup

```bash
# 1. Validar configuraciones
python -m alignpress.cli.validate_profile config/ --recursive

# 2. Calibrar cámara
python -m alignpress.cli.calibrate \
  --camera 0 \
  --pattern-size 9 6 \
  --square-size-mm 25.0 \
  --output calibration/camera_0/homography.json

# 3. Probar detector
python -m alignpress.cli.test_detector \
  --config config/example_detector.yaml \
  --image datasets/test_001.jpg \
  --homography calibration/camera_0/homography.json \
  --save-debug output/debug.jpg \
  --verbose

# 4. Benchmark de rendimiento
python -m alignpress.cli.benchmark \
  --config config/example_detector.yaml \
  --dataset datasets/test_images/ \
  --output benchmark_results.json
```

### Workflow de Desarrollo

```bash
# Validar cambios en profiles
python -m alignpress.cli.validate_profile profiles/ --recursive --fix-common

# Test rápido con cámara
python -m alignpress.cli.test_detector \
  --config config/development.yaml \
  --camera 0 \
  --show \
  --verbose

# Benchmark de desarrollo (muestra pequeña)
python -m alignpress.cli.benchmark \
  --config config/development.yaml \
  --dataset datasets/dev_samples/ \
  --samples 10
```

---

## 🐛 Troubleshooting

### Problemas Comunes

#### "No module named 'alignpress'"
```bash
# Instalar en modo desarrollo
pip install -e .

# O añadir al PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

#### "Camera not found"
```bash
# Listar cámaras disponibles
python -c "import cv2; print([i for i in range(10) if cv2.VideoCapture(i).isOpened()])"

# Probar con diferentes IDs
python -m alignpress.cli.test_detector --config config.yaml --camera 1
```

#### "Template file not found"
```bash
# Verificar paths en configuración
python -m alignpress.cli.validate_profile config/detector.yaml

# Generar templates de prueba
python tools/create_test_templates.py
```

#### "JSON schema validation failed"
```bash
# Instalar jsonschema
pip install jsonschema

# Validar manualmente
python -c "
import json, yaml, jsonschema
with open('config/schemas/detector.schema.json') as f: schema = json.load(f)
with open('config/detector.yaml') as f: data = yaml.safe_load(f)
jsonschema.validate(data, schema)
"
```

### Logs de Debug

Para obtener más información de debug:

```bash
# Activar logging verbose
export ALIGNPRESS_LOG_LEVEL=DEBUG

# O usar --verbose en cada comando
python -m alignpress.cli.test_detector --config config.yaml --image test.jpg --verbose
```

---

## 📝 Contribuir

Para añadir nuevos CLI tools:

1. Crear archivo en `alignpress/cli/`
2. Seguir patrones de argumentos establecidos
3. Usar `rich` para output formateado
4. Añadir documentación aquí
5. Crear tests en `tests/integration/`

### Template de CLI Tool

```python
#!/usr/bin/env python3
"""
CLI tool for [purpose].
"""

import argparse
import sys
from rich.console import Console

console = Console()

def main() -> int:
    parser = argparse.ArgumentParser(description="[Description]")
    # Add arguments...

    args = parser.parse_args()

    try:
        # Implementation...
        return 0
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return 1

if __name__ == '__main__':
    sys.exit(main())
```