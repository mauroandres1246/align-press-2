# Templates Directory

Este directorio contiene las imágenes de referencia (templates) para la detección de logos.

## Estructura esperada:

- `logo_pecho.png` - Template para logo del pecho
- `logo_manga_izq.png` - Template para logo manga izquierda
- `logo_manga_der.png` - Template para logo manga derecha

## Notas:

- Las imágenes deben estar en formato PNG, JPG, JPEG, BMP o TIFF
- Recomendado: fondo blanco, logo en negro/color sólido
- Tamaño recomendado: 50-150 píxeles de ancho
- Asegurar que tengan suficientes features distintivos para ORB detector

## Para generar templates de prueba:

```bash
# Instalar dependencias primero
pip install -r requirements.txt

# Generar templates sintéticos
python3 tools/create_test_templates.py
```

## Calidad del template:

Un buen template debe:
- Tener suficientes features distintivos (esquinas, bordes, patrones)
- No ser demasiado uniforme o simple
- Estar bien iluminado y enfocado
- Ser representativo del logo real