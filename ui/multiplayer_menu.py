import pygame
from ui.text_input import TextInput

class MultiplayerMenu:
    def __init__(self, pantalla, font_titulo, font_opcion, font_input):
        self.pantalla = pantalla
        self.font_titulo = font_titulo
        self.font_opcion = font_opcion
        self.font_input = font_input
        self.cursor_actual = None

    def show(self, nombre, personaje):
        opciones_multiplayer = ["Servidor", "Cliente", "Volver"]
        clock = pygame.time.Clock()

        while True:
            self.pantalla.fill((180, 180, 180))
            mouse_pos = pygame.mouse.get_pos()
            cursor_hover = False

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    exit()

                # Solo manejo con mouse, teclas no cambian hover
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for i, rect in enumerate(self.get_option_rects()):
                        if rect.collidepoint(mouse_pos):
                            opcion = opciones_multiplayer[i]
                            if opcion == "Volver":
                                return None
                            elif opcion == "Servidor":
                                from .server_config_menu import server_config_menu
                                return server_config_menu(
                                    self.pantalla, self.font_titulo, self.font_opcion,
                                    self.font_input, nombre, personaje
                                )
                            else:
                                from .client_connect_menu import client_connect_menu
                                return client_connect_menu(
                                    self.pantalla, self.font_titulo, self.font_opcion,
                                    self.font_input, nombre, personaje
                                )

            # Dibujar menú
            self.draw_menu(opciones_multiplayer, mouse_pos)
            pygame.display.flip()
            clock.tick(60)

    def get_option_rects(self):
        rects = []
        y = 200
        for _ in range(3):
            rects.append(pygame.Rect(240, y - 5, 300, 40))
            y += 50
        return rects

    def draw_menu(self, opciones, mouse_pos):
        titulo = self.font_titulo.render("Multijugador", True, (0, 0, 0))
        self.pantalla.blit(titulo, (250, 50))

        y = 200
        for i, opcion in enumerate(opciones):
            rect_hover = pygame.Rect(240, y - 5, 300, 40)
            if rect_hover.collidepoint(mouse_pos):
                pygame.draw.rect(self.pantalla, (255, 0, 0), rect_hover, border_radius=5)
                texto = self.font_opcion.render(opcion, True, (255, 255, 255))
                cursor_hover = True
            else:
                texto = self.font_opcion.render(opcion, True, (0, 0, 0))
            rect_op = texto.get_rect(topleft=(250, y))
            self.pantalla.blit(texto, rect_op)
            y += 50

        # Cambiar cursor
        hover_area = [pygame.Rect(240, 200 + i*50 - 5, 300, 40) for i in range(len(opciones))]
        if any(r.collidepoint(mouse_pos) for r in hover_area):
            if self.cursor_actual != "HAND":
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
                self.cursor_actual = "HAND"
        else:
            if self.cursor_actual != "ARROW":
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
                self.cursor_actual = "ARROW"
