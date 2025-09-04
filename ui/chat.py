# core/ui/chat.py
import pygame
import time

class Chat:
    COLORES_NOMBRES = [
        (0, 0, 255),     # Azul
        (0, 200, 0),     # Verde
        (200, 0, 0),     # Rojo
        (255, 140, 0),   # Naranja
        (128, 0, 128),   # Morado
    ]

    def __init__(self, nombre_jugador, game=None, posicion=(10, 410), ancho=300, alto=80):
        self.nombre_jugador = nombre_jugador
        self.game = game 
        self.posicion = posicion
        self.ancho = ancho
        self.alto = alto
        self.mensajes = []
        self.font = pygame.font.SysFont("Arial", 16)
        self.color_fondo = (0, 0, 0, 150)
        self.color_texto = (255, 255, 255)
        self.color_nombre = self.COLORES_NOMBRES[hash(nombre_jugador) % len(self.COLORES_NOMBRES)]
        self.input_text = ""
        self.activo = False
        self.scroll_offset = 0
        self.cursor_visible = True
        self.last_cursor_toggle = pygame.time.get_ticks()
        self.cursor_interval = 500  # milisegundos

    def agregar_mensaje(self, texto):
        self.mensajes.append(texto)
        self.scroll_offset = 0

    def lineas_visibles(self):
        return (self.alto - 25) // 18

    def draw(self, pantalla):
        # Fondo
        surface = pygame.Surface((self.ancho, self.alto), pygame.SRCALPHA)
        surface.fill(self.color_fondo)
        pantalla.blit(surface, self.posicion)

        # Mensajes visibles según scroll
        max_lineas = self.lineas_visibles()
        inicio = max(0, len(self.mensajes) - max_lineas - self.scroll_offset)
        fin = inicio + max_lineas
        mensajes_a_mostrar = self.mensajes[inicio:fin]

        y_offset = 5
        for mensaje in mensajes_a_mostrar:
            if ": " in mensaje:
                nombre, texto = mensaje.split(": ", 1)
                color_nombre = self.COLORES_NOMBRES[hash(nombre) % len(self.COLORES_NOMBRES)]
                render_nombre = self.font.render(nombre + ": ", True, color_nombre)
                pantalla.blit(render_nombre, (self.posicion[0] + 5, self.posicion[1] + y_offset))

                render_texto = self.font.render(texto, True, self.color_texto)
                pantalla.blit(render_texto, (self.posicion[0] + 5 + render_nombre.get_width(), self.posicion[1] + y_offset))
            else:
                render = self.font.render(mensaje, True, self.color_texto)
                pantalla.blit(render, (self.posicion[0] + 5, self.posicion[1] + y_offset))
            y_offset += 18

        # Barra de scroll
        total_mensajes = len(self.mensajes)
        if total_mensajes > max_lineas:
            barra_altura = int((max_lineas / total_mensajes) * (self.alto - 25))
            barra_altura = max(10, barra_altura)
            max_offset = total_mensajes - max_lineas
            posicion_barra = int((self.scroll_offset / max_offset) * (self.alto - 25 - barra_altura)) if max_offset > 0 else 0

            pygame.draw.rect(
                pantalla,
                (150, 150, 150),
                (
                    self.posicion[0] + self.ancho - 6,
                    self.posicion[1] + 5 + posicion_barra,
                    4,
                    barra_altura
                )
            )

        # Línea de entrada con cursor parpadeante
        if self.activo:
            ahora = pygame.time.get_ticks()
            if ahora - self.last_cursor_toggle >= self.cursor_interval:
                self.cursor_visible = not self.cursor_visible
                self.last_cursor_toggle = ahora

            texto_mostrar = "Decir: " + self.input_text
            if self.cursor_visible:
                texto_mostrar += "|"
            input_render = self.font.render(texto_mostrar, True, self.color_texto)
            pantalla.blit(input_render, (self.posicion[0] + 5, self.posicion[1] + self.alto - 20))

    def handle_event(self, evento):
        if evento.type == pygame.KEYDOWN:
            if evento.key == pygame.K_RETURN:
                if self.activo:
                    if self.input_text.strip():
                        mensaje_formateado = f"{self.nombre_jugador}: {self.input_text.strip()}"
                        self.agregar_mensaje(mensaje_formateado)
                        # 🔥 enviar al resto
                        if hasattr(self, "game"):
                            self.game.enviar_chat(mensaje_formateado)
                    self.input_text = ""
                    self.activo = False
                else:
                    self.activo = True
            elif self.activo:
                if evento.key == pygame.K_BACKSPACE:
                    self.input_text = self.input_text[:-1]
                else:
                    if evento.unicode.isprintable():
                        self.input_text += evento.unicode
            else:
                if evento.key == pygame.K_PAGEUP:
                    self.scroll_offset = min(self.scroll_offset + 1, max(0, len(self.mensajes) - self.lineas_visibles()))
                elif evento.key == pygame.K_PAGEDOWN:
                    self.scroll_offset = max(self.scroll_offset - 1, 0)

        elif evento.type == pygame.MOUSEBUTTONDOWN and not self.activo:
            if evento.button == 4:
                self.scroll_offset = min(self.scroll_offset + 1, max(0, len(self.mensajes) - self.lineas_visibles()))
            elif evento.button == 5:
                self.scroll_offset = max(self.scroll_offset - 1, 0)
