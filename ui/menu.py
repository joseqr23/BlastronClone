import os
import pygame
from ui.text_input import TextInput
from ui.multiplayer_menu import MultiplayerMenu

class Menu:
    def __init__(self, pantalla):
        self.pantalla = pantalla
        self.font_titulo = pygame.font.SysFont("Arial", 40, bold=True)
        self.font_opcion = pygame.font.SysFont("Arial", 35)
        self.font_input = pygame.font.SysFont("Arial", 25)

        self.opciones = ["Modo Solo", "Modo Multijugador", "Modo Libre"]
        self.opcion_seleccionada = 0

        self.text_input = TextInput((320, 153, 270, 35), self.font_input, max_length=29)

        # 🔹 Cargar automáticamente todos los robots que tengan portrait.png
        self.personajes = []
        self.portraits = {}
        robots_path = "assets/robots"

        for carpeta in os.listdir(robots_path):
            portrait_path = os.path.join(robots_path, carpeta, "portrait.png")
            if os.path.isfile(portrait_path):
                self.personajes.append(carpeta)
                img = pygame.image.load(portrait_path).convert_alpha()
                self.portraits[carpeta] = pygame.transform.scale(img, (50, 50))

        self.personaje_idx = 0

        # Rectángulos interactivos
        self.rect_flecha_izq = None
        self.rect_flecha_der = None
        self.rect_opciones = []
        self.cursor_actual = None

    def run(self):
        clock = pygame.time.Clock()
        pygame.key.set_repeat(400, 40)

        while True:
            self.pantalla.fill((200, 200, 200))
            mouse_pos = pygame.mouse.get_pos()
            cursor_hover = False

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    exit()

                self.text_input.handle_event(event)

                # Teclado
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
                        resultado = self.handle_opcion()
                        if resultado:
                            return resultado

                # Mouse
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.rect_flecha_izq and self.rect_flecha_izq.collidepoint(mouse_pos):
                        self.personaje_idx = (self.personaje_idx - 1) % len(self.personajes)
                    elif self.rect_flecha_der and self.rect_flecha_der.collidepoint(mouse_pos):
                        self.personaje_idx = (self.personaje_idx + 1) % len(self.personajes)

                    for i, rect in enumerate(self.rect_opciones):
                        if rect.collidepoint(mouse_pos):
                            self.opcion_seleccionada = i
                            resultado = self.handle_opcion()
                            if resultado:
                                return resultado

            self.text_input.update()
            self.draw_menu(mouse_pos)
            pygame.display.flip()
            clock.tick(60)

    def handle_opcion(self):
        modo = self.opciones[self.opcion_seleccionada]
        nombre = self.text_input.get_text() or "Jugador"
        personaje = self.personajes[self.personaje_idx]

        if modo == "Modo Multijugador":
            # Llamamos al menú modular de multijugador
            multiplayer_menu = MultiplayerMenu(self.pantalla, self.font_titulo, self.font_opcion, self.font_input)
            resultado = multiplayer_menu.show(nombre, personaje)
            # Puede devolver None si el jugador hizo "Volver"
            if resultado is None:
                return self.run()  # vuelve al menú principal
            return resultado
        else:
            return {
                "modo": modo,
                "nombre": nombre,
                "personaje": personaje,
            }
        
    def multiplayer_menu(self, nombre, personaje):
        opciones_multiplayer = ["Servidor", "Cliente", "Volver"]
        seleccion = 0
        clock = pygame.time.Clock()

        while True:
            self.pantalla.fill((180, 180, 180))
            mouse_pos = pygame.mouse.get_pos()
            cursor_hover = False

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    exit()
                # Teclado
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP:
                        seleccion = (seleccion - 1) % len(opciones_multiplayer)
                    elif event.key == pygame.K_DOWN:
                        seleccion = (seleccion + 1) % len(opciones_multiplayer)
                    elif event.key == pygame.K_RETURN:
                        if opciones_multiplayer[seleccion] == "Volver":
                            return None
                        return {
                            "modo": "Multijugador",
                            "tipo": opciones_multiplayer[seleccion],
                            "nombre": nombre,
                            "personaje": personaje
                        }
                # Mouse
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for i, rect in enumerate(self.rect_opciones):
                        if rect.collidepoint(mouse_pos):
                            if opciones_multiplayer[i] == "Volver":
                                return None
                            return {
                                "modo": "Multijugador",
                                "tipo": opciones_multiplayer[i],
                                "nombre": nombre,
                                "personaje": personaje
                            }

            # Dibujo del submenú
            titulo = self.font_titulo.render("Multijugador", True, (0, 0, 0))
            self.pantalla.blit(titulo, (250, 50))

            y = 200
            self.rect_opciones = []
            for i, opcion in enumerate(opciones_multiplayer):
                rect_hover = pygame.Rect(240, y - 5, 300, 40)
                # 🔹 Solo hover con mouse
                if rect_hover.collidepoint(mouse_pos):
                    pygame.draw.rect(self.pantalla, (255, 0, 0), rect_hover, border_radius=5)
                    texto = self.font_opcion.render(opcion, True, (255, 255, 255))
                    cursor_hover = True
                else:
                    texto = self.font_opcion.render(opcion, True, (0, 0, 0))

                rect_op = texto.get_rect(topleft=(250, y))
                self.rect_opciones.append(rect_op)
                self.pantalla.blit(texto, rect_op)
                y += 50

            # Cambiar cursor
            if cursor_hover and self.cursor_actual != "HAND":
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
                self.cursor_actual = "HAND"
            elif not cursor_hover and self.cursor_actual != "ARROW":
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
                self.cursor_actual = "ARROW"

            pygame.display.flip()
            clock.tick(60)

    def draw_menu(self, mouse_pos):
        cursor_hover = False

        # 🔹 Título
        titulo = self.font_titulo.render("Menú Principal", True, (0, 0, 0))
        self.pantalla.blit(titulo, (250, 50))

        # 🔹 Nombre
        etiqueta_nombre = self.font_input.render("Nombre:", True, (0, 0, 0))
        self.pantalla.blit(etiqueta_nombre, (200, 150))
        self.text_input.draw(self.pantalla)

        # 🔹 Personaje + Flechas + Portrait
        texto_personaje = self.font_input.render("Personaje:", True, (0, 0, 0))
        self.pantalla.blit(texto_personaje, (200, 200))

        portrait = self.portraits[self.personajes[self.personaje_idx]]
        portrait_rect = portrait.get_rect()
        portrait_rect.center = (400, 220)

        # Flecha izquierda
        flecha_izq = self.font_input.render("←", True, (0, 0, 0))
        self.rect_flecha_izq = flecha_izq.get_rect(
            topleft=(portrait_rect.left - 30, portrait_rect.centery - flecha_izq.get_height() // 2))
        self.pantalla.blit(flecha_izq, self.rect_flecha_izq)
        if self.rect_flecha_izq.collidepoint(mouse_pos):
            cursor_hover = True

        # Portrait
        self.pantalla.blit(portrait, portrait_rect)

        # Nombre del personaje
        nombre_personaje = self.personajes[self.personaje_idx].title()
        texto_nombre = self.font_input.render(nombre_personaje, True, (0, 0, 0))
        texto_nombre_rect = texto_nombre.get_rect(midleft=(portrait_rect.right + 50, portrait_rect.centery))
        self.pantalla.blit(texto_nombre, texto_nombre_rect)

        # Flecha derecha
        flecha_der = self.font_input.render("→", True, (0, 0, 0))
        self.rect_flecha_der = flecha_der.get_rect(
            topleft=(portrait_rect.right + 10, portrait_rect.centery - flecha_der.get_height() // 2))
        self.pantalla.blit(flecha_der, self.rect_flecha_der)
        if self.rect_flecha_der.collidepoint(mouse_pos):
            cursor_hover = True

        # 🔹 Opciones de menú con hover solo mouse
        self.rect_opciones = []
        y = 300
        for opcion in self.opciones:
            rect_hover = pygame.Rect(240, y - 5, 300, 40)
            if rect_hover.collidepoint(mouse_pos):
                pygame.draw.rect(self.pantalla, (255, 0, 0), rect_hover, border_radius=5)
                texto = self.font_opcion.render(opcion, True, (255, 255, 255))
                cursor_hover = True
            else:
                texto = self.font_opcion.render(opcion, True, (0, 0, 0))

            rect_op = texto.get_rect(topleft=(250, y))
            self.rect_opciones.append(rect_op)
            self.pantalla.blit(texto, rect_op)
            y += 40

        # Cambiar cursor
        if cursor_hover and self.cursor_actual != "HAND":
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
            self.cursor_actual = "HAND"
        elif not cursor_hover and self.cursor_actual != "ARROW":
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
            self.cursor_actual = "ARROW"
