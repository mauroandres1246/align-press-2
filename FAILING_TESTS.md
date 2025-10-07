# Tests Fallidos - Análisis Detallado

**Total:** 29 tests fallidos de 250 tests (11.6%)
**Pasando:** 221/250 (88.4%)

---

## Resumen por Categoría

| Categoría | Fallidos | Total | % Fallo |
|-----------|----------|-------|---------|
| CLI Integration | 4 | 19 | 21% |
| CLI Calibrate | 5 | 13 | 38% |
| Detector Unit | 10 | 32 | 31% |
| Detector Transparency | 2 | 9 | 22% |
| Profile | 1 | 10 | 10% |
| Schemas Extended | 5 | 19 | 26% |
| Template Extraction | 1 | 14 | 7% |
| **Benchmark** | **ERROR** | - | - |

---

## 1. CLI Integration Tests (4 fallos)

### Archivo: `tests/integration/test_cli_integration.py`

#### ❌ test_validate_command_success
**Error:** `assert result.returncode == 0` (got 1)
**Causa:** CLI validate_profile está retornando error code 1
**Prioridad:** 🔥 ALTA

#### ❌ test_validate_command_directory
**Error:** `assert result.returncode == 0` (got 1)
**Causa:** Validación de directorio falla
**Prioridad:** 🔥 ALTA

#### ❌ test_validate_command_with_schema
**Error:** `assert result.returncode == 0` (got 1)
**Causa:** Validación con schema falla
**Prioridad:** 🔥 ALTA

#### ❌ test_verbose_and_quiet_flags
**Error:** `assert result.returncode == 0` (got 1)
**Output:** `✗ logos must be a non-empty list`
**Causa:** Profile de test es inválido
**Prioridad:** 🔥 ALTA

**Solución sugerida:** Los tests están creando profiles temporales que no cumplen con el schema. Necesitan crear profiles válidos con al menos un logo.

---

## 2. CLI Calibrate Tests (5 fallos)

### Archivo: `tests/integration/test_cli_calibrate.py`

#### ❌ test_calculate_mm_per_px
**Error:** `AttributeError: 'CameraCalibrator' object has no attribute '_calculate_mm_per_px'`
**Causa:** Método privado no existe en implementación
**Prioridad:** ⚠️ MEDIA (test mal escrito)

#### ❌ test_save_calibration
**Error:** `KeyError: 'plane_config'`
**Causa:** El JSON guardado usa estructura de CalibrationDataSchema, no tiene campo 'plane_config' separado
**Prioridad:** ⚠️ MEDIA (test mal escrito)

#### ❌ test_validate_calibration_good
**Error:** `KeyError: 'scale_consistency'`
**Causa:** quality_metrics no incluye 'scale_consistency' en el mock
**Prioridad:** ⚠️ MEDIA (test incompleto)

#### ❌ test_validate_calibration_bad_error
**Error:** `KeyError: 'scale_consistency'`
**Causa:** Mismo que arriba
**Prioridad:** ⚠️ MEDIA

#### ❌ test_validate_calibration_missing_corners
**Error:** `KeyError: 'scale_consistency'`
**Causa:** Mismo que arriba
**Prioridad:** ⚠️ MEDIA

**Solución sugerida:** Actualizar tests para que coincidan con la estructura real del CameraCalibrator. Revisar qué métricas realmente calcula el validador.

---

## 3. Detector Unit Tests (10 fallos)

### Archivo: `tests/unit/test_detector.py`

#### ❌ test_px_to_mm_conversion
**Error:** `assert abs(x_mm - 10.0) < 1e-6` → `assert 30.0 < 1e-06`
**Causa:** Confusión entre mm_per_px y px_per_mm
**Prioridad:** 🔥 ALTA

#### ❌ test_conversion_roundtrip
**Error:** `assert abs(back_to_mm[0] - original_mm[0]) < 1.0` → `assert 46.7 < 1.0`
**Causa:** Mismo error de conversión
**Prioridad:** 🔥 ALTA

#### ❌ test_detect_perfect_alignment
**Error:** `assert result.found is True` → `False`
**Causa:** Template tiene muy pocas features (6), detector no puede hacer matching
**Prioridad:** 🔥 ALTA (mock template insuficiente)

#### ❌ test_detect_with_offset
**Error:** `assert result.found is True` → `False`
**Causa:** Mock template insuficiente
**Prioridad:** 🔥 ALTA

#### ❌ test_detect_with_rotation
**Error:** `assert result.found is True` → `False`
**Causa:** Mock template insuficiente
**Prioridad:** 🔥 ALTA

#### ❌ test_detect_single_logo_multi_config
**Error:** `assert logo_a_result.found is True` → `False`
**Causa:** Mock template insuficiente
**Prioridad:** 🔥 ALTA

#### ❌ test_roi_centered_correctly
**Error:** `assert abs(roi_offset[0] - expected_px[0]) < 100` → `assert 120 < 100`
**Causa:** ROI no se está centrando correctamente en el cálculo
**Prioridad:** 🔥 ALTA

#### ❌ test_detector_with_custom_thresholds
**Error:** `AttributeError: 'ThresholdsSchema' object has no attribute 'max_deviation_mm'`
**Causa:** El schema usa nombres diferentes (ej: `max_deviation` en vez de `max_deviation_mm`)
**Prioridad:** ⚠️ MEDIA (test desactualizado)

#### ❌ test_detector_with_akaze_features
**Error:** `KeyError: 'features'`
**Causa:** detector_config no tiene el campo 'features'
**Prioridad:** ⚠️ MEDIA (test mal escrito)

#### ❌ test_full_pipeline_perfect_case
**Error:** `assert result.found is True` → `False`
**Causa:** Mock template insuficiente
**Prioridad:** 🔥 ALTA

#### ❌ test_full_pipeline_multiple_logos
**Error:** `assert detected_count >= 1` → `assert 0 >= 1`
**Causa:** Mock templates insuficientes
**Prioridad:** 🔥 ALTA

**Solución sugerida:**
1. Crear función helper que genere templates realistas con suficientes features (>50)
2. Arreglar conversiones px↔mm (usar `1/mm_per_px` cuando sea necesario)
3. Actualizar tests para usar nombres de campos correctos en schemas

---

## 4. Detector Transparency Tests (2 fallos)

### Archivo: `tests/unit/test_detector_transparency.py`

#### ❌ test_detector_handles_invalid_template_path
**Error:** `pydantic_core._pydantic_core.ValidationError: Template file not found`
**Causa:** LogoSpecSchema valida que el template existe al crear el objeto
**Prioridad:** ⚠️ BAJA (test necesita usar `pytest.raises` desde el inicio)

#### ❌ test_detector_with_circle_logo
**Error:** `assert len(unique_values) > 2` → `assert 2 > 2`
**Causa:** Mock circle logo solo tiene 2 valores únicos (0 y 255), esperaba gradient
**Prioridad:** ⚠️ BAJA (mock necesita mejorar)

**Solución sugerida:** Mejorar generación de mock templates con gradientes.

---

## 5. Profile Tests (1 fallo)

### Archivo: `tests/unit/test_profile.py`

#### ❌ test_load_valid_variant
**Error:**
```
ValidationError: 3 validation errors for SizeVariant
  type: Value error, Type must be 'variant', got 'size_variant'
  size: Field required
  offsets: Field required
```
**Causa:** El archivo YAML de test tiene `type: 'size_variant'` pero debe ser `type: 'variant'`
**Prioridad:** ⚠️ MEDIA (fixture mal configurado)

**Solución sugerida:** Corregir el archivo `profiles/variantes/test_variant.yaml` para que tenga los campos correctos.

---

## 6. Schemas Extended Tests (5 fallos)

### Archivo: `tests/unit/test_schemas_extended.py`

#### ❌ test_default_thresholds
**Error:** `AttributeError: 'ThresholdsSchema' object has no attribute 'max_deviation_mm'`
**Causa:** Campo se llama `max_deviation` no `max_deviation_mm`
**Prioridad:** ⚠️ MEDIA

#### ❌ test_custom_thresholds
**Error:** Mismo error
**Prioridad:** ⚠️ MEDIA

#### ❌ test_threshold_validation
**Error:** `Failed: DID NOT RAISE <class 'ValueError'>`
**Causa:** ThresholdsSchema permite valores negativos (no valida)
**Prioridad:** ⚠️ BAJA (feature no implementada)

#### ❌ test_plane_with_homography
**Error:** `AttributeError: 'PlaneConfigSchema' object has no attribute 'homography'`
**Causa:** PlaneConfigSchema no tiene campo homography (está en CalibrationInfo)
**Prioridad:** ⚠️ MEDIA (test desactualizado)

#### ❌ test_fallback_enabled
**Error:** `AttributeError: 'FallbackParamsSchema' object has no attribute 'angles_deg'`
**Causa:** Campo se llama diferente en la implementación real
**Prioridad:** ⚠️ MEDIA

**Solución sugerida:** Revisar schema real y actualizar todos los tests para usar nombres de campos correctos.

---

## 7. Template Extraction Test (1 fallo)

### Archivo: `tests/unit/test_template_extraction_transparency.py`

#### ❌ test_full_extraction_workflow_with_background_removal
**Error:** `assert output_path.exists()` → `False`
**Causa:** El archivo no se guardó en la ruta esperada
**Prioridad:** ⚠️ BAJA (edge case)

**Solución sugerida:** Verificar que el extractor realmente guarde el archivo.

---

## 8. Benchmark Tests (ERROR)

### Archivo: `tests/integration/test_cli_benchmark.py`

#### 🔴 ERROR durante collection
**Error:** `ImportError while importing test module`
**Causa:** Error de importación, posiblemente import circular o módulo faltante
**Prioridad:** 🔥 CRÍTICA

**Solución sugerida:** Revisar imports en el archivo test_cli_benchmark.py

---

## Plan de Acción Sugerido

### Prioridad 1 (CRÍTICA - 1-2 horas)

1. ✅ Arreglar import error en `test_cli_benchmark.py`
2. ✅ Arreglar 4 tests de CLI integration (crear profiles válidos en fixtures)
3. ✅ Arreglar conversiones px↔mm en detector tests

### Prioridad 2 (ALTA - 2-3 horas)

4. ✅ Crear helper para generar mock templates con suficientes features
5. ✅ Arreglar 7 tests de detector que usan mock templates insuficientes
6. ✅ Corregir test de ROI centering

### Prioridad 3 (MEDIA - 1-2 horas)

7. ✅ Actualizar tests de calibración para coincidir con implementación real
8. ✅ Corregir fixture de variant profile
9. ✅ Actualizar tests de schemas para usar nombres de campos correctos

### Prioridad 4 (BAJA - opcional)

10. ⚠️ Mejorar mock circle logo con gradientes
11. ⚠️ Agregar validación de valores negativos a ThresholdsSchema
12. ⚠️ Verificar guardado de archivos en template extraction

---

## Tiempo Estimado Total

- **Prioridad 1:** 1-2 horas → 4 tests CLI + benchmark error
- **Prioridad 2:** 2-3 horas → 8 tests detector
- **Prioridad 3:** 1-2 horas → 11 tests schemas/calibrate/profile
- **Total:** 4-7 horas de trabajo

**Resultado esperado:** 250/250 tests pasando (100%)

---

**Última actualización:** 1 de octubre, 2025
