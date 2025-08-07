import pygame
import os

# Configuración de pantalla
ANCHO, ALTO = 1000, 494
pygame.init()
pantalla = pygame.display.set_mode((ANCHO, ALTO))
pygame.display.set_caption("Editor de Plataformas con Fondo")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 24)

# Cargar fondo
try:
    fondo = pygame.image.load("assets/maps/fondo.png").convert()
    fondo = pygame.transform.scale(fondo, (ANCHO, ALTO))
except:
    print("⚠️ No se encontró la imagen 'fondo.png'. Asegúrate de que exista.")
    fondo = pygame.Surface((ANCHO, ALTO))
    fondo.fill((30, 30, 30))

# Parámetros de plataforma
platforms = []
platform_color = (0, 255, 0)
current_platform = None
drawing = False
start_pos = None

def draw_text(text, x, y, color=(255, 255, 255)):
    rendered = font.render(text, True, color)
    pantalla.blit(rendered, (x, y))

def save_platforms(filename="plataformas_generadas.py"):
    with open(filename, "w") as f:
        f.write("# Lista de plataformas generadas desde el editor\n")
        f.write("PLATAFORMAS = [\n")
        for plat in platforms:
            x, y, w, h = plat
            f.write(f"    ({x}, {y}, {w}, {h}),\n")
        f.write("]\n")
    print(f"✅ Plataformas guardadas en {filename}")

# Bucle principal del editor
corriendo = True
while corriendo:
    pantalla.blit(fondo, (0, 0))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            corriendo = False

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Clic izquierdo inicia rectángulo
                start_pos = pygame.mouse.get_pos()
                drawing = True

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1 and current_platform:
                drawing = False
                if current_platform.width > 5 and current_platform.height > 5:
                    platforms.append((current_platform.x, current_platform.y, current_platform.width, current_platform.height))
                    print(f"🟩 Plataforma añadida: ({current_platform.x}, {current_platform.y}, {current_platform.width}, {current_platform.height})")
                current_platform = None
                start_pos = None

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_s:
                save_platforms()

    # Actualizar plataforma en dibujo (soporta arrastrar en cualquier dirección)
    if drawing and start_pos:
        mouse_x, mouse_y = pygame.mouse.get_pos()
        x1, y1 = start_pos
        x2, y2 = mouse_x, mouse_y
        x = min(x1, x2)
        y = min(y1, y2)
        w = abs(x2 - x1)
        h = abs(y2 - y1)
        current_platform = pygame.Rect(x, y, w, h)

    # Dibujar plataformas existentes
    for plat in platforms:
        pygame.draw.rect(pantalla, platform_color, pygame.Rect(*plat), 2)

    # Dibujar plataforma en edición
    if current_platform:
        pygame.draw.rect(pantalla, (0, 200, 200), current_platform, 2)

    # Cuadrícula (opcional)
    for x in range(0, ANCHO, 50):
        pygame.draw.line(pantalla, (50, 50, 50), (x, 0), (x, ALTO))
    for y in range(0, ALTO, 50):
        pygame.draw.line(pantalla, (50, 50, 50), (0, y), (ANCHO, y))

    # Instrucciones
    draw_text("🖱️ Clic y arrastra para crear plataformas", 10, 10)
    draw_text("💾 Presiona 'S' para guardar", 10, 30)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
