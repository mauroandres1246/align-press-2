# Align-Press v2 - Testing Tools

Herramientas completas para probar el sistema de detección de logos con tu plancha real de 50cm x 60cm.

## 🎯 Flujo de Testing Completo

### Para tu setup específico (50cm x 60cm):

```bash
# Opción 1: Script rápido simplificado
python tools/testing/quick_test_your_platen.py

# Opción 2: Workflow completo automatizado
python tools/testing/complete_testing_workflow.py \
  --calibration-image datasets/calibration/platen_with_chessboard.jpg \
  --logo-image datasets/real_templates/logo_source.jpg \
  --pattern-size 9 6 \
  --square-size-mm 25.0 \
  --logo-position-mm 250 300
```

## 📁 Preparación de Imágenes

### 1. Imagen de Calibración
- **Archivo**: `datasets/calibration/platen_with_chessboard.jpg`
- **Contenido**: Tu plancha de 50x60cm con patrón de ajedrez 9x6
- **Patrón**: 9x6 esquinas internas, cuadros de 25mm
- **Calidad**: Imagen enfocada, iluminación uniforme, ángulo perpendicular

### 2. Imagen del Logo
- **Archivo**: `datasets/real_templates/logo_source.jpg`
- **Contenido**: Imagen clara de tu logo para extraer template
- **Calidad**: Alto contraste, bordes nítidos, mínimo ruido de fondo

### 3. Imágenes de Prueba
Organizar en `datasets/testing/`:
```
testing/
├── correct/          # Logo en posición correcta
├── incorrect/        # Logo fuera de posición
├── no_logo/         # Sin logo (test falsos positivos)
└── variations/      # Diferentes condiciones
```

## 🛠️ Herramientas Individuales

### Setup del Entorno
```bash
python tools/testing/setup_testing_environment.py
```
- Crea estructura de directorios
- Genera documentación
- Valida prerequisites

### Calibración desde Imagen
```bash
python tools/testing/calibrate_from_image.py \
  --image calibration/platen_50x60/pattern_image.jpg \
  --pattern-size 9 6 \
  --square-size-mm 25 \
  --output datasets/calibration/platen_50x60/
```

### Extracción de Template
```bash
# Selección interactiva de ROI
python tools/testing/extract_template.py \
  --input datasets/real_templates/logo_source.jpg \
  --output datasets/real_templates/main_logo.png \
  --interactive \
  --enhance \
  --generate-variations

# ROI manual (coordenadas x,y,ancho,alto)
python tools/testing/extract_template.py \
  --input datasets/real_templates/logo_source.jpg \
  --output datasets/real_templates/main_logo.png \
  --roi 100 50 200 150 \
  --enhance \
  --generate-variations
```

### Evaluación Completa
```bash
python tools/testing/run_full_evaluation.py \
  --config config/platen_50x60_detector.yaml \
  --dataset datasets/testing/ \
  --calibration calibration/platen_50x60/calibration.json \
  --output results/evaluation_results.json \
  --html-report results/evaluation_report.html
```

## 📊 Resultados y Reportes

### Archivos Generados
- **`results/evaluation_report.html`**: Reporte visual completo
- **`results/evaluation_results.json`**: Datos detallados en JSON
- **`calibration/platen_50x60/calibration_debug.jpg`**: Debug de calibración
- **`results/workflow_summary.json`**: Resumen del workflow completo

### Métricas Evaluadas
- **Precisión de detección**: TP, FP, FN por categoría
- **Exactitud de posicionamiento**: Desviación en mm
- **Rendimiento**: Tiempo de procesamiento, FPS estimado
- **Robustez**: Variaciones de iluminación, ángulo, escala

## 🎯 Configuración para tu Plancha

### Parámetros Específicos (50cm x 60cm)
```yaml
# config/platen_50x60_detector.yaml
plane:
  width_mm: 500.0    # 50 cm
  height_mm: 600.0   # 60 cm
  mm_per_px: 0.4     # Se actualiza con calibración

logos:
  - name: "main_logo"
    position_mm: [250.0, 300.0]  # Centro de plancha
    roi:
      width_mm: 80.0
      height_mm: 60.0
      margin_factor: 1.5

thresholds:
  position_tolerance_mm: 5.0    # Tolerancia inicial
  angle_tolerance_deg: 8.0
  min_inliers: 12
  max_reproj_error: 4.0
```

## 🐛 Troubleshooting

### Problemas Comunes

#### "Chessboard pattern not detected"
```bash
# Verificar patrón de calibración
python tools/testing/calibrate_from_image.py --help

# Problemas típicos:
# - Imagen desenfocada
# - Patrón no es 9x6 esquinas internas
# - Cuadros no son exactamente 25mm
# - Iluminación con sombras
```

#### "Template extraction failed"
```bash
# Verificar calidad de imagen del logo
python tools/testing/extract_template.py \
  --input datasets/real_templates/logo_source.jpg \
  --output test_template.png \
  --interactive

# Problemas típicos:
# - Logo con poco contraste
# - Imagen muy pequeña
# - ROI mal seleccionado
```

#### "Low detection rate"
```bash
# Ajustar configuración del detector
# Editar config/platen_50x60_detector.yaml:

# Para logos con pocos features:
features:
  nfeatures: 2000        # Aumentar features

# Para condiciones variables:
thresholds:
  position_tolerance_mm: 8.0  # Más tolerante
  min_inliers: 8             # Menos estricto

fallback:
  scales: [0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4]  # Más escalas
  match_threshold: 0.6       # Más permisivo
```

### Validación de Calidad

#### Calibración
- **Error de reproyección**: < 2.0 píxeles (excelente), < 3.0 (bueno)
- **Factor de escala**: 0.2-0.8 mm/px (rango típico)
- **Detección de esquinas**: 100% (perfecto)

#### Template
- **Features ORB**: >50 (excelente), >20 (bueno)
- **Sharpness**: >100 (excelente), >50 (bueno)
- **Contraste**: >50 (excelente), >30 (bueno)
- **Tamaño**: >50px en dimensión menor

#### Detección
- **Tasa de detección**: >90% (excelente), >70% (bueno)
- **Precisión posición**: <3mm desviación (excelente), <5mm (bueno)
- **Velocidad**: >20 FPS (excelente), >10 FPS (bueno)

## 📋 Checklist de Testing

### Pre-Testing
- [ ] Entorno virtual activado
- [ ] Dependencias instaladas (`pip install -e ".[dev]"`)
- [ ] Estructura de directorios creada
- [ ] Patrón de ajedrez impreso (9x6, 25mm)

### Calibración
- [ ] Foto de plancha con patrón tomada
- [ ] Imagen enfocada y bien iluminada
- [ ] Patrón detectado correctamente
- [ ] Error de reproyección < 2.0px
- [ ] Factor mm_per_px razonable (0.2-0.8)

### Template
- [ ] Imagen del logo capturada
- [ ] ROI seleccionado correctamente
- [ ] Template con buen contraste
- [ ] Variaciones generadas
- [ ] Análisis de calidad > 50 features

### Testing
- [ ] Imágenes de prueba organizadas por categoría
- [ ] Al menos 5 imágenes por categoría
- [ ] Condiciones variadas incluidas
- [ ] Metadatos de expectativas configurados

### Evaluación
- [ ] Configuración actualizada con calibración
- [ ] Evaluación ejecutada sin errores
- [ ] Tasa de detección > 70%
- [ ] Reporte HTML generado
- [ ] Resultados JSON guardados

### Optimización
- [ ] Parámetros ajustados según resultados
- [ ] Re-evaluación después de ajustes
- [ ] Documentación de configuración final
- [ ] Backup de configuración funcional

## 🎯 Ejemplo Completo

Para tu caso específico con imágenes de plancha de 50x60cm:

```bash
# 1. Setup inicial
python tools/testing/setup_testing_environment.py

# 2. Colocar tus imágenes:
# - datasets/calibration/platen_with_chessboard.jpg (tu imagen #1)
# - datasets/real_templates/logo_source.jpg (tu imagen #2)

# 3. Ejecutar workflow completo
python tools/testing/quick_test_your_platen.py

# 4. Revisar resultados
# - results/evaluation_report.html (abrir en browser)
# - calibration/platen_50x60/calibration_debug.jpg (verificar calibración)

# 5. Iterar y optimizar
# - Ajustar config/platen_50x60_detector.yaml según resultados
# - Añadir más imágenes de prueba
# - Re-ejecutar evaluación
```

¡Tu sistema estará listo para detectar logos en la plancha de 50x60cm! 🎉