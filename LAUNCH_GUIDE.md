# 🚀 Guía de Lanzamiento - Align-Press v2

## Requisitos Previos

```bash
# Asegúrate de estar en el entorno virtual
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate  # Windows
```

## 🎯 Modos de Lanzamiento

### 1. **Wizard de Calibración** 📷
Herramienta para calibrar la cámara con patrón de tablero de ajedrez.

```bash
python run_app.py --calibration
```

**Pasos:**
1. Configura el patrón de tablero (default: 9x6, 25mm)
2. Captura imágenes desde diferentes ángulos (mínimo 5)
3. El wizard calcula automáticamente la homografía
4. Guarda el archivo de calibración (.npz)

---

### 2. **Editor de Profiles** 📝
Editor con syntax highlighting para archivos YAML de profiles.

```bash
python run_app.py --profile-editor
```

**Características:**
- Syntax highlighting para YAML
- Números de línea
- Templates para Platen y Style profiles
- Validación YAML en tiempo real
- Explorador de archivos

---

### 3. **Debug View** 🔍
Vista avanzada para debugging de detección de logos.

```bash
python run_app.py --debug
```

**Características:**
- Preview en tiempo real de la cámara
- Métricas detalladas de detección
- Visualización de keypoints y matches
- Control de overlays (ROI, homography, etc.)
- Datos raw en JSON

---

### 4. **Aplicación Completa** 🖥️
Aplicación completa con modo operador y técnico.

```bash
python run_app.py                  # Modo operador
python run_app.py --technician     # Modo técnico
```

---

## 🛠️ Opciones Avanzadas

### Usando cámara específica
```bash
# La mayoría de sistemas usan camera_id=0 por defecto
# Si tienes múltiples cámaras, puedes cambiar el ID en el código
```

### Simulación sin cámara
Si no tienes cámara disponible, el código usa imágenes de simulación automáticamente.

---

## 📁 Estructura de Archivos Esperada

```
align-press-v2/
├── profiles/
│   ├── planchas/           # Platen profiles
│   │   └── *.yaml
│   └── estilos/            # Style profiles
│       └── *.yaml
├── templates/
│   └── *.png
├── calibration/
│   └── *.npz
└── logs/
    ├── jobs/
    └── snapshots/
```

**Nota**: El sistema usa carpetas "planchas" y "estilos" (en español) dentro de `profiles/`.

---

## 🎨 Ejemplos de Uso

### Flujo Completo para Técnico

1. **Calibrar cámara:**
   ```bash
   python run_app.py --calibration
   ```

2. **Crear/editar profiles:**
   ```bash
   python run_app.py --profile-editor
   ```

3. **Debug de detección:**
   ```bash
   python run_app.py --debug
   ```

### Flujo para Operador

```bash
python run_app.py
# Seleccionar composición → Live view → Capturar → Validar
```

---

## ⚠️ Troubleshooting

### Error: No se puede abrir la cámara
- Verifica que ninguna otra app esté usando la cámara
- Prueba con `camera_id=1` o `2` si tienes múltiples cámaras
- Otorga permisos de cámara al sistema

### Error: Template no encontrado
- Asegúrate de tener templates en `templates/` o `tests/fixtures/templates/`
- El script creará templates de demo automáticamente

### Error: YAML inválido
- Usa el Profile Editor con validación incorporada
- Verifica indentación (usar espacios, no tabs)

---

## 🎥 Demo Rápido

**Ver el Wizard de Calibración:**
```bash
python run_app.py --calibration
```

**Ver el Editor de Profiles:**
```bash
python run_app.py --profile-editor
```

**Ver Debug View (sin cámara, modo demo):**
```bash
python run_app.py --debug
```

---

## 📝 Notas

- Todos los modos son independientes y se pueden lanzar por separado
- El Debug View crea automáticamente un composition de demo
- El Profile Editor busca profiles en `profiles/planchas` y `profiles/estilos`
- Los archivos de calibración se guardan en `calibration/`
- Ya se han creado 2 platens y 2 estilos de demostración para probar el wizard

---

## 🆘 Ayuda

```bash
python run_app.py --help
```
