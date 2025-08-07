import pygame

# Configuración de pantalla
ANCHO, ALTO = 1000, 494
pygame.init()
pantalla = pygame.display.set_mode((ANCHO, ALTO))
pygame.display.set_caption("Editor de Plataformas")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 24)

# Parámetros de plataforma
platforms = []
platform_color = (0, 255, 0)
current_platform = None
drawing = False

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
    print(f"Guardado en {filename}")

# Bucle principal del editor
corriendo = True
while corriendo:
    pantalla.fill((30, 30, 30))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            corriendo = False

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Clic izquierdo inicia rectángulo
                start_pos = pygame.mouse.get_pos()
                current_platform = pygame.Rect(*start_pos, 0, 0)
                drawing = True

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1 and current_platform:
                drawing = False
                if current_platform.width > 5 and current_platform.height > 5:
                    platforms.append((current_platform.x, current_platform.y, current_platform.width, current_platform.height))
                    print(f"Plataforma añadida: ({current_platform.x}, {current_platform.y}, {current_platform.width}, {current_platform.height})")
                current_platform = None

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_s:
                save_platforms()

    # Actualización de plataforma en dibujo
    if drawing and current_platform:
        mouse_x, mouse_y = pygame.mouse.get_pos()
        current_platform.width = mouse_x - current_platform.x
        current_platform.height = mouse_y - current_platform.y

    # Dibujar plataformas existentes
    for plat in platforms:
        pygame.draw.rect(pantalla, platform_color, pygame.Rect(*plat))

    # Dibujar plataforma actual en edición
    if current_platform:
        pygame.draw.rect(pantalla, (0, 200, 200), current_platform, 2)

    draw_text("Haz clic y arrastra para crear plataformas.", 10, 10)
    draw_text("Presiona 'S' para guardar.", 10, 30)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
