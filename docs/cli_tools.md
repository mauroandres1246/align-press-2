# Align-Press CLI Tools - Guía Completa

Esta guía documenta todas las herramientas de línea de comandos (CLI) de Align-Press v2.

## Tabla de Contenidos

1. [Instalación](#instalación)
2. [Calibración de Cámara](#calibración-de-cámara)
3. [Validación de Profiles](#validación-de-profiles)
4. [Benchmark de Performance](#benchmark-de-performance)
5. [Troubleshooting](#troubleshooting)

---

## Instalación

### Requisitos

- Python 3.10+
- OpenCV 4.x
- Todas las dependencias en `requirements.txt`

### Instalación desde repositorio

```bash
# Clonar repositorio
git clone https://github.com/your-org/align-press-v2.git
cd align-press-v2

# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Verificar instalación
python -m alignpress.cli --help
```

---

## Calibración de Cámara

La calibración de cámara es **necesaria antes de usar el detector** para obtener la homografía que mapea píxeles de la imagen a coordenadas reales en milímetros sobre la plancha.

### Uso Básico

```bash
python -m alignpress.cli.calibrate \
  --camera 0 \
  --pattern-size 9 6 \
  --square-size-mm 25.0 \
  --output calibration/camera_0/homography.json
```

### Parámetros

| Parámetro | Tipo | Descripción | Requerido |
|-----------|------|-------------|-----------|
| `--camera`, `-c` | int | ID del dispositivo de cámara (usualmente 0) | ✅ |
| `--pattern-size` | int int | Tamaño del patrón de ajedrez (ancho alto) en esquinas internas | ✅ |
| `--square-size-mm` | float | Tamaño de los cuadrados del tablero en milímetros | ✅ |
| `--output`, `-o` | path | Ruta donde guardar el archivo de calibración | ✅ |
| `--no-preview` | flag | Ejecutar sin mostrar ventana de previsualización (modo headless) | ❌ |
| `--force` | flag | Sobrescribir archivo existente sin confirmar | ❌ |

### Proceso de Calibración

1. **Preparación del patrón:**
   - Imprime un tablero de ajedrez de 9×6 esquinas
   - Monta el tablero en una superficie plana y rígida
   - Ilumina uniformemente sin reflejos

2. **Posicionamiento:**
   - Coloca el tablero completamente visible en el centro del campo de visión
   - Asegúrate de que las esquinas externas sean visibles
   - Mantén la cámara estable (usa un trípode si es posible)

3. **Captura:**
   - El programa mostrará el feed de la cámara en vivo
   - Cuando detecte el patrón, dibujará las esquinas en verde
   - Presiona **ESPACIO** para capturar el frame actual
   - Se recomienda capturar **10-15 frames** desde diferentes ángulos ligeros

4. **Validación:**
   - El programa calculará automáticamente:
     - Homografía 3×3
     - Escala mm/px
     - Error de reproyección
   - Si la calidad es baja, se te pedirá recalibrar

### Ejemplo Completo

```bash
# Calibración con preview interactivo
python -m alignpress.cli.calibrate \
  --camera 0 \
  --pattern-size 9 6 \
  --square-size-mm 25.0 \
  --output calibration/camera_0/homography_2025-10-01.json

# Calibración headless (servidor sin pantalla)
python -m alignpress.cli.calibrate \
  --camera 0 \
  --pattern-size 9 6 \
  --square-size-mm 25.0 \
  --output calibration/camera_0/homography.json \
  --no-preview \
  --force
```

### Formato del Archivo de Salida

```json
{
  "version": 1,
  "timestamp": "2025-10-01T14:30:00Z",
  "camera_id": 0,
  "pattern_info": {
    "type": "chessboard",
    "size": [9, 6],
    "square_size_mm": 25.0
  },
  "homography": [
    [1.02, -0.01, 45.3],
    [0.01, 1.01, 30.2],
    [0.0001, 0.0001, 1.0]
  ],
  "mm_per_px": 0.48,
  "quality_metrics": {
    "reproj_error_px": 0.82,
    "corners_detected": 54,
    "corners_expected": 54,
    "scale_consistency": 0.012
  }
}
```

### Interpretación de Métricas de Calidad

| Métrica | Bueno | Aceptable | Malo | Acción |
|---------|-------|-----------|------|--------|
| `reproj_error_px` | < 1.0 | 1.0 - 2.0 | > 2.0 | Recalibrar con mejor iluminación |
| `corners_detected` | 100% | ≥ 80% | < 80% | Usar patrón más grande o acercarse |
| `scale_consistency` | < 0.02 | 0.02 - 0.05 | > 0.05 | Verificar que patrón sea plano |

---

## Validación de Profiles

Valida archivos de configuración de profiles (planchas, estilos, variantes) contra sus schemas.

### Uso Básico

```bash
# Validar un archivo individual
python -m alignpress.cli.validate_profile \
  profiles/estilos/polo_basico.yaml

# Validar todos los archivos en un directorio
python -m alignpress.cli.validate_profile \
  profiles/estilos/ \
  --recursive

# Validar con auto-corrección de errores comunes
python -m alignpress.cli.validate_profile \
  profiles/ \
  --recursive \
  --fix-common
```

### Parámetros

| Parámetro | Tipo | Descripción | Requerido |
|-----------|------|-------------|-----------|
| `path` | path | Ruta al archivo o directorio de profiles | ✅ |
| `--schema` | path | Ruta al archivo JSON schema para validación estricta | ❌ |
| `--recursive`, `-r` | flag | Validar archivos recursivamente en subdirectorios | ❌ |
| `--fix-common` | flag | Intentar corregir automáticamente errores comunes | ❌ |
| `--quiet`, `-q` | flag | Suprimir output excepto errores | ❌ |

### Validaciones Realizadas

1. **Schema YAML/JSON:**
   - Sintaxis correcta
   - Campos requeridos presentes
   - Tipos de datos correctos

2. **Validación Semántica:**
   - Templates existen en filesystem
   - Rutas relativas se resuelven correctamente
   - Dimensiones son válidas (width/height > 0)

3. **Validación de Composición:**
   - Posiciones de logos dentro de límites de plancha
   - ROIs no se solapan
   - Ángulos en rango válido (-180° a 180°)

4. **Validación de Referencias:**
   - Template paths apuntan a archivos existentes
   - Homography paths son válidos
   - Calibrations no están vencidas

### Errores Comunes y Auto-Correcciones

| Error | Auto-corrección | Ejemplo |
|-------|-----------------|---------|
| Ruta relativa rota | Busca archivo en paths estándar | `template.png` → `templates/logos/template.png` |
| Versión faltante | Añade `version: 1` | — |
| Metadata faltante | Añade bloque `metadata: {}` | — |
| Trailing whitespace | Elimina espacios al final | — |
| Duplicación de campos | Mantiene último valor | — |

### Ejemplo de Output

```
📋 Validating Profiles

╭────────────────────────────┬────────┬──────────╮
│ Profile                    │ Status │ Issues   │
├────────────────────────────┼────────┼──────────┤
│ polo_basico.yaml           │ ✓      │ 0        │
│ plancha_300x200.yaml       │ ⚠      │ 1        │
│ variante_polo_xl.yaml      │ ✗      │ 3        │
╰────────────────────────────┴────────┴──────────╯

📋 Detailed Errors:

plancha_300x200.yaml:
  ⚠ Calibration is 45 days old (recommended: < 30 days)

variante_polo_xl.yaml:
  ✗ logos must be a non-empty list
  ✗ Template file not found: templates/logos/missing.png
  ✗ Position (350, 250) outside platen bounds (300x200)
```

### Validación con JSON Schema

Para validación estricta usando JSON schemas:

```bash
python -m alignpress.cli.validate_profile \
  profiles/estilos/polo_basico.yaml \
  --schema config/schemas/style.schema.json
```

Esto valida contra el schema oficial, útil para **CI/CD pipelines**.

---

## Benchmark de Performance

Mide el rendimiento del detector sobre un dataset de imágenes.

### Uso Básico

```bash
python -m alignpress.cli.benchmark \
  --config config/detector_config.yaml \
  --dataset datasets/test_images/ \
  --output benchmark_results.json
```

### Parámetros

| Parámetro | Tipo | Descripción | Requerido |
|-----------|------|-------------|-----------|
| `--config`, `-c` | path | Ruta al archivo de configuración del detector | ✅ |
| `--dataset`, `-d` | path | Ruta al directorio de imágenes o imagen única | ✅ |
| `--output`, `-o` | path | Ruta donde guardar resultados en JSON | ❌ |
| `--samples`, `-s` | int | Limitar número de imágenes a procesar | ❌ |
| `--quiet`, `-q` | flag | Suprimir output excepto resumen final | ❌ |

### Métricas Medidas

1. **Tiempo de Procesamiento:**
   - Tiempo total por imagen (ms)
   - Tiempo promedio (ms)
   - Tiempo mínimo/máximo
   - FPS (frames por segundo)

2. **Detección:**
   - Tasa de detección por logo
   - Confidence promedio
   - Inliers promedio
   - Error de reproyección

3. **Memoria:**
   - Uso de memoria pico (MB)
   - Uso de memoria promedio

### Ejemplo de Output

```
🎯 Align-Press Detector Benchmark

Configuration: config/detector_config.yaml
Dataset: datasets/test_images/ (100 images)

Processing... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:50

📊 Performance Summary

╭────────────────────────┬─────────────╮
│ Metric                 │ Value       │
├────────────────────────┼─────────────┤
│ Total Samples          │ 100         │
│ Average Time (ms)      │ 52.3        │
│ Min Time (ms)          │ 38.1        │
│ Max Time (ms)          │ 89.5        │
│ Std Deviation (ms)     │ 12.4        │
│ FPS (average)          │ 19.1        │
│ Total Time (s)         │ 5.23        │
╰────────────────────────┴─────────────╯

📈 Detection Stats

╭────────────────┬──────────┬────────────┬──────────────╮
│ Logo           │ Found    │ Avg Conf   │ Avg Inliers  │
├────────────────┼──────────┼────────────┼──────────────┤
│ pecho          │ 98/100   │ 0.87       │ 48.2         │
│ manga_izq      │ 95/100   │ 0.82       │ 42.5         │
│ manga_der      │ 97/100   │ 0.84       │ 44.1         │
╰────────────────┴──────────┴────────────┴──────────────╯

💾 Results saved to: benchmark_results.json
```

### Formato de Archivo de Salida

```json
{
  "timestamp": "2025-10-01T15:30:00Z",
  "config_path": "config/detector_config.yaml",
  "dataset_path": "datasets/test_images/",
  "summary": {
    "total_samples": 100,
    "avg_time_ms": 52.3,
    "min_time_ms": 38.1,
    "max_time_ms": 89.5,
    "std_time_ms": 12.4,
    "fps": 19.1,
    "total_time_s": 5.23
  },
  "logo_stats": {
    "pecho": {
      "detection_rate": 0.98,
      "avg_confidence": 0.87,
      "avg_inliers": 48.2,
      "avg_reproj_error": 1.4
    }
  },
  "samples": [
    {
      "image_path": "datasets/test_images/test_001.jpg",
      "total_time_ms": 51.2,
      "logo_results": [
        {
          "logo_name": "pecho",
          "found": true,
          "time_ms": 48.5,
          "confidence": 0.89
        }
      ]
    }
  ]
}
```

### Uso en CI/CD

Para integrar en pipelines de testing:

```bash
# Run benchmark y fallar si FPS < threshold
python -m alignpress.cli.benchmark \
  --config config/detector_config.yaml \
  --dataset datasets/test_images/ \
  --samples 50 \
  --output benchmark.json \
  --quiet

# Check results
python scripts/check_benchmark_threshold.py \
  --results benchmark.json \
  --min-fps 15 \
  --min-detection-rate 0.90
```

### Optimización con Benchmark

1. **Identificar Cuellos de Botella:**
   - Si `avg_time_ms` es alto (>100ms en desktop), revisa número de features
   - Si detección falla, aumenta `nfeatures` o ajusta thresholds

2. **Comparar Configuraciones:**
   ```bash
   # Benchmark con ORB
   python -m alignpress.cli.benchmark \
     --config config/orb_config.yaml \
     --dataset datasets/ \
     --output bench_orb.json

   # Benchmark con AKAZE
   python -m alignpress.cli.benchmark \
     --config config/akaze_config.yaml \
     --dataset datasets/ \
     --output bench_akaze.json

   # Comparar
   python scripts/compare_benchmarks.py bench_orb.json bench_akaze.json
   ```

3. **Target Performance (Raspberry Pi 4):**
   - FPS: ≥ 10 (para operación en tiempo real)
   - Tiempo promedio: ≤ 100ms
   - Detection rate: ≥ 95%

---

## Troubleshooting

### Calibración

**Problema:** Cámara no detectada
```
Error: Could not open camera 0
```
**Solución:**
- Verifica que la cámara esté conectada: `ls /dev/video*`
- Prueba otro ID de cámara: `--camera 1`
- Verifica permisos: añade usuario a grupo `video`

**Problema:** Tablero no detectado
```
⚠ Chessboard not detected in frame
```
**Solución:**
- Mejora la iluminación (evita sombras y reflejos)
- Acerca el tablero a la cámara
- Verifica el tamaño del patrón (`--pattern-size` correcto)
- Asegúrate de que todo el tablero sea visible

**Problema:** Calibración de baja calidad
```
⚠ High reprojection error: 5.23px > 2.0px
```
**Solución:**
- Usa un tablero más grande y rígido
- Captura más frames desde diferentes ángulos
- Mejora el enfoque de la cámara
- Reduce la distancia al tablero

### Validación

**Problema:** Template no encontrado
```
✗ Template file not found: templates/logo.png
```
**Solución:**
- Verifica que el archivo existe: `ls templates/logo.png`
- Usa `--fix-common` para auto-corregir rutas
- Actualiza el path en el profile manualmente

**Problema:** Posiciones fuera de límites
```
✗ Position (350, 250) outside platen bounds (300x200)
```
**Solución:**
- Edita el profile y ajusta `position_mm`
- Verifica que las dimensiones de la plancha sean correctas
- Considera cambiar a una plancha más grande

### Benchmark

**Problema:** Performance muy lenta
```
Average Time (ms): 250.5
FPS: 4.0
```
**Solución:**
- Reduce `nfeatures` en config (prueba 1000 en vez de 1500)
- Desactiva fallback template matching
- Usa ORB en vez de SIFT/AKAZE (más rápido)
- Verifica que estés usando OpenCV compilado con optimizaciones

**Problema:** Baja tasa de detección
```
Logo 'pecho': Found 45/100 (45%)
```
**Solución:**
- Aumenta `nfeatures`
- Ajusta thresholds: `max_reproj_error`, `min_inliers`
- Verifica calidad de los templates
- Activa fallback template matching

---

## Ejemplos de Uso Avanzado

### 1. Flujo Completo de Setup

```bash
# 1. Calibrar cámara
python -m alignpress.cli.calibrate \
  --camera 0 \
  --pattern-size 9 6 \
  --square-size-mm 25.0 \
  --output calibration/camera_0.json

# 2. Validar todos los profiles
python -m alignpress.cli.validate_profile \
  profiles/ \
  --recursive \
  --fix-common

# 3. Benchmark de performance
python -m alignpress.cli.benchmark \
  --config config/production_config.yaml \
  --dataset datasets/validation/ \
  --output benchmark_baseline.json

# 4. Verificar que cumple requisitos
python scripts/validate_performance.py benchmark_baseline.json
```

### 2. Automatización con Scripts

Crea `scripts/setup_system.sh`:

```bash
#!/bin/bash
set -e

echo "🚀 Setting up Align-Press system..."

# Calibrate
echo "📷 Calibrating camera..."
python -m alignpress.cli.calibrate \
  --camera 0 \
  --pattern-size 9 6 \
  --square-size-mm 25.0 \
  --output calibration/camera_0.json \
  --no-preview \
  --force

# Validate
echo "✓ Validating profiles..."
python -m alignpress.cli.validate_profile \
  profiles/ \
  --recursive \
  --quiet

# Benchmark
echo "⚡ Running performance benchmark..."
python -m alignpress.cli.benchmark \
  --config config/default.yaml \
  --dataset datasets/test/ \
  --samples 20 \
  --output benchmark.json \
  --quiet

echo "✅ Setup complete!"
```

### 3. CI/CD Integration

`.github/workflows/test.yml`:

```yaml
name: Test Pipeline

on: [push, pull_request]

jobs:
  validate-profiles:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Validate all profiles
        run: |
          python -m alignpress.cli.validate_profile \
            profiles/ \
            --recursive \
            --quiet

  performance-benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
      - name: Run benchmark
        run: |
          python -m alignpress.cli.benchmark \
            --config config/default.yaml \
            --dataset datasets/ci_test/ \
            --output benchmark.json \
            --quiet
      - name: Check performance thresholds
        run: |
          python scripts/check_thresholds.py \
            --results benchmark.json \
            --min-fps 10 \
            --min-detection 0.90
```

---

## Referencias

- [Documentación OpenCV Calibration](https://docs.opencv.org/4.x/dc/dbb/tutorial_py_calibration.html)
- [Pydantic Validation](https://docs.pydantic.dev/)
- [YAML Schema](https://yaml.org/spec/1.2/spec.html)

---

**Última actualización:** 2025-10-01
**Versión:** 2.0.0
