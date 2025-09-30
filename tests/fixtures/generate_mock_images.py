"""
Script para generar imágenes mock para testing del detector.
Crea templates y escenas de prueba con transformaciones conocidas.
"""

import cv2
import numpy as np
from pathlib import Path


def create_simple_template(name: str, size=(100, 80), color=(0, 0, 255)):
    """Crea un template simple con features detectables."""
    img = np.ones((size[1], size[0], 3), dtype=np.uint8) * 255  # Fondo blanco

    # Añadir formas con features detectables
    cv2.rectangle(img, (10, 10), (size[0]-10, size[1]-10), color, 2)
    cv2.circle(img, (size[0]//2, size[1]//2), 15, color, -1)

    # Añadir texto para más features
    cv2.putText(img, name.upper(), (15, size[1]//2),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)

    return img


def create_plane_image(templates_info, plane_size=(600, 400), background_color=220):
    """
    Crea una imagen de plancha con logos en posiciones específicas.

    Args:
        templates_info: Lista de dicts con {template, position, angle}
        plane_size: (width, height) en pixels
        background_color: Color de fondo

    Returns:
        Imagen de la plancha con logos
    """
    plane = np.ones((plane_size[1], plane_size[0], 3), dtype=np.uint8) * background_color

    for info in templates_info:
        template = info['template']
        pos = info['position']  # (x, y) centro en pixels
        angle = info.get('angle', 0.0)  # grados

        h, w = template.shape[:2]

        # Crear matriz de rotación
        M = cv2.getRotationMatrix2D((w//2, h//2), angle, 1.0)

        # Calcular nuevo tamaño después de rotación
        cos = abs(M[0, 0])
        sin = abs(M[0, 1])
        new_w = int(h * sin + w * cos)
        new_h = int(h * cos + w * sin)

        # Ajustar traslación
        M[0, 2] += (new_w - w) / 2
        M[1, 2] += (new_h - h) / 2

        # Rotar template
        rotated = cv2.warpAffine(template, M, (new_w, new_h),
                                 borderMode=cv2.BORDER_CONSTANT,
                                 borderValue=(background_color, background_color, background_color))

        # Calcular posición de pegado
        x1 = max(0, int(pos[0] - new_w // 2))
        y1 = max(0, int(pos[1] - new_h // 2))
        x2 = min(plane_size[0], x1 + new_w)
        y2 = min(plane_size[1], y1 + new_h)

        # Recortar template si es necesario
        crop_x1 = max(0, -int(pos[0] - new_w // 2))
        crop_y1 = max(0, -int(pos[1] - new_h // 2))
        crop_x2 = crop_x1 + (x2 - x1)
        crop_y2 = crop_y1 + (y2 - y1)

        # Pegar template en plancha
        if x2 > x1 and y2 > y1:
            plane[y1:y2, x1:x2] = rotated[crop_y1:crop_y2, crop_x1:crop_x2]

    return plane


def main():
    """Genera todas las imágenes mock necesarias."""
    base_path = Path(__file__).parent
    templates_path = base_path / "templates"
    images_path = base_path / "images"

    templates_path.mkdir(exist_ok=True)
    images_path.mkdir(exist_ok=True)

    print("🎨 Generando templates mock...")

    # Template A (rojo)
    template_a = create_simple_template("A", size=(100, 80), color=(0, 0, 255))
    cv2.imwrite(str(templates_path / "mock_template_a.png"), template_a)
    print(f"  ✓ {templates_path / 'mock_template_a.png'}")

    # Template B (azul)
    template_b = create_simple_template("B", size=(80, 60), color=(255, 0, 0))
    cv2.imwrite(str(templates_path / "mock_template_b.png"), template_b)
    print(f"  ✓ {templates_path / 'mock_template_b.png'}")

    print("\n🖼️  Generando escenas de prueba...")

    # Configuración de la plancha (300mm x 200mm @ 0.5 mm/px = 600x400 px)
    plane_size = (600, 400)

    # 1. Escena perfecta (logos en posiciones exactas)
    print("  Generando: escena perfecta...")
    perfect_scene = create_plane_image([
        {
            'template': template_a,
            'position': (300, 200),  # Centro: 150mm, 100mm @ 0.5mm/px = 300px, 200px
            'angle': 0.0
        },
        {
            'template': template_b,
            'position': (150, 100),  # 75mm, 50mm @ 0.5mm/px = 150px, 100px
            'angle': 0.0
        }
    ], plane_size=plane_size)
    cv2.imwrite(str(images_path / "mock_plane_perfect.jpg"), perfect_scene)
    print(f"  ✓ {images_path / 'mock_plane_perfect.jpg'}")

    # 2. Escena con offset (desviación de 5mm = 10px @ 0.5mm/px)
    print("  Generando: escena con offset...")
    offset_scene = create_plane_image([
        {
            'template': template_a,
            'position': (310, 205),  # +5mm en x e y = +10px
            'angle': 3.0  # +3 grados
        },
        {
            'template': template_b,
            'position': (145, 95),  # -5mm en x e y = -10px
            'angle': -3.0  # -3 grados
        }
    ], plane_size=plane_size)
    cv2.imwrite(str(images_path / "mock_plane_offset.jpg"), offset_scene)
    print(f"  ✓ {images_path / 'mock_plane_offset.jpg'}")

    # 3. Escena con rotación (10 grados)
    print("  Generando: escena con rotación...")
    rotated_scene = create_plane_image([
        {
            'template': template_a,
            'position': (300, 200),
            'angle': 10.0
        },
        {
            'template': template_b,
            'position': (150, 100),
            'angle': -10.0
        }
    ], plane_size=plane_size)
    cv2.imwrite(str(images_path / "mock_plane_rotated.jpg"), rotated_scene)
    print(f"  ✓ {images_path / 'mock_plane_rotated.jpg'}")

    # 4. Escena sin logos (fondo vacío)
    print("  Generando: escena sin logos...")
    empty_scene = np.ones((plane_size[1], plane_size[0], 3), dtype=np.uint8) * 220
    cv2.imwrite(str(images_path / "mock_plane_empty.jpg"), empty_scene)
    print(f"  ✓ {images_path / 'mock_plane_empty.jpg'}")

    # 5. Escena con solo un logo
    print("  Generando: escena con un solo logo...")
    single_logo_scene = create_plane_image([
        {
            'template': template_a,
            'position': (300, 200),
            'angle': 0.0
        }
    ], plane_size=plane_size)
    cv2.imwrite(str(images_path / "mock_plane_single_logo.jpg"), single_logo_scene)
    print(f"  ✓ {images_path / 'mock_plane_single_logo.jpg'}")

    print("\n✅ Todas las imágenes mock generadas exitosamente!")
    print(f"\n📁 Templates: {templates_path}")
    print(f"📁 Imágenes:  {images_path}")


if __name__ == "__main__":
    main()
