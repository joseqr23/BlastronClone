import pygame
from ui.text_input import TextInput

class Menu:
    def __init__(self, pantalla):
        self.pantalla = pantalla
        self.font_titulo = pygame.font.SysFont("Arial", 40, bold=True)
        self.font_opcion = pygame.font.SysFont("Arial", 28)
        self.font_input = pygame.font.SysFont("Arial", 24)

        self.opciones = ["Modo Solo", "Modo Multijugador", "Modo Libre"]
        self.opcion_seleccionada = 0

        self.text_input = TextInput((320, 145, 250, 35), self.font_input, max_length=22)
        self.personajes = ["robot", "netali_sprites", "robot_sprites"]
        self.personaje_idx = 0

    def run(self):
        clock = pygame.time.Clock()
        pygame.key.set_repeat(400, 40)

        while True:
            self.pantalla.fill((200, 200, 200))

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    exit()

                self.text_input.handle_event(event)

                if event.type == pygame.KEYDOWN and not self.text_input.active:
                    if event.key == pygame.K_UP:
                        self.opcion_seleccionada = (self.opcion_seleccionada - 1) % len(self.opciones)
                    elif event.key == pygame.K_DOWN:
                        self.opcion_seleccionada = (self.opcion_seleccionada + 1) % len(self.opciones)
                    elif event.key == pygame.K_LEFT:
                        self.personaje_idx = (self.personaje_idx - 1) % len(self.personajes)
                    elif event.key == pygame.K_RIGHT:
                        self.personaje_idx = (self.personaje_idx + 1) % len(self.personajes)
                    elif event.key == pygame.K_RETURN:
                        return {
                            "modo": self.opciones[self.opcion_seleccionada],
                            "nombre": self.text_input.get_text() or "Jugador",
                            "personaje": self.personajes[self.personaje_idx],
                        }

            self.text_input.update()

            titulo = self.font_titulo.render("Menú Principal", True, (0, 0, 0))
            self.pantalla.blit(titulo, (250, 50))

            etiqueta_nombre = self.font_input.render("Nombre:", True, (0, 0, 0))
            self.pantalla.blit(etiqueta_nombre, (200, 150))

            self.text_input.draw(self.pantalla)

            personaje_texto = self.font_input.render(
                f"Personaje: {self.personajes[self.personaje_idx]}  ← →", True, (0, 0, 0)
            )
            self.pantalla.blit(personaje_texto, (200, 200))

            y = 300
            for i, opcion in enumerate(self.opciones):
                color = (255, 0, 0) if i == self.opcion_seleccionada else (0, 0, 0)
                texto = self.font_opcion.render(opcion, True, color)
                self.pantalla.blit(texto, (250, y))
                y += 40

            pygame.display.flip()
            clock.tick(60)
