# JSON Schemas for Align-Press v2

Este directorio contiene los JSON schemas para validación de archivos de configuración.

## Schemas Disponibles

### `detector.schema.json`
Schema para archivos de configuración del detector.

**Uso:**
```bash
python -m alignpress.cli.validate_profile \
  config/example_detector.yaml \
  --schema config/schemas/detector.schema.json
```

### `platen.schema.json`
Schema para perfiles de planchas.

**Uso:**
```bash
python -m alignpress.cli.validate_profile \
  profiles/planchas/plancha_300x200.yaml \
  --schema config/schemas/platen.schema.json
```

### `style.schema.json`
Schema para perfiles de estilos.

**Uso:**
```bash
python -m alignpress.cli.validate_profile \
  profiles/estilos/polo_basico.yaml \
  --schema config/schemas/style.schema.json
```

### `variant.schema.json`
Schema para variantes de talla.

**Uso:**
```bash
python -m alignpress.cli.validate_profile \
  profiles/variantes/talla_m.yaml \
  --schema config/schemas/variant.schema.json
```

## Validación Automática

Los schemas se pueden usar con el CLI de validación para verificar:

- **Estructura correcta**: Campos requeridos y tipos de datos
- **Valores válidos**: Rangos numéricos, enums, patrones
- **Consistencia**: Referencias entre campos

## Desarrollo

Al modificar los schemas:

1. Actualizar la versión si hay cambios breaking
2. Documentar cambios en el schema
3. Actualizar tests de validación
4. Verificar compatibilidad con perfiles existentes

## Herramientas

Para validación manual con herramientas externas:

```bash
# Con ajv-cli (npm install -g ajv-cli)
ajv validate -s detector.schema.json -d ../../config/example_detector.yaml

# Con Python jsonschema
python -c "
import json, yaml, jsonschema
with open('detector.schema.json') as f: schema = json.load(f)
with open('../../config/example_detector.yaml') as f: data = yaml.safe_load(f)
jsonschema.validate(data, schema)
print('Valid!')
"
```