import os
import pygame

class RobotSelector:
    def __init__(self, screen, robots_path):
        self.screen = screen
        self.robots_path = robots_path
        self.robots = []  # (nombre, imagen)
        self.selected_index = 0
        self.load_portraits()

        self.font = pygame.font.Font(None, 28)

    def load_portraits(self):
        for folder in os.listdir(self.robots_path):
            folder_path = os.path.join(self.robots_path, folder)
            portrait_path = os.path.join(folder_path, "portrait.png")
            if os.path.isdir(folder_path) and os.path.exists(portrait_path):
                image = pygame.image.load(portrait_path).convert_alpha()
                self.robots.append((folder, image))

    def run(self):
        clock = pygame.time.Clock()
        running = True

        while running:
            self.screen.fill((30, 30, 30))

            # Eventos
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    raise SystemExit
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RIGHT:
                        self.selected_index = (self.selected_index + 1) % len(self.robots)
                    elif event.key == pygame.K_LEFT:
                        self.selected_index = (self.selected_index - 1) % len(self.robots)
                    elif event.key == pygame.K_RETURN:
                        return self.robots[self.selected_index][0]  # Nombre del robot

            # Dibujar retratos
            spacing = 100
            start_x = (self.screen.get_width() - (len(self.robots) * spacing)) // 2
            y = self.screen.get_height() // 2

            for i, (name, img) in enumerate(self.robots):
                x = start_x + i * spacing
                rect = img.get_rect(center=(x, y))
                self.screen.blit(img, rect)

                # Marco de selección
                if i == self.selected_index:
                    pygame.draw.rect(self.screen, (255, 255, 0), rect.inflate(10, 10), 3)

                # Nombre
                text_surface = self.font.render(name, True, (255, 255, 255))
                text_rect = text_surface.get_rect(center=(x, y + 50))
                self.screen.blit(text_surface, text_rect)

            pygame.display.flip()
            clock.tick(60)
