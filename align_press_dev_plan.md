# Align-Press v2 - Plan de Desarrollo y Documentación de Tareas

**Proyecto:** Sistema de Detección y Alineación de Logos para Prensas Textiles  
**Objetivo:** Pipeline robusto OpenCV + ORB para Raspberry Pi con UI operador/técnico  
**Estrategia:** Desarrollo "dentro→fuera" (Core → CLI → UI)  
**Fecha de inicio:** 28 de septiembre, 2025  
**Última actualización:** 28 de septiembre, 2025

---

## 📊 Estado General del Proyecto

```
[████████░░░░░░░░░░░░] 35% Completado

Fase 0: Refactoring del Detector    [██████████] 100% ✅
Fase 1: CLI Tools                    [████░░░░░░]  40% 🔄
Fase 2: Core Business Logic          [░░░░░░░░░░]   0% ⏸️
Fase 3: UI Operador (MVP)            [░░░░░░░░░░]   0% ⏸️
Fase 4: UI Técnico                   [░░░░░░░░░░]   0% ⏸️
Fase 5: Deployment Raspberry Pi      [░░░░░░░░░░]   0% ⏸️
Fase 6: Hardware Expansion           [░░░░░░░░░░]   0% 📅
```

**Leyenda:**
- ✅ Completado
- 🔄 En progreso
- ⏸️ Pendiente (próximo)
- 📅 Planificado (futuro)
- ❌ Bloqueado

---

## 🎯 Principios de Diseño

### Arquitectura
1. **Separación de responsabilidades:** Core (sin UI) → CLI → UI
2. **Testeable:** Cada módulo tiene tests unitarios independientes
3. **Configurable:** YAML para humanos, JSON para máquinas
4. **Escalable:** Preparado para 2 cámaras + Arduino sin refactors mayores
5. **Portable:** Desktop (dev) → Raspberry Pi (prod) sin cambios de código

### Convenciones de Código
- **Estilo:** PEP 8, type hints obligatorios
- **Docstrings:** Google style
- **Validación:** Pydantic para schemas
- **Logging:** structlog (JSON estructurado)
- **Testing:** pytest + pytest-qt, cobertura >80%

### Gestión de Configuración
- **Versionado:** Todos los profiles tienen campo `version: N`
- **Migraciones:** Script `tools/profile_migrator.py` para cambios de schema
- **Validación:** Schemas JSON para validación estricta pre-carga
- **Defaults:** `config/app.yaml` tiene valores sensatos para Pi

---

## 📁 Estructura de Archivos (Referencia)

```
align-press-v2/
├── README.md
├── requirements.txt
├── pyproject.toml
│
├── config/
│   ├── app.yaml              # ✅ Configuración principal
│   ├── logging.yaml          # ⏸️ Config de structlog
│   └── schemas/              # ⏸️ JSON schemas para validación
│       ├── platen.schema.json
│       ├── style.schema.json
│       └── variant.schema.json
│
├── profiles/
│   ├── planchas/             # ⏸️ Perfiles de planchas
│   ├── estilos/              # ⏸️ Definiciones de estilos
│   └── variantes/            # 📅 Offsets por talla (opcional)
│
├── templates/                # ✅ Imágenes de referencia de logos
├── calibration/              # ⏸️ Homografías por cámara
├── datasets/                 # 🔄 Imágenes para testing
├── logs/                     # ⏸️ Logs y job cards
│
├── alignpress/               # Código fuente
│   ├── core/                 # 🔄 Lógica de negocio
│   ├── ui/                   # ⏸️ Interfaz PySide6
│   ├── cli/                  # 🔄 Herramientas CLI
│   ├── utils/                # 🔄 Utilidades compartidas
│   └── hardware/             # 📅 Abstracciones hardware
│
├── tests/                    # 🔄 Testing automatizado
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
└── tools/                    # ⏸️ Scripts auxiliares
```

---

# 🗂️ FASE 0: REFACTORING DEL DETECTOR

**Objetivo:** Modularizar el detector existente (`logo_planar_detector.py`) en componentes testeables y reutilizables.

**Prioridad:** 🔥 CRÍTICA (bloqueante para todo lo demás)  
**Estado:** ✅ **COMPLETADO** (2025-09-28)  
**Duración estimada:** 1-2 días  
**Duración real:** —

---

## Checklist de Tareas

### T0.1: Crear estructura de módulos core ✅
**Responsable:** Developer  
**Estado:** ✅ Completado  
**Archivos creados:**
- [x] `alignpress/core/__init__.py`
- [x] `alignpress/core/detector.py`
- [x] `alignpress/utils/__init__.py`
- [x] `alignpress/utils/geometry.py`
- [x] `alignpress/utils/image_utils.py`

**Notas:**
- Se movieron las funciones geométricas (`angle_deg`, `l2`, `polygon_center`) a `geometry.py`
- Se centralizaron utilidades de imagen (conversiones, clipping) en `image_utils.py`

---

### T0.2: Refactorizar `PlanarLogoDetector` ✅
**Responsable:** Developer  
**Estado:** ✅ Completado  
**Archivo:** `alignpress/core/detector.py`

**Cambios realizados:**
- [x] Separar clases de configuración (`PlaneConfig`, `LogoSpec`, etc.) en dataclasses
- [x] Mover lógica de carga de templates a método privado `_load_template()`
- [x] Extraer matching de logos a método `_match_logo()`
- [x] Extraer fallback template matching a `_fallback_template()`
- [x] Añadir type hints completos
- [x] Documentar métodos públicos con docstrings

**Decisiones de diseño:**
- Se mantiene la estrategia ORB + RANSAC como método principal
- Fallback de template matching es opcional (configurable)
- La clase es stateless excepto por templates cargados (thread-safe)

---

### T0.3: Crear módulo de utilidades geométricas ✅
**Responsable:** Developer  
**Estado:** ✅ Completado  
**Archivo:** `alignpress/utils/geometry.py`

**Funciones implementadas:**
- [x] `angle_deg(p0, p1)`: Ángulo entre dos puntos
- [x] `l2(a, b)`: Distancia euclidiana
- [x] `polygon_center(poly)`: Centro de polígono
- [x] `angle_diff_circular(a, b)`: Diferencia angular mínima (circular)
- [x] `clamp(val, lo, hi)`: Clipping de valores

**Tests:** `tests/unit/test_geometry.py` pendiente (T0.6)

---

### T0.4: Crear módulo de utilidades de imagen ✅
**Responsable:** Developer  
**Estado:** ✅ Completado  
**Archivo:** `alignpress/utils/image_utils.py`

**Funciones implementadas:**
- [x] `mm_to_px(x_mm, y_mm, scale)`: Conversión mm → px
- [x] `px_to_mm(x_px, y_px, scale)`: Conversión px → mm
- [x] `extract_roi(img, center, size)`: Extracción de ROI con clipping
- [x] `warp_perspective(img, H, size)`: Wrapper de cv2.warpPerspective con optimizaciones

**Tests:** `tests/unit/test_image_utils.py` pendiente (T0.6)

---

### T0.5: Separar configuración en schemas Pydantic ⏸️
**Responsable:** Developer  
**Estado:** ⏸️ **PENDIENTE** (próxima tarea)  
**Archivo:** `alignpress/core/schemas.py`

**Tareas:**
- [ ] Crear `PlaneConfigSchema` con validación de dimensiones positivas
- [ ] Crear `LogoSpecSchema` con validación de paths de templates
- [ ] Crear `ThresholdsSchema` con rangos válidos
- [ ] Crear `FeatureParamsSchema` validando tipo ORB/AKAZE
- [ ] Crear `FallbackParamsSchema` con rangos de scales/angles
- [ ] Añadir validadores custom (ej: verificar que template existe)

**Criterios de aceptación:**
- Pydantic debe rechazar configs inválidas con mensajes claros
- Schemas deben tener valores default sensatos
- Documentación inline de cada campo

---

### T0.6: Crear tests unitarios del detector ⏸️
**Responsable:** Developer  
**Estado:** ⏸️ **PENDIENTE**  
**Archivos:** `tests/unit/test_detector.py`, `tests/unit/test_geometry.py`

**Tests a implementar:**

#### `test_detector.py`
- [ ] `test_detector_initialization`: Verifica carga correcta de config y templates
- [ ] `test_mm_to_px_conversion`: Prueba conversiones con diferentes escalas
- [ ] `test_warp_to_plane`: Verifica rectificación correcta
- [ ] `test_detect_perfect_alignment`: Logo en posición exacta → error ~0mm
- [ ] `test_detect_with_offset`: Logo desviado 5mm → error ~5mm ±0.5mm
- [ ] `test_detect_with_rotation`: Logo rotado 10° → error angular ~10° ±1°
- [ ] `test_detect_no_logo`: Imagen sin logo → `found: false`
- [ ] `test_fallback_template_match`: Fuerza fallback y verifica detección
- [ ] `test_roi_extraction`: ROI centrada correctamente alrededor de posición esperada

#### `test_geometry.py`
- [ ] `test_angle_deg_quadrants`: Verifica ángulos en 4 cuadrantes
- [ ] `test_l2_distance`: Distancia euclidiana casos conocidos
- [ ] `test_polygon_center`: Centro de cuadrado, triángulo, pentágono
- [ ] `test_angle_diff_circular`: Diferencia 350° - 10° = 20° (no 340°)

**Fixtures necesarios:**
- [ ] `mock_config.json` con plancha 300×200mm, 2 logos
- [ ] `mock_template_A.png` (logo simple con features)
- [ ] `mock_plane_perfect.jpg` (logo en posición exacta)
- [ ] `mock_plane_offset.jpg` (logo desviado 5mm, 3°)

---

### T0.7: Documentar API del detector ⏸️
**Responsable:** Developer  
**Estado:** ⏸️ **PENDIENTE**  
**Archivo:** `docs/core/detector_api.md`

**Contenido:**
- [ ] Descripción general del `PlanarLogoDetector`
- [ ] Explicación de cada método público
- [ ] Ejemplos de uso (código Python)
- [ ] Formato de entrada (config JSON/YAML)
- [ ] Formato de salida (estructura de `results`)
- [ ] Troubleshooting común (pocos inliers, fallback, etc.)

---

## Notas de la Fase 0

**Decisiones técnicas:**
- Se mantiene OpenCV como única dependencia de visión (sin scikit-image)
- Los tests usan imágenes sintéticas generadas con `cv2.warpPerspective` para evitar dependencias externas
- El detector es agnóstico a la fuente de imagen (archivo/cámara se maneja fuera)

**Deuda técnica identificada:**
- Actualmente no hay caché de templates (se recargan en cada init)
- El detector carga todos los templates en memoria (puede ser problemático con >20 logos)

**Próximos pasos después de T0.7:**
- Pasar a **Fase 1: CLI Tools** (prioridad: `cli/test_detector.py`)

---

---

# 🛠️ FASE 1: CLI TOOLS

**Objetivo:** Crear herramientas de línea de comandos para testing del detector, calibración y validación de configuraciones SIN necesidad de UI.

**Prioridad:** 🔥 ALTA (necesarias para validar el detector antes de UI)  
**Estado:** 🔄 **EN PROGRESO** (40% completado)  
**Duración estimada:** 2-3 días  
**Duración real:** —

---

## Checklist de Tareas

### T1.1: Crear CLI para testing del detector 🔄
**Responsable:** Developer  
**Estado:** 🔄 **EN PROGRESO** (70%)  
**Archivo:** `alignpress/cli/test_detector.py`

**Funcionalidad:**
```bash
# Test con imagen estática
python -m alignpress.cli.test_detector \
  --config config/example.yaml \
  --image datasets/test_001.jpg \
  --save-debug output/debug_001.jpg \
  --verbose

# Test con cámara en vivo
python -m alignpress.cli.test_detector \
  --config config/example.yaml \
  --camera 0 \
  --show \
  --fps 30
```

**Tareas:**
- [x] Parser de argumentos con `argparse`
- [x] Carga de configuración desde YAML/JSON
- [x] Modo imagen única con guardado de debug
- [ ] Modo cámara en vivo con loop
- [ ] Output estructurado (JSON + tabla ASCII para consola)
- [ ] Manejo de errores (archivo no existe, cámara no disponible, etc.)

**Output esperado (modo verbose):**
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
[INFO] Guardado debug en output/debug_001.jpg
[SUMMARY] 2/2 logos detectados, 1/2 OK, 1/2 requieren ajuste
```

**Criterios de aceptación:**
- CLI funciona con imágenes estáticas y muestra métricas
- Modo cámara procesa frames en vivo y actualiza consola
- Imagen de debug muestra overlays (posición esperada, detectada, error)

---

### T1.2: Crear CLI para calibración de cámara ⏸️
**Responsable:** Developer  
**Estado:** ⏸️ **PENDIENTE**  
**Archivo:** `alignpress/cli/calibrate.py`

**Funcionalidad:**
```bash
# Calibración interactiva con chessboard
python -m alignpress.cli.calibrate \
  --camera 0 \
  --pattern-size 9x6 \
  --square-size-mm 25.0 \
  --output calibration/camera_0/homography.json \
  --preview
```

**Tareas:**
- [ ] Captura de imagen desde cámara con preview
- [ ] Detección de chessboard con `cv2.findChessboardCorners`
- [ ] Cálculo de homografía imagen→plano
- [ ] Cálculo de escala (mm/px) desde dimensiones conocidas del patrón
- [ ] Validación de calidad (error de reproyección, simetría)
- [ ] Guardado en JSON con metadata (timestamp, dimensiones, etc.)

**Estructura del JSON de salida:**
```json
{
  "version": 1,
  "timestamp": "2025-09-28T14:30:00Z",
  "camera_id": 0,
  "pattern": {
    "type": "chessboard",
    "size": [9, 6],
    "square_size_mm": 25.0
  },
  "homography": [[1.0, 0.0, 0.0], ...],
  "plane_config": {
    "mm_per_px": 0.48,
    "width_px": 600,
    "height_px": 400
  },
  "quality_metrics": {
    "reproj_error_px": 0.8,
    "corners_detected": 54,
    "corners_expected": 54
  }
}
```

**Criterios de aceptación:**
- Detecta correctamente chessboard en condiciones de iluminación razonables
- Rechaza calibraciones con error >2px o <80% de esquinas detectadas
- JSON generado es compatible con el detector (T0.2)

---

### T1.3: Crear CLI para validación de profiles ⏸️
**Responsable:** Developer  
**Estado:** ⏸️ **PENDIENTE**  
**Archivo:** `alignpress/cli/validate_profile.py`

**Funcionalidad:**
```bash
# Validar un profile individual
python -m alignpress.cli.validate_profile \
  profiles/estilos/polo_basico_v2.yaml \
  --schema schemas/style.schema.json

# Validar todos los profiles de un directorio
python -m alignpress.cli.validate_profile \
  profiles/estilos/ \
  --recursive \
  --fix-common  # Intenta auto-corregir errores comunes
```

**Tareas:**
- [ ] Carga y parseo de YAML/JSON
- [ ] Validación contra JSON schema (si se provee)
- [ ] Validación semántica (ej: verificar que templates existen)
- [ ] Verificación de dimensiones (posiciones dentro de plancha, ROIs válidos)
- [ ] Detección de problemas comunes (rutas relativas rotas, versiones obsoletas)
- [ ] Modo `--fix-common` para correcciones automáticas

**Criterios de aceptación:**
- Valida correctamente profiles bien formados
- Detecta errores comunes (templates faltantes, dimensiones fuera de rango)
- Modo `--fix-common` puede corregir paths relativos rotos

---

### T1.4: Crear CLI para benchmark de performance ⏸️
**Responsable:** Developer  
**Estado:** ⏸️ **PENDIENTE**  
**Archivo:** `alignpress/cli/benchmark.py`

**Funcionalidad:**
```bash
# Benchmark sobre dataset de imágenes
python -m alignpress.cli.benchmark \
  --config config/example.yaml \
  --dataset datasets/synthetic/ \
  --samples 100 \
  --output benchmark_results.json
```

**Tareas:**
- [ ] Procesamiento de N imágenes del dataset
- [ ] Medición de tiempos (total, por logo, por etapa)
- [ ] Medición de uso de memoria (pico, promedio)
- [ ] Cálculo de FPS promedio
- [ ] Generación de reporte (JSON + tabla ASCII)
- [ ] Comparación con baseline (si existe benchmark previo)

**Criterios de aceptación:**
- Procesa dataset completo sin errores
- Tiempos medidos son consistentes (±5% entre runs)
- Identifica cuellos de botella (etapas lentas)

---

### T1.5: Documentar uso de CLI tools ⏸️
**Responsable:** Developer  
**Estado:** ⏸️ **PENDIENTE**  
**Archivo:** `docs/cli/README.md`

**Contenido:**
- [ ] Instalación de dependencias
- [ ] Guía rápida de uso de cada herramienta
- [ ] Ejemplos de comandos comunes
- [ ] Troubleshooting (cámara no detectada, etc.)
- [ ] Interpretación de métricas (qué es un buen/mal resultado)

---

## Notas de la Fase 1

**Decisiones técnicas:**
- CLI usa `rich` para output colorido y tablas (opcional, fallback a print())
- Todos los CLIs aceptan `--verbose` y `--quiet` para control de output
- Los CLIs son scripts ejecutables pero también importables como módulos (testing)

**Deuda técnica identificada:**
- No hay logging estructurado aún (pendiente Fase 2)
- Benchmark no mide impacto de fallback template matching por separado

**Próximos pasos después de T1.5:**
- Pasar a **Fase 2: Core Business Logic** (prioridad: `core/profile.py`)

---

---

# 📦 FASE 2: CORE BUSINESS LOGIC

**Objetivo:** Implementar la lógica de negocio que combina planchas, estilos y variantes, genera job cards, y gestiona calibraciones.

**Prioridad:** 🔥 ALTA (necesario antes de UI)  
**Estado:** ⏸️ **PENDIENTE**  
**Duración estimada:** 3-4 días  
**Duración real:** —

---

## Checklist de Tareas

### T2.1: Crear módulo de gestión de profiles ⏸️
**Responsable:** Developer  
**Estado:** ⏸️ **PENDIENTE**  
**Archivo:** `alignpress/core/profile.py`

**Clases a implementar:**

#### `PlatenProfile`
```python
@dataclass
class PlatenProfile:
    name: str
    version: int
    dimensions_mm: Tuple[float, float]  # (width, height)
    calibration: CalibrationData
    metadata: Dict[str, Any]
    
    @classmethod
    def from_file(cls, path: Path) -> "PlatenProfile":
        """Carga desde YAML/JSON con validación"""
        ...
    
    def is_calibration_valid(self, max_age_days: int = 30) -> bool:
        """Verifica si la calibración no está vencida"""
        ...
```

**Tareas:**
- [ ] Implementar clases con Pydantic para validación
- [ ] Crear `ProfileLoader` con caché
- [ ] Implementar validación cruzada (posiciones dentro de plancha, etc.)
- [ ] Tests unitarios con fixtures

**Criterios de aceptación:**
- Carga correctamente profiles válidos
- Rechaza profiles con errores de schema
- Aplica correctamente offsets de variantes

---

### T2.2: Crear módulo de composición ⏸️
**Responsable:** Developer  
**Estado:** ⏸️ **PENDIENTE**  
**Archivo:** `alignpress/core/composition.py`

**Clase principal:**

#### `Composition`
```python
class Composition:
    def __init__(
        self,
        platen: PlatenProfile,
        style: StyleProfile,
        variant: Optional[SizeVariant] = None
    ):
        self.platen = platen
        self.style = style
        self.variant = variant
        self._validate()
    
    def to_detector_config(self) -> Dict[str, Any]:
        """Genera config para PlanarLogoDetector"""
        ...
    
    def get_expected_positions(self) -> Dict[str, Tuple[float, float]]:
        """Devuelve posiciones esperadas (mm) por logo"""
        ...
```

**Tareas:**
- [ ] Implementar `Composition` con validación completa
- [ ] Método `to_detector_config()` que genera JSON válido
- [ ] Visualización de composición (opcional: dibuja layout en imagen)
- [ ] Tests con combinaciones válidas/inválidas

**Criterios de aceptación:**
- Genera configs que funcionan con `PlanarLogoDetector` sin modificaciones
- Detecta logos fuera de plancha o ROIs solapados
- Aplica correctamente offsets de variantes

---

### T2.3: Crear módulo de job cards ⏸️
**Responsable:** Developer  
**Estado:** ⏸️ **PENDIENTE**  
**Archivo:** `alignpress/core/job_card.py`

**Clase principal:**

#### `JobCard`
```python
@dataclass
class JobCard:
    job_id: str
    timestamp_start: datetime
    timestamp_end: Optional[datetime]
    composition: Composition
    results: List[LogoResult]
    snapshot_path: Optional[Path]
    operator_notes: str
    
    def add_result(self, logo_name: str, detection: Dict[str, Any]):
        """Añade resultado de detección de un logo"""
        ...
    
    def finalize(self):
        """Marca job como completado"""
        self.timestamp_end = datetime.now()
    
    def to_json(self) -> str:
        """Serializa a JSON"""
        ...
```

**Tareas:**
- [ ] Implementar `JobCard` con serialización JSON
- [ ] Método `save()` que maneja paths relativos correctamente
- [ ] Generación de snapshot con overlays
- [ ] Tests con job exitosos/fallidos

**Criterios de aceptación:**
- JSON generado es válido y deserializable
- Snapshots se guardan correctamente con timestamp
- `is_successful` refleja correctamente estado del job

---

### T2.4: Crear módulo de gestión de calibraciones ⏸️
**Responsable:** Developer  
**Estado:** ⏸️ **PENDIENTE**  
**Archivo:** `alignpress/core/calibration.py`

**Clases principales:**

#### `CalibrationData`
```python
@dataclass
class CalibrationData:
    homography: np.ndarray  # 3×3
    mm_per_px: float
    timestamp: datetime
    pattern_info: Dict[str, Any]
    quality_metrics: Dict[str, float]
    
    @property
    def age_days(self) -> int:
        return (datetime.now() - self.timestamp).days
    
    def is_expired(self, max_age_days: int = 30) -> bool:
        return self.age_days > max_age_days
```

**Tareas:**
- [ ] Implementar `CalibrationData` con validación
- [ ] Implementar `CalibrationManager` con caché
- [ ] Sistema de notificaciones de vencimiento
- [ ] Tests con calibraciones válidas/vencidas

**Criterios de aceptación:**
- Detecta correctamente calibraciones vencidas
- Caché evita recargas innecesarias
- JSON de calibración es compatible con CLI de calibración (T1.2)

---

### T2.5: Crear módulo de configuración centralizada ⏸️
**Responsable:** Developer  
**Estado:** ⏸️ **PENDIENTE**  
**Archivo:** `alignpress/utils/config_loader.py`

**Estructura de `config/app.yaml`:**
```yaml
version: 1
language: "es"

paths:
  profiles: "profiles"
  templates: "templates"
  calibration: "calibration"
  datasets: "datasets"
  logs: "logs"

ui:
  theme: "light"  # light|dark
  technical_pin: "2468"
  fullscreen: false
  fps_target: 30

detector:
  feature_type: "ORB"
  nfeatures: 1500
  fallback_enabled: true

calibration:
  max_age_days: 30
  warning_days: 7

logging:
  level: "INFO"
  format: "json"
  output: "logs/sessions/"
```

**Tareas:**
- [ ] Implementar `AppConfig` con Pydantic
- [ ] Validación de paths (directorios existen, permisos de escritura)
- [ ] Generación de config default si no existe
- [ ] Tests con configs válidas/inválidas

**Criterios de aceptación:**
- Carga correctamente `app.yaml`
- Genera config default sensata si archivo no existe
- Resuelve paths relativos correctamente desde cualquier CWD

---

### T2.6: Implementar logging estructurado ⏸️
**Responsable:** Developer  
**Estado:** ⏸️ **PENDIENTE**  
**Archivo:** `alignpress/utils/logger.py`

**Uso:**
```python
from alignpress.utils.logger import get_logger

logger = get_logger(__name__)
logger.info("detector_initialized", logos_count=2, feature_type="ORB")
logger.warning("calibration_near_expiry", camera_id="camera_0", days_remaining=5)
```

**Tareas:**
- [ ] Configurar `structlog` con processors adecuados
- [ ] Logs rotativos por sesión (1 archivo por día)
- [ ] Integración con `AppConfig` para niveles/paths
- [ ] Tests de logging (captura de output)

**Criterios de aceptación:**
- Logs son válidos JSON y parseables
- Rotación funciona correctamente
- Performance no se degrada (logging asíncrono)

---

### T2.7: Tests de integración del core ⏸️
**Responsable:** Developer  
**Estado:** ⏸️ **PENDIENTE**  
**Archivo:** `tests/integration/test_core_pipeline.py`

**Tests a implementar:**
- [ ] `test_load_composition_from_files`: Carga plancha + estilo + variante
- [ ] `test_composition_to_detector_config`: Config generado es válido
- [ ] `test_full_detection_pipeline`: Composición → Detector → JobCard
- [ ] `test_calibration_expiry_workflow`: Carga calibración, verifica vencimiento
- [ ] `test_profile_validation_end_to_end`: Validación completa de profiles

**Criterios de aceptación:**
- Todos los módulos core se integran sin errores
- Pipeline completo (carga → detección → guardado) funciona

---

## Notas de la Fase 2

**Decisiones técnicas:**
- Pydantic se usa para TODA la validación de schemas
- Paths son siempre `pathlib.Path` (nunca strings)
- Fechas/tiempos son siempre `datetime` con timezone UTC

**Deuda técnica identificada:**
- No hay sistema de migraciones de schemas aún
- JobCards no soportan múltiples cámaras aún (pendiente Fase 6)

**Próximos pasos después de T2.7:**
- Pasar a **Fase 3: UI Operador (MVP)**

---

---

# 🖥️ FASE 3: UI OPERADOR (MVP)

**Objetivo:** Implementar interfaz gráfica básica para operadores usando PySide6.

**Prioridad:** 🔥 MEDIA (después de validar el core)  
**Estado:** ⏸️ **PENDIENTE**  
**Duración estimada:** 4-5 días  
**Duración real:** —

---

## Checklist de Tareas

### T3.1: Setup del proyecto PySide6 ⏸️
**Responsable:** Developer  
**Estado:** ⏸️ **PENDIENTE**  
**Archivos:** `alignpress/ui/__init__.py`, `alignpress/ui/main_window.py`

**Tareas:**
- [ ] Añadir PySide6 a `requirements.txt`
- [ ] Crear `MainWindow` con layout básico
- [ ] Implementar cambio entre modos (operador/técnico)
- [ ] Sistema de autenticación con PIN para modo técnico
- [ ] Aplicar tema (light/dark desde `app.yaml`)

**Criterios de aceptación:**
- Ventana principal se abre sin errores
- Cambio de modo funciona con autenticación
- Tema se aplica desde config

---

### T3.2: Implementar wizard de selección ⏸️
**Responsable:** Developer  
**Estado:** ⏸️ **PENDIENTE**  
**Archivo:** `alignpress/ui/operator/wizard.py`

**Funcionalidad:**
- 3 pasos: Plancha → Estilo → Talla
- Preview visual de cada opción
- Validación antes de permitir "Siguiente"
- Guarda última selección como default

**Tareas:**
- [ ] Crear `SelectionWizard` con 3 páginas
- [ ] Implementar `PlatenSelectionPage` con lista + preview
- [ ] Implementar `StyleSelectionPage` con lista + thumbnails
- [ ] Implementar `SizeSelectionPage` con radio buttons
- [ ] Validación: deshabilitar "Siguiente" si selección inválida
- [ ] Guardar última selección en `QSettings`

**Criterios de aceptación:**
- Wizard completo genera `Composition` válida
- Preview muestra correctamente thumbnails/dimensiones
- Última selección se recuerda entre sesiones

---

### T3.3: Implementar widget de cámara ⏸️
**Responsable:** Developer  
**Estado:** ⏸️ **PENDIENTE**  
**Archivo:** `alignpress/ui/widgets/camera_widget.py`

**Funcionalidad:**
- Wrapper de `cv2.VideoCapture` con señales Qt
- Control de FPS (limitable)
- Soporte para imagen estática (modo simulación)

**Tareas:**
- [ ] Implementar `CameraWidget` con QTimer
- [ ] Manejo de errores (cámara no disponible)
- [ ] Modo simulación con imagen estática
- [ ] Control de FPS adaptativo
- [ ] Tests con mock de VideoCapture

**Criterios de aceptación:**
- Emite frames correctamente a FPS configurado
- Maneja gracefully cámara desconectada
- Modo simulación funciona sin cámara física

---

### T3.4: Implementar live view con overlay ⏸️
**Responsable:** Developer  
**Estado:** ⏸️ **PENDIENTE**  
**Archivo:** `alignpress/ui/operator/live_view.py`

**Funcionalidad:**
- Viewport con feed de cámara
- Overlay de posiciones objetivo (fantasma)
- Overlay de detecciones en tiempo real
- Panel lateral con métricas por logo
- Tooltips de corrección

**Tareas:**
- [ ] Implementar `LiveViewWidget` con camera feed
- [ ] Overlay de posiciones objetivo (semi-transparente)
- [ ] Overlay de detecciones con colores semánticos
- [ ] Panel lateral con estado por logo
- [ ] Tooltips con instrucciones
- [ ] Botón "Validar Todo"

**Criterios de aceptación:**
- Feed de cámara se muestra sin lag (>20 FPS)
- Overlays son claros y no obstruyen visión
- Métricas se actualizan en tiempo real

---

### T3.5: Implementar checklist de validación ⏸️
**Responsable:** Developer  
**Estado:** ⏸️ **PENDIENTE**  
**Archivo:** `alignpress/ui/operator/checklist.py`

**Funcionalidad:**
- Lista de logos con estado
- Visualización de métricas finales
- Confirmación antes de guardar job card

**Tareas:**
- [ ] Implementar `ValidationChecklistDialog`
- [ ] Items de resultado con emoji + métricas
- [ ] Botón "Volver" regresa a live view
- [ ] Botón "Confirmar" finaliza job card

**Criterios de aceptación:**
- Dialog muestra claramente estado de cada logo
- Confirmación guarda job card correctamente

---

### T3.6: Implementar panel de métricas ⏸️
**Responsable:** Developer  
**Estado:** ⏸️ **PENDIENTE**  
**Archivo:** `alignpress/ui/widgets/metrics_panel.py`

**Funcionalidad:**
- Panel lateral compacto con estado por logo
- LEDs virtuales (🟢🟡🔴)
- Métricas numéricas (dx, dy, θ)

**Tareas:**
- [ ] Implementar `MetricsPanel` con widgets por logo
- [ ] Implementar `LogoMetricWidget` con LED + labels
- [ ] Actualización eficiente

**Criterios de aceptación:**
- Panel se actualiza en tiempo real sin lag
- LEDs cambian correctamente de color

---

### T3.7: Tests de la UI operador ⏸️
**Responsable:** Developer  
**Estado:** ⏸️ **PENDIENTE**  
**Archivo:** `tests/ui/test_operator_workflow.py`

**Tests a implementar:**
- [ ] `test_wizard_completes_successfully`
- [ ] `test_live_view_processes_frames`
- [ ] `test_overlay_updates_on_detection`
- [ ] `test_validation_checklist_shows_results`
- [ ] `test_job_card_saved_on_confirm`

**Criterios de aceptación:**
- Tests corren sin abrir ventanas
- Coverage >70% en módulos UI

---

## Notas de la Fase 3

**Decisiones técnicas:**
- Se usa `QLabel` con `QPixmap` para viewport
- Overlays se dibujan con OpenCV antes de convertir a QPixmap
- FPS se limita a 20-30 para no sobrecargar Pi

**Próximos pasos después de T3.7:**
- Pasar a **Fase 4: UI Técnico**

---

---

# 🔧 FASE 4: UI TÉCNICO

**Objetivo:** Implementar interfaz para técnicos: calibración, edición de profiles, debugging.

**Prioridad:** 🔥 MEDIA-BAJA  
**Estado:** ⏸️ **PENDIENTE**  
**Duración estimada:** 3-4 días  
**Duración real:** —

---

## Checklist de Tareas

### T4.1: Implementar wizard de calibración ⏸️
**Responsable:** Developer  
**Estado:** ⏸️ **PENDIENTE**  
**Archivo:** `alignpress/ui/technician/calibration_wizard.py`

**Funcionalidad:**
- 3 pasos: Preparación → Captura → Validación
- Preview con detección de chessboard en tiempo real
- Guardado de calibración con metadata

**Criterios de aceptación:**
- Detecta chessboard en tiempo real
- Rechaza calibraciones de baja calidad

---

### T4.2: Implementar editor de profiles ⏸️
**Responsable:** Developer  
**Estado:** ⏸️ **PENDIENTE**  
**Archivo:** `alignpress/ui/technician/profile_editor.py`

**Funcionalidad:**
- Árbol de profiles
- Editor de texto con syntax highlighting
- Preview visual de layout
- Validación en vivo

**Criterios de aceptación:**
- Edición de YAML con syntax highlighting
- Validación detecta errores en tiempo real

---

### T4.3: Implementar debug view ⏸️
**Responsable:** Developer  
**Estado:** ⏸️ **PENDIENTE**  
**Archivo:** `alignpress/ui/technician/debug_view.py`

**Funcionalidad:**
- Viewport con overlays avanzados
- Panel de métricas detalladas
- Logs en tiempo real
- Export de imágenes debug

**Criterios de aceptación:**
- Overlays son toggleables
- Logs se actualizan en tiempo real

---

### T4.4: Tests de la UI técnico ⏸️
**Responsable:** Developer  
**Estado:** ⏸️ **PENDIENTE**  
**Archivo:** `tests/ui/test_technician_workflow.py`

**Tests a implementar:**
- [ ] `test_calibration_wizard_completes`
- [ ] `test_profile_editor_validates`
- [ ] `test_debug_view_shows_overlays`

---

## Notas de la Fase 4

**Próximos pasos después de T4.4:**
- Pasar a **Fase 5: Deployment Raspberry Pi**

---

---

# 🥧 FASE 5: DEPLOYMENT EN RASPBERRY PI

**Objetivo:** Preparar el sistema para correr en Raspberry Pi 4/5.

**Prioridad:** 🔥 MEDIA  
**Estado:** ⏸️ **PENDIENTE**  
**Duración estimada:** 2-3 días  
**Duración real:** —

---

## Checklist de Tareas

### T5.1: Crear Dockerfile para testing ⏸️
**Responsable:** Developer  
**Estado:** ⏸️ **PENDIENTE**  
**Archivo:** `Dockerfile`

**Criterios de aceptación:**
- Imagen construye sin errores
- Tests pasan dentro del contenedor

---

### T5.2: Crear script de instalación para Pi ⏸️
**Responsable:** Developer  
**Estado:** ⏸️ **PENDIENTE**  
**Archivo:** `scripts/install_pi.sh`

**Criterios de aceptación:**
- Script se ejecuta sin errores en Pi limpio
- Aplicación arranca automáticamente al bootear

---

### T5.3: Optimizaciones de rendimiento ⏸️
**Responsable:** Developer  
**Estado:** ⏸️ **PENDIENTE**

**Tareas:**
- [ ] FPS adaptativo
- [ ] Caché de ROIs
- [ ] Reducción de resolución si es necesario
- [ ] Usar OpenCV con OpenCL

**Criterios de aceptación:**
- Detector corre a >20 FPS en Pi 4
- Uso de CPU <70%

---

### T5.4: Modo kiosk/fullscreen ⏸️
**Responsable:** Developer  
**Estado:** ⏸️ **PENDIENTE**

**Criterios de aceptación:**
- Fullscreen funciona en Pi
- Atajos de teclado funcionan

---

### T5.5: Testing end-to-end en Pi ⏸️
**Responsable:** Developer  
**Estado:** ⏸️ **PENDIENTE**

**Criterios de aceptación:**
- Aplicación funciona sin modificaciones en Pi
- Performance es aceptable (>20 FPS)

---

## Próximos pasos después de T5.5:
- Pasar a **Fase 6: Hardware Expansion**

---

---

# 🔌 FASE 6: HARDWARE EXPANSION (FUTURO)

**Objetivo:** Soporte para múltiples cámaras y comunicación con Arduino.

**Prioridad:** 📅 BAJA (planificado, no inmediato)  
**Estado:** 📅 **PLANIFICADO**  
**Duración estimada:** 4-5 días  
**Duración real:** —

---

## Checklist de Tareas

### T6.1: Abstracción de múltiples cámaras ⏸️
**Responsable:** Developer  
**Estado:** 📅 **PLANIFICADO**  
**Archivo:** `alignpress/hardware/camera.py`

---

### T6.2: Protocolo de comunicación Arduino ⏸️
**Responsable:** Developer  
**Estado:** 📅 **PLANIFICADO**  
**Archivo:** `alignpress/hardware/arduino_comm.py`

**Protocolo propuesto:**
```json
// Pi → Arduino
{
  "type": "logo_status",
  "logo": "pecho",
  "status": "OK",
  "deviation": {"dx_mm": 2.1, "dy_mm": -0.8, "theta_deg": 1.2}
}
```

---

### T6.3: Integración de semáforos en UI ⏸️
**Responsable:** Developer  
**Estado:** 📅 **PLANIFICADO**

---

### T6.4: Dashboard multi-estación ⏸️
**Responsable:** Developer  
**Estado:** 📅 **PLANIFICADO**

---

### T6.5: Código Arduino de ejemplo ⏸️
**Responsable:** Developer  
**Estado:** 📅 **PLANIFICADO**  
**Archivo:** `arduino/semaphore_controller/semaphore_controller.ino`

---

---

# 📚 DOCUMENTACIÓN ADICIONAL

## Documentos a Crear

### D1: README.md principal ⏸️
### D2: Guía de instalación ⏸️
### D3: Guía de configuración ⏸️
### D4: Guía del operador ⏸️
### D5: Guía del técnico ⏸️
### D6: Referencia API ⏸️
### D7: Arquitectura del sistema ⏸️
### D8: Guía de contribución ⏸️

---

---

# 🧪 ESTRATEGIA DE TESTING

## Cobertura Objetivo por Módulo

| Módulo | Cobertura Objetivo | Prioridad |
|--------|-------------------|-----------|
| `core/detector.py` | >90% | 🔥 CRÍTICA |
| `core/profile.py` | >85% | 🔥 CRÍTICA |
| `core/composition.py` | >85% | 🔥 CRÍTICA |
| `core/calibration.py` | >80% | 🔥 ALTA |
| `utils/*` | >80% | 🔥 ALTA |
| `cli/*` | >70% | 🔥 MEDIA |
| `ui/operator/*` | >60% | 🔥 MEDIA |
| `ui/technician/*` | >50% | 🔥 MEDIA-BAJA |

---

---

# 🔄 PROCESO DE DESARROLLO

## Workflow Git

### Branches
```
main           → Código en producción (estable)
develop        → Integración continua
feature/T0.5   → Features individuales
hotfix/bug-123 → Fixes urgentes
```

### Commits
**Formato:**
```
[T0.5] Añadir schemas Pydantic para validación

- PlaneConfigSchema con validación de dimensiones
- LogoSpecSchema con verificación de paths
- Tests unitarios para schemas
```

---

## Checklist Pre-Commit

- [ ] Código pasa linters (black, flake8, mypy)
- [ ] Tests unitarios pasan
- [ ] Documentación actualizada
- [ ] No hay TODOs sin issue
- [ ] No hay print() de debug

---

## Checklist Pre-Merge a Develop

- [ ] Todos los tests pasan
- [ ] Cobertura cumple objetivo
- [ ] Documentación actualizada
- [ ] CHANGELOG.md actualizado
- [ ] Code review completado

---

---

# 📊 MÉTRICAS Y KPIs

## Métricas de Desarrollo

| Métrica | Objetivo | Actual |
|---------|----------|--------|
| Cobertura tests (core) | >85% | — |
| FPS promedio (Pi 4) | >25 | — |
| Uso de memoria (pico) | <200MB | — |
| Tiempo de startup | <3s | — |

---

---

# 🚀 ROADMAP DE LANZAMIENTO

## Sprint 0: Fundaciones (Fase 0-1)
**Duración:** 3-5 días  
**Objetivo:** Core funcional y testeado

- [x] Refactoring del detector
- [ ] CLI tools básicos
- [ ] Tests unitarios del core

**Entregable:** Detector funcional vía CLI

---

## Sprint 1: Business Logic (Fase 2)
**Duración:** 3-4 días  
**Objetivo:** Lógica de negocio completa

**Entregable:** Pipeline core end-to-end (CLI)

---

## Sprint 2: UI Operador MVP (Fase 3)
**Duración:** 4-5 días  
**Objetivo:** UI básica funcional

**Entregable:** Aplicación desktop funcional

---

## Sprint 3: UI Técnico (Fase 4)
**Duración:** 3-4 días  
**Objetivo:** Herramientas para técnicos

**Entregable:** Aplicación completa

---

## Sprint 4: Deployment Pi (Fase 5)
**Duración:** 2-3 días  
**Objetivo:** Sistema corriendo en hardware final

**Entregable:** Sistema desplegado en Pi

---

## Sprint 5: Hardware Expansion (Fase 6)
**Duración:** 4-5 días  
**Objetivo:** Múltiples cámaras + Arduino

**Entregable:** Sistema completo

---

---

# 🐛 REGISTRO DE DECISIONES TÉCNICAS

## ADR-001: Uso de ORB en lugar de SIFT/SURF
**Fecha:** 2025-09-28  
**Estado:** ✅ Aceptado

**Justificación:**
- ORB es libre de patentes
- Performance excelente en Pi
- Robusto a rotación y escala

---

## ADR-002: PySide6 en lugar de PyQt6
**Fecha:** 2025-09-28  
**Estado:** ✅ Aceptado

**Justificación:**
- Licencia LGPL más permisiva
- Mantenimiento oficial de Qt Company
- Buen soporte en Raspberry Pi

---

## ADR-003: YAML para configuración, JSON para datos
**Fecha:** 2025-09-28  
**Estado:** ✅ Aceptado

**Justificación:**
- YAML es más legible para técnicos
- JSON es más estándar para datos

---

## ADR-004: Homografía pre-calculada vs detección de marcadores
**Fecha:** 2025-09-28  
**Estado:** ✅ Aceptado

**Justificación:**
- Mucho más rápido
- Suficientemente preciso si cámara está fija
- Calibración periódica compensa drift

---

---

# 📋 LISTA DE VERIFICACIÓN FINAL

## Pre-Producción Checklist

### Funcionalidad
- [ ] Detector funciona con >95% de éxito
- [ ] UI operador es intuitiva
- [ ] Job cards se guardan correctamente
- [ ] Sistema maneja errores gracefully

### Performance
- [ ] FPS >25 en Pi 4
- [ ] Tiempo de startup <3s
- [ ] Uso de memoria <200MB
- [ ] CPU <70%

### Estabilidad
- [ ] Sin crashes en 8h continuas
- [ ] Logs no llenan disco
- [ ] Sistema se recupera de errores

### Documentación
- [ ] README completo
- [ ] Guía del operador
- [ ] Guía de instalación
- [ ] API documentada

### Testing
- [ ] Cobertura >80% en core
- [ ] Tests de integración pasan
- [ ] Testing manual en Pi completo

### Deployment
- [ ] Script de instalación funciona
- [ ] Autostart configurado
- [ ] Backup implementado

---

---

# 🆘 TROUBLESHOOTING COMÚN

## P1: "No se detectan logos"

**Causas:**
- Iluminación inadecuada
- Template mal recortado
- ROI muy pequeña
- Calibración incorrecta

**Solución:**
1. Verificar iluminación uniforme
2. Recortar templates con margen mínimo
3. Aumentar `roi.margin_factor`
4. Re-calibrar cámara

---

## P2: "FPS muy bajo"

**Causas:**
- Resolución muy alta
- `nfeatures` muy alto
- ROIs grandes
- Fallback activo

**Solución:**
1. Reducir resolución a 1280×720
2. Reducir `nfeatures` a 1000-1200
3. Ajustar ROIs más pequeñas
4. Deshabilitar fallback

---

## P3: "Calibración falla"

**Causas:**
- Patrón no plano
- Brillos en el patrón
- Resolución baja
- Cámara desenfocada

**Solución:**
1. Imprimir en papel rígido
2. Iluminación difusa
3. Imprimir en alta calidad
4. Ajustar enfoque

---

---

# 📞 CONTACTOS Y RECURSOS

## Recursos de Desarrollo

### Documentación Oficial
- **OpenCV:** https://docs.opencv.org/4.x/
- **PySide6:** https://doc.qt.io/qtforpython/
- **Pydantic:** https://docs.pydantic.dev/
- **structlog:** https://www.structlog.org/

---

## Mantenimiento del Documento

**Última actualización:** 2025-09-28  
**Responsable:** Developer  
**Frecuencia:** Semanal durante desarrollo

---

---

# 🎯 PRÓXIMOS PASOS INMEDIATOS

## Para Developer (AHORA)

### 1. Completar Fase 0 ✅
Ya completado.

### 2. Iniciar T0.5: Schemas Pydantic ⏸️
**Acción inmediata:**
```bash
touch alignpress/core/schemas.py
```

### 3. Crear fixtures para testing ⏸️
```bash
mkdir -p tests/fixtures/{images,configs}
```

---

## Template para Reportes de Progreso

```markdown
## Reporte Semanal - Semana del [FECHA]

### Completado
- [x] T0.2: Refactorizar PlanarLogoDetector

### En Progreso
- [ ] T0.5: Schemas Pydantic (70%)

### Próxima Semana
- [ ] T0.6: Tests unitarios

### Bloqueadores
- Ninguno

### Métricas
- Cobertura: 45%
- Tests pasando: 12/15
```

---

---

# 📝 NOTAS FINALES

## Filosofía del Proyecto

> **"Funcional antes que perfecto, testeado antes que features"**

Prioridades:
1. **Robustez:** Simple que funciona > complejo que falla
2. **Testabilidad:** Tests independientes
3. **Documentación:** Código autoexplicativo
4. **Performance:** Optimizar después de medir

---

## Principios de Desarrollo

### YAGNI
No implementar funcionalidad "tal vez necesitemos después"

### KISS
Preferir soluciones simples

### DRY
Evitar duplicación mediante abstracción

---

## Glosario de Términos

| Término | Definición |
|---------|-----------|
| **Plancha** | Superficie de la prensa |
| **Logo** | Diseño a estampar |
| **ROI** | Region of Interest |
| **Homografía** | Transformación imagen→plano |
| **Template** | Imagen de referencia |
| **Composición** | Plancha + estilo + variante |
| **Job Card** | Tarjeta con métricas |
| **Profile** | Archivo de configuración |

---

---

**FIN DEL DOCUMENTO**

---

**Instrucciones de uso:**

1. Este documento vive en `DEVELOPMENT_PLAN.md`
2. Actualizar semanalmente
3. Marcar tareas con ✅ y fecha
4. Documentar decisiones como ADRs
5. Exportable a PDF

**Mantenimiento:**
- Revisar checklist cada lunes
- Archivar tareas mensuales
- Actualizar roadmap según cambios