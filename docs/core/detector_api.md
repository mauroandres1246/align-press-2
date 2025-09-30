# PlanarLogoDetector API Documentation

**Módulo:** `alignpress.core.detector`
**Clase:** `PlanarLogoDetector`
**Versión:** 2.0
**Última actualización:** 30 de septiembre, 2025

---

## 📋 Índice

- [Descripción General](#descripción-general)
- [Instalación y Setup](#instalación-y-setup)
- [Métodos Públicos](#métodos-públicos)
  - [Constructor](#constructor)
  - [detect_logos()](#detect_logos)
  - [get_expected_positions_px()](#get_expected_positions_px)
  - [get_roi_bounds_px()](#get_roi_bounds_px)
- [Formato de Configuración](#formato-de-configuración)
- [Formato de Resultados](#formato-de-resultados)
- [Ejemplos de Uso](#ejemplos-de-uso)
- [Troubleshooting](#troubleshooting)
- [Performance y Optimización](#performance-y-optimización)

---

## 📖 Descripción General

`PlanarLogoDetector` es la clase principal del sistema de detección de logos en superficies planas (planchas textiles). Utiliza **ORB features** como método primario de detección con un fallback opcional a **template matching** para casos difíciles.

### Características Principales

- ✅ **Detección robusta** basada en features (ORB/AKAZE/SIFT)
- ✅ **Verificación geométrica** con RANSAC
- ✅ **Soporte para transparencias** (PNG con canal alpha)
- ✅ **Corrección de perspectiva** mediante homografía
- ✅ **Múltiples logos** en una sola detección
- ✅ **Validación exhaustiva** con Pydantic schemas
- ✅ **Métricas detalladas** (posición, ángulo, confianza)

### Algoritmo de Detección

```
1. Preprocesamiento
   ├─ Aplicar homografía (opcional)
   ├─ Convertir a escala de grises
   └─ Mejorar contraste

2. Para cada logo configurado:
   ├─ Extraer ROI centrada en posición esperada
   ├─ Detectar features ORB en ROI y template
   ├─ Matching de features (BFMatcher o FLANN)
   ├─ Filtrar matches con ratio test
   ├─ Calcular homografía con RANSAC
   ├─ Validar geometría (inliers, error de reproyección)
   ├─ Calcular posición, ángulo y error
   └─ [Opcional] Fallback a template matching si falla

3. Retornar resultados
   └─ Lista de LogoResultSchema con métricas
```

---

## 🚀 Instalación y Setup

### Instalación

```bash
pip install opencv-python numpy pydantic
```

### Import

```python
from alignpress.core.detector import PlanarLogoDetector
```

---

## 🔧 Métodos Públicos

### Constructor

```python
def __init__(self, config: Union[Dict[str, Any], DetectorConfigSchema])
```

Inicializa el detector con la configuración proporcionada.

**Parámetros:**
- `config` (dict | DetectorConfigSchema): Configuración del detector
  - Si es `dict`, se valida automáticamente con `DetectorConfigSchema`
  - Si es `DetectorConfigSchema`, se usa directamente

**Raises:**
- `ValueError`: Si la configuración es inválida
- `FileNotFoundError`: Si algún template no existe
- `ValidationError`: Si Pydantic encuentra errores de validación

**Ejemplo:**

```python
# Desde dict
config = {
    "plane": {
        "width_mm": 500.0,
        "height_mm": 600.0,
        "mm_per_px": 0.5,
        "homography": None
    },
    "logos": [
        {
            "name": "logo_pecho",
            "template_path": "templates/pecho.png",
            "position_mm": (250.0, 300.0),
            "angle_deg": 0.0,
            "roi": {
                "width_mm": 80.0,
                "height_mm": 60.0,
                "margin_factor": 1.5
            }
        }
    ],
    "thresholds": {
        "max_position_error_mm": 3.0,
        "max_angle_error_deg": 5.0,
        "min_inliers": 15,
        "max_reproj_error_px": 3.0
    },
    "feature_params": {
        "type": "ORB",
        "nfeatures": 1500,
        "scaleFactor": 1.2,
        "nlevels": 8
    }
}

detector = PlanarLogoDetector(config)
```

---

### detect_logos()

```python
def detect_logos(
    self,
    image: np.ndarray,
    homography: Optional[np.ndarray] = None
) -> List[LogoResultSchema]
```

Detecta todos los logos configurados en la imagen de entrada.

**Parámetros:**
- `image` (np.ndarray): Imagen de entrada en formato BGR (OpenCV)
- `homography` (np.ndarray, optional): Matriz de homografía 3×3 para corrección de perspectiva

**Returns:**
- `List[LogoResultSchema]`: Lista de resultados de detección, uno por cada logo configurado

**Raises:**
- `ValueError`: Si la imagen es inválida (None o vacía)

**Ejemplo:**

```python
import cv2

# Cargar imagen
image = cv2.imread("foto_plancha.jpg")

# Detectar logos
results = detector.detect_logos(image)

# Procesar resultados
for result in results:
    print(f"Logo: {result.name}")
    print(f"  Encontrado: {result.found}")
    if result.found:
        print(f"  Posición: {result.position_mm}")
        print(f"  Error: {result.error_mm:.2f}mm")
        print(f"  Ángulo: {result.angle_deg:.1f}°")
        print(f"  Confianza: {result.confidence:.2f}")
```

---

### get_expected_positions_px()

```python
def get_expected_positions_px(self) -> Dict[str, Tuple[int, int]]
```

Obtiene las posiciones esperadas de todos los logos en píxeles.

**Returns:**
- `Dict[str, Tuple[int, int]]`: Diccionario que mapea nombres de logos a posiciones (x, y) en píxeles

**Ejemplo:**

```python
positions = detector.get_expected_positions_px()
# Output: {'logo_pecho': (500, 600), 'logo_manga': (150, 200)}

for logo_name, (x, y) in positions.items():
    print(f"{logo_name}: ({x}px, {y}px)")
```

---

### get_roi_bounds_px()

```python
def get_roi_bounds_px(self, logo_name: str) -> Optional[Tuple[int, int, int, int]]
```

Obtiene los límites de la ROI de un logo en píxeles.

**Parámetros:**
- `logo_name` (str): Nombre del logo

**Returns:**
- `Tuple[int, int, int, int] | None`: Coordenadas (x1, y1, x2, y2) de la ROI, o None si el logo no existe

**Ejemplo:**

```python
roi = detector.get_roi_bounds_px("logo_pecho")
if roi:
    x1, y1, x2, y2 = roi
    print(f"ROI: ({x1}, {y1}) → ({x2}, {y2})")
    # Dibujar ROI en imagen
    cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
```

---

## ⚙️ Formato de Configuración

### Configuración Completa (YAML)

```yaml
version: 1

plane:
  width_mm: 500.0
  height_mm: 600.0
  mm_per_px: 0.5
  homography: null  # O matriz 3x3

logos:
  - name: "logo_pecho"
    template_path: "templates/pecho.png"
    position_mm: [250.0, 300.0]  # (x, y) en milímetros
    angle_deg: 0.0
    roi:
      width_mm: 80.0
      height_mm: 60.0
      margin_factor: 1.5  # Multiplica ROI para búsqueda ampliada
    has_transparency: true  # Opcional, detecta automáticamente
    transparency_method: "contour"  # O "threshold"

  - name: "logo_manga_izq"
    template_path: "templates/manga.png"
    position_mm: [100.0, 150.0]
    angle_deg: 0.0
    roi:
      width_mm: 60.0
      height_mm: 40.0
      margin_factor: 1.2

thresholds:
  max_position_error_mm: 3.0
  max_angle_error_deg: 5.0
  min_inliers: 15
  max_reproj_error_px: 3.0

feature_params:
  type: "ORB"  # ORB, AKAZE, SIFT
  nfeatures: 1500
  scaleFactor: 1.2
  nlevels: 8
  edgeThreshold: 31  # Solo ORB
  patchSize: 31      # Solo ORB

matching_params:
  algorithm: "BF"  # BF o FLANN
  normType: "HAMMING"  # HAMMING para ORB/AKAZE, L2 para SIFT
  crossCheck: true
  ratio_test_threshold: 0.75

fallback:
  enabled: false
  scales: [0.8, 0.9, 1.0, 1.1, 1.2]
  angles_deg: [-10, -5, 0, 5, 10]
  match_threshold: 0.7
```

### Configuración Mínima (JSON)

```json
{
  "plane": {
    "width_mm": 500.0,
    "height_mm": 600.0,
    "mm_per_px": 0.5
  },
  "logos": [
    {
      "name": "logo_test",
      "template_path": "template.png",
      "position_mm": [250.0, 300.0],
      "roi": {
        "width_mm": 80.0,
        "height_mm": 60.0
      }
    }
  ]
}
```

### Descripción de Campos

#### `plane`
- `width_mm`: Ancho de la plancha en milímetros
- `height_mm`: Alto de la plancha en milímetros
- `mm_per_px`: Escala (milímetros por píxel)
- `homography`: Matriz de homografía 3×3 (opcional)

#### `logos[].roi`
- `width_mm`: Ancho del logo en milímetros
- `height_mm`: Alto del logo en milímetros
- `margin_factor`: Factor multiplicador para ROI de búsqueda (1.2 = +20%)

#### `thresholds`
- `max_position_error_mm`: Error máximo de posición aceptable
- `max_angle_error_deg`: Error angular máximo aceptable
- `min_inliers`: Mínimo de inliers RANSAC requeridos
- `max_reproj_error_px`: Error de reproyección máximo

#### `feature_params`
- `type`: Tipo de detector (`ORB`, `AKAZE`, `SIFT`)
- `nfeatures`: Número máximo de features a detectar
- `scaleFactor`: Factor de escala entre niveles de pirámide
- `nlevels`: Número de niveles de la pirámide

---

## 📊 Formato de Resultados

### Estructura de `LogoResultSchema`

```python
class LogoResultSchema(BaseModel):
    name: str                          # Nombre del logo
    found: bool                        # ¿Fue detectado?
    position_mm: Optional[Tuple[float, float]]  # Posición detectada (x, y) en mm
    angle_deg: Optional[float]         # Ángulo detectado en grados
    error_mm: Optional[float]          # Error de posición en mm
    angle_error_deg: Optional[float]   # Error angular en grados
    confidence: Optional[float]        # Confianza de detección (0-1)
    inliers: Optional[int]             # Número de inliers RANSAC
    reproj_error_px: Optional[float]   # Error de reproyección en píxeles
    processing_time_ms: float          # Tiempo de procesamiento en ms
    meets_position_tolerance: bool     # ¿Cumple tolerancia de posición?
    meets_angle_tolerance: bool        # ¿Cumple tolerancia angular?
```

### Ejemplo de Resultado

```python
# Logo detectado correctamente
LogoResultSchema(
    name="logo_pecho",
    found=True,
    position_mm=(251.3, 298.7),
    angle_deg=1.2,
    error_mm=2.1,
    angle_error_deg=1.2,
    confidence=0.87,
    inliers=48,
    reproj_error_px=1.3,
    processing_time_ms=45.2,
    meets_position_tolerance=True,
    meets_angle_tolerance=True
)

# Logo no detectado
LogoResultSchema(
    name="logo_manga",
    found=False,
    position_mm=None,
    angle_deg=None,
    error_mm=None,
    angle_error_deg=None,
    confidence=None,
    inliers=None,
    reproj_error_px=None,
    processing_time_ms=23.1,
    meets_position_tolerance=False,
    meets_angle_tolerance=False
)
```

---

## 💡 Ejemplos de Uso

### Ejemplo 1: Detección Básica

```python
import cv2
from alignpress.core.detector import PlanarLogoDetector

# Configuración mínima
config = {
    "plane": {
        "width_mm": 500.0,
        "height_mm": 600.0,
        "mm_per_px": 0.5
    },
    "logos": [{
        "name": "logo_central",
        "template_path": "template.png",
        "position_mm": (250.0, 300.0),
        "roi": {
            "width_mm": 80.0,
            "height_mm": 60.0
        }
    }]
}

# Inicializar detector
detector = PlanarLogoDetector(config)

# Cargar y procesar imagen
image = cv2.imread("plancha.jpg")
results = detector.detect_logos(image)

# Mostrar resultados
for result in results:
    if result.found:
        print(f"✓ {result.name} detectado")
        print(f"  Posición: {result.position_mm}")
        print(f"  Error: {result.error_mm:.2f}mm")
    else:
        print(f"✗ {result.name} no detectado")
```

### Ejemplo 2: Múltiples Logos con Validación

```python
from pathlib import Path

# Cargar configuración desde YAML
import yaml
with open("config/detector.yaml") as f:
    config = yaml.safe_load(f)

detector = PlanarLogoDetector(config)

# Detectar logos
image = cv2.imread("plancha_completa.jpg")
results = detector.detect_logos(image)

# Validar todos los logos
all_ok = True
for result in results:
    if not result.found:
        print(f"❌ {result.name}: NO DETECTADO")
        all_ok = False
    elif not result.meets_position_tolerance:
        print(f"⚠️  {result.name}: ERROR DE POSICIÓN ({result.error_mm:.2f}mm)")
        all_ok = False
    elif not result.meets_angle_tolerance:
        print(f"⚠️  {result.name}: ERROR DE ÁNGULO ({result.angle_error_deg:.1f}°)")
        all_ok = False
    else:
        print(f"✅ {result.name}: OK")

if all_ok:
    print("\n🎉 Todos los logos correctamente alineados")
else:
    print("\n⚠️  Ajuste necesario")
```

### Ejemplo 3: Visualización de Resultados

```python
import cv2
import numpy as np

def draw_results(image, detector, results):
    """Dibuja resultados de detección en la imagen."""
    vis = image.copy()

    for result in results:
        # Obtener posición esperada
        expected_pos = detector.get_expected_positions_px()
        exp_x, exp_y = expected_pos[result.name]

        # Dibujar posición esperada (azul)
        cv2.circle(vis, (exp_x, exp_y), 5, (255, 0, 0), -1)

        if result.found:
            # Convertir posición detectada a píxeles
            det_mm_x, det_mm_y = result.position_mm
            scale = 1.0 / detector.config.plane.mm_per_px
            det_x = int(det_mm_x * scale)
            det_y = int(det_mm_y * scale)

            # Dibujar posición detectada (verde/rojo)
            color = (0, 255, 0) if result.meets_position_tolerance else (0, 0, 255)
            cv2.circle(vis, (det_x, det_y), 5, color, -1)

            # Dibujar línea de error
            cv2.line(vis, (exp_x, exp_y), (det_x, det_y), color, 2)

            # Texto con métricas
            text = f"{result.name}: {result.error_mm:.1f}mm"
            cv2.putText(vis, text, (det_x + 10, det_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # Dibujar ROI
        roi_bounds = detector.get_roi_bounds_px(result.name)
        if roi_bounds:
            x1, y1, x2, y2 = roi_bounds
            cv2.rectangle(vis, (x1, y1), (x2, y2), (128, 128, 128), 1)

    return vis

# Usar función
detector = PlanarLogoDetector(config)
image = cv2.imread("test.jpg")
results = detector.detect_logos(image)

visualization = draw_results(image, detector, results)
cv2.imwrite("results_visualization.jpg", visualization)
```

### Ejemplo 4: Con Corrección de Perspectiva

```python
# Calibrar homografía (una vez)
import numpy as np

# ... código de calibración con chessboard ...
# Resultado: matriz H de homografía

# Guardar homografía
config["plane"]["homography"] = H.tolist()

# Detectar con corrección automática
detector = PlanarLogoDetector(config)
results = detector.detect_logos(image)  # Aplica homografía internamente
```

### Ejemplo 5: Procesamiento Batch

```python
from pathlib import Path
import json

detector = PlanarLogoDetector(config)
dataset_path = Path("datasets/testing")
results_file = "batch_results.json"

all_results = []
for img_path in dataset_path.glob("*.jpg"):
    image = cv2.imread(str(img_path))
    results = detector.detect_logos(image)

    # Serializar resultados
    all_results.append({
        "image": img_path.name,
        "logos": [r.model_dump() for r in results]
    })

    print(f"Procesado: {img_path.name}")

# Guardar resultados
with open(results_file, "w") as f:
    json.dump(all_results, f, indent=2)

print(f"✅ Resultados guardados en {results_file}")
```

---

## 🐛 Troubleshooting

### Problema: "Logo no detectado" (found=False)

**Causas posibles:**
1. **Pocos features en el template**
   - Template muy pequeño o uniforme
   - Solución: Usar template más grande con más detalles

2. **Iluminación muy diferente**
   - Template capturado con iluminación distinta
   - Solución: Mejorar iluminación o capturar nuevo template

3. **ROI muy pequeña**
   - Logo está fuera de la ROI de búsqueda
   - Solución: Aumentar `margin_factor` en config

4. **Logo muy rotado o escalado**
   - Transformación excede capacidad de ORB
   - Solución: Activar fallback template matching

**Diagnóstico:**
```python
# Verificar número de features en template
detector = PlanarLogoDetector(config)
for logo_name, kp in detector._template_keypoints.items():
    print(f"{logo_name}: {len(kp)} features")
    if len(kp) < 20:
        print(f"  ⚠️  Muy pocas features! Recomendado: >50")
```

---

### Problema: "Error de posición muy alto"

**Causas posibles:**
1. **Escala (mm_per_px) incorrecta**
   - Calibración errónea
   - Solución: Re-calibrar con chessboard

2. **Template mal recortado**
   - Demasiado margen alrededor del logo
   - Solución: Recortar template ajustadamente

3. **Homografía desactualizada**
   - Cámara movida desde calibración
   - Solución: Re-calibrar

**Diagnóstico:**
```python
# Verificar escala con objeto de tamaño conocido
positions = detector.get_expected_positions_px()
print(f"Posición esperada: {positions}")

# Comparar con posición visual en imagen
```

---

### Problema: "FPS muy bajo / Lento"

**Causas posibles:**
1. **Demasiados features**
   - `nfeatures` muy alto
   - Solución: Reducir a 1000-1500

2. **Imagen de alta resolución**
   - Imagen >2MP innecesaria
   - Solución: Redimensionar a 1280×720

3. **ROIs muy grandes**
   - `margin_factor` demasiado alto
   - Solución: Reducir a 1.2-1.5

4. **Fallback activado**
   - Template matching es más lento
   - Solución: Desactivar si no es necesario

**Benchmark:**
```python
import time

image = cv2.imread("test.jpg")
detector = PlanarLogoDetector(config)

start = time.time()
results = detector.detect_logos(image)
total_time = (time.time() - start) * 1000

print(f"Tiempo total: {total_time:.1f}ms")
for r in results:
    print(f"  {r.name}: {r.processing_time_ms:.1f}ms")
```

---

### Problema: "Muchos falsos positivos"

**Causas posibles:**
1. **min_inliers muy bajo**
   - Acepta matches de baja calidad
   - Solución: Aumentar a 20-30

2. **max_reproj_error_px muy alto**
   - Permite geometría imprecisa
   - Solución: Reducir a 2.0-3.0

3. **Template genérico**
   - Logo similar a patrones del fondo
   - Solución: Usar template más distintivo

**Ajuste de umbrales:**
```yaml
thresholds:
  max_position_error_mm: 2.0  # Más estricto
  max_angle_error_deg: 3.0    # Más estricto
  min_inliers: 25             # Más alto
  max_reproj_error_px: 2.0    # Más bajo
```

---

### Problema: "Template con transparencia no funciona"

**Verificación:**
```python
from alignpress.utils.image_utils import has_transparency, get_image_info

template_path = "template.png"
info = get_image_info(template_path)
print(f"Tiene alpha: {info['has_alpha']}")
print(f"Shape: {info['shape']}")

# Si no tiene alpha pero debería
# Solución: Procesar con background removal
```

---

## ⚡ Performance y Optimización

### Benchmarks Típicos

**Hardware de referencia:** Raspberry Pi 4 (4GB RAM)

| Configuración | FPS | Tiempo (ms) | Notas |
|---------------|-----|-------------|-------|
| 1 logo, ORB 1500 | 25-30 | ~35ms | Óptimo |
| 2 logos, ORB 1500 | 15-20 | ~60ms | Aceptable |
| 3 logos, ORB 2000 | 10-12 | ~90ms | Límite |
| 1 logo + fallback | 8-10 | ~120ms | Lento |

### Optimizaciones Recomendadas

1. **Resolución de imagen**
   ```python
   # Redimensionar si es muy grande
   if image.shape[0] > 1080:
       scale = 1080 / image.shape[0]
       image = cv2.resize(image, None, fx=scale, fy=scale)
   ```

2. **Número de features**
   ```yaml
   feature_params:
     nfeatures: 1000  # Reducir de 1500
   ```

3. **ROI ajustada**
   ```yaml
   roi:
     margin_factor: 1.2  # Reducir de 1.5
   ```

4. **Deshabilitar fallback**
   ```yaml
   fallback:
     enabled: false
   ```

5. **Usar ORB en lugar de SIFT**
   ```yaml
   feature_params:
     type: "ORB"  # Más rápido que SIFT
   ```

---

## 📚 Referencias

- **OpenCV ORB:** https://docs.opencv.org/4.x/d1/d89/tutorial_py_orb.html
- **RANSAC:** https://en.wikipedia.org/wiki/Random_sample_consensus
- **Pydantic:** https://docs.pydantic.dev/

---

## 🔄 Changelog

### v2.0 (2025-09-30)
- ✨ Soporte para transparencias (PNG con alpha)
- ✨ Validación exhaustiva con Pydantic v2
- ✨ Múltiples tipos de features (ORB/AKAZE/SIFT)
- 🐛 Corrección de bugs en cálculo de ángulos
- 📝 Documentación completa de API

### v1.0 (2025-09-28)
- 🎉 Primera versión refactorizada
- ✅ Detección ORB + RANSAC
- ✅ Template matching fallback
- ✅ Métricas detalladas

---

**Documento generado automáticamente** | Align-Press v2.0
Para reportar issues: [GitHub Issues](https://github.com/your-repo/align-press-v2/issues)
