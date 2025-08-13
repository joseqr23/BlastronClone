import pygame

class Menu:
    def __init__(self, pantalla):
        self.pantalla = pantalla
        self.font_titulo = pygame.font.SysFont("Arial", 40, bold=True)
        self.font_opcion = pygame.font.SysFont("Arial", 28)
        self.font_input = pygame.font.SysFont("Arial", 24)

        self.opciones = ["Modo Solo", "Modo Multijugador", "Modo Libre"]
        self.opcion_seleccionada = 0
        self.nombre = ""
        self.introduciendo_nombre = True

        self.personajes = ["robot", "netali_sprites", "robot_sprites"]
        self.personaje_idx = 0

    def run(self):
        clock = pygame.time.Clock()
        while True:
            self.pantalla.fill((200, 200, 200))

            # --- Eventos ---
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    exit()

                if event.type == pygame.KEYDOWN:
                    if self.introduciendo_nombre:
                        if event.key == pygame.K_RETURN:
                            self.introduciendo_nombre = False
                        elif event.key == pygame.K_BACKSPACE:
                            self.nombre = self.nombre[:-1]
                        else:
                            if len(self.nombre) < 12 and event.unicode.isprintable():
                                self.nombre += event.unicode
                    else:
                        if event.key == pygame.K_UP:
                            self.opcion_seleccionada = (self.opcion_seleccionada - 1) % len(self.opciones)
                        elif event.key == pygame.K_DOWN:
                            self.opcion_seleccionada = (self.opcion_seleccionada + 1) % len(self.opciones)
                        elif event.key == pygame.K_LEFT:
                            self.personaje_idx = (self.personaje_idx - 1) % len(self.personajes)
                        elif event.key == pygame.K_RIGHT:
                            self.personaje_idx = (self.personaje_idx + 1) % len(self.personajes)
                        elif event.key == pygame.K_RETURN:
                            # Devuelve datos seleccionados
                            return {
                                "modo": self.opciones[self.opcion_seleccionada],
                                "nombre": self.nombre if self.nombre.strip() else "Jugador",
                                "personaje": self.personajes[self.personaje_idx]
                            }

            # --- Render ---
            titulo = self.font_titulo.render("Menú Principal", True, (0, 0, 0))
            self.pantalla.blit(titulo, (250, 50))

            # Campo nombre
            nombre_texto = self.font_input.render(f"Nombre: {self.nombre}", True, (0, 0, 255))
            self.pantalla.blit(nombre_texto, (200, 150))

            # Selector personaje
            personaje_texto = self.font_input.render(
                f"Personaje: {self.personajes[self.personaje_idx]}  ← →", True, (0, 0, 0)
            )
            self.pantalla.blit(personaje_texto, (200, 200))

            # Opciones
            y = 300
            for i, opcion in enumerate(self.opciones):
                color = (255, 0, 0) if i == self.opcion_seleccionada else (0, 0, 0)
                texto = self.font_opcion.render(opcion, True, color)
                self.pantalla.blit(texto, (250, y))
                y += 40

            pygame.display.flip()
            clock.tick(60)
