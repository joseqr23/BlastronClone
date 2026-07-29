# core/ui/chat.py
from utils.colors import ColorManager
import pygame
import time

# Misma paleta de acento (dorado) que se usó en el HUD de armas, para que
# los widgets en pantalla se vean consistentes entre sí.
COL_PANEL_FONDO = (14, 14, 18, 200)
COL_PANEL_BORDE_ACTIVO = (255, 196, 60)
COL_PANEL_BORDE_INACTIVO = (90, 90, 100)
COL_DIVISOR = (60, 60, 68)
COL_INPUT_FONDO_ACTIVO = (40, 34, 18, 220)
COL_TEXTO = (235, 235, 235)
COL_HINT = (150, 150, 150)
COL_SCROLLBAR = (255, 196, 60, 200)
COL_SCROLLBAR_RIEL = (255, 255, 255, 25)


class Chat:
    COLORES_NOMBRES = [
        (0, 0, 255),     # Azul
        (0, 200, 0),     # Verde
        (200, 0, 0),     # Rojo
        (255, 140, 0),   # Naranja
        (128, 0, 128),   # Morado
        (255, 255, 0),   # Amarillo (extra)
        (0, 255, 255),   # Cyan (extra)
        (255, 0, 255),   # Fucsia (extra)
    ]

    def __init__(self, nombre_jugador, game=None, robot_local=None, posicion=(10, 410), ancho=300, alto=80):
        self.nombre_jugador = nombre_jugador
        self.game = game
        self.posicion = posicion
        self.ancho = ancho
        self.alto = alto
        self.mensajes = []
        self.font = pygame.font.SysFont("Arial", 16)
        self.font_hint = pygame.font.SysFont("Arial", 13)
        self.color_fondo = (0, 0, 0, 150)
        self.color_texto = COL_TEXTO
        self.color_nombre = ColorManager.get_color(self.nombre_jugador)
        self.input_text = ""
        self.activo = False
        self.scroll_offset = 0
        self.cursor_visible = True
        self.last_cursor_toggle = pygame.time.get_ticks()
        self.cursor_interval = 500  # milisegundos
        self.robot_local = robot_local
        self.colapsado = True  # oculto por defecto — se muestra con la tecla C

    def agregar_mensaje(self, texto):
        self.mensajes.append(texto)
        self.scroll_offset = 0

    def lineas_visibles(self):
        return (self.alto - 25) // 18

    # ------------------------------------------------------------------
    # Dibujo
    # ------------------------------------------------------------------
    def draw(self, pantalla):
        x, y = self.posicion
        if self.colapsado:
            hint = self.font_hint.render("Chat (C)", True, COL_HINT)
            fondo_hint = pygame.Surface((hint.get_width() + 16, hint.get_height() + 8), pygame.SRCALPHA)
            pygame.draw.rect(fondo_hint, COL_PANEL_FONDO, fondo_hint.get_rect(), border_radius=6)
            pantalla.blit(fondo_hint, (x, y))
            pantalla.blit(hint, (x + 8, y + 4))
            return
        alto_input = 24
        rect_panel = pygame.Rect(x, y, self.ancho, self.alto)
        rect_input = pygame.Rect(x, y + self.alto - alto_input, self.ancho, alto_input)

        # Panel de fondo, redondeado, con borde dorado cuando el chat
        # está activo (escribiendo) y borde apagado cuando no — mismo
        # lenguaje visual que el resto del HUD.
        fondo = pygame.Surface((self.ancho, self.alto), pygame.SRCALPHA)
        pygame.draw.rect(fondo, COL_PANEL_FONDO, fondo.get_rect(), border_radius=8)
        pantalla.blit(fondo, (x, y))
        borde = COL_PANEL_BORDE_ACTIVO if self.activo else COL_PANEL_BORDE_INACTIVO
        pygame.draw.rect(pantalla, borde, rect_panel, width=2, border_radius=8)

        # Mensajes visibles según scroll
        max_lineas = self.lineas_visibles()
        inicio = max(0, len(self.mensajes) - max_lineas - self.scroll_offset)
        fin = inicio + max_lineas
        mensajes_a_mostrar = self.mensajes[inicio:fin]
        y_offset = 7
        for mensaje in mensajes_a_mostrar:
            if ": " in mensaje:
                nombre, texto = mensaje.split(": ", 1)
                color_nombre = ColorManager.get_color(nombre)
                render_nombre = self.font.render(nombre + ": ", True, color_nombre)
                pantalla.blit(render_nombre, (x + 8, y + y_offset))
                render_texto = self.font.render(texto, True, self.color_texto)
                pantalla.blit(render_texto, (x + 8 + render_nombre.get_width(), y + y_offset))
            else:
                render = self.font.render(mensaje, True, self.color_texto)
                pantalla.blit(render, (x + 8, y + y_offset))
            y_offset += 18

        # Barra de scroll — riel tenue + barra dorada, con bordes redondeados.
        total_mensajes = len(self.mensajes)
        area_mensajes_alto = self.alto - alto_input - 8
        if total_mensajes > max_lineas:
            riel_rect = pygame.Rect(x + self.ancho - 8, y + 4, 4, area_mensajes_alto)
            riel = pygame.Surface(riel_rect.size, pygame.SRCALPHA)
            riel.fill(COL_SCROLLBAR_RIEL)
            pantalla.blit(riel, riel_rect.topleft)

            barra_altura = max(10, int((max_lineas / total_mensajes) * area_mensajes_alto))
            max_offset = total_mensajes - max_lineas
            posicion_barra = int((self.scroll_offset / max_offset) * (area_mensajes_alto - barra_altura)) if max_offset > 0 else 0
            barra_rect = pygame.Rect(riel_rect.x, riel_rect.y + posicion_barra, 4, barra_altura)
            barra = pygame.Surface(barra_rect.size, pygame.SRCALPHA)
            barra.fill(COL_SCROLLBAR)
            pantalla.blit(barra, barra_rect.topleft)

        # Divisor entre los mensajes y la línea de entrada.
        pygame.draw.line(pantalla, COL_DIVISOR, (x + 6, rect_input.top), (x + self.ancho - 6, rect_input.top), 1)

        # Línea de entrada: franja propia, resaltada solo cuando se está
        # escribiendo, con cursor parpadeante. Cuando no está activa se
        # muestra un hint apagado para que se sepa cómo abrir el chat.
        if self.activo:
            franja = pygame.Surface((self.ancho - 4, alto_input - 2), pygame.SRCALPHA)
            pygame.draw.rect(franja, COL_INPUT_FONDO_ACTIVO, franja.get_rect(), border_radius=6)
            pantalla.blit(franja, (x + 2, rect_input.top + 1))

            ahora = pygame.time.get_ticks()
            if ahora - self.last_cursor_toggle >= self.cursor_interval:
                self.cursor_visible = not self.cursor_visible
                self.last_cursor_toggle = ahora
            texto_mostrar = "> " + self.input_text
            if self.cursor_visible:
                texto_mostrar += "|"
            input_render = self.font.render(texto_mostrar, True, COL_TEXTO)
            pantalla.blit(input_render, (x + 8, rect_input.top + 3))
        else:
            hint_render = self.font_hint.render("Enter para chatear | Cerrar (C)", True, COL_HINT)
            pantalla.blit(hint_render, (x + 8, rect_input.top + 5))

    def handle_event(self, evento):
        if evento.type == pygame.KEYDOWN:
            if not self.activo and evento.key == pygame.K_c:
                self.colapsado = not self.colapsado
                return
            if evento.key == pygame.K_RETURN:
                if self.activo:
                    if self.input_text.strip():
                        mensaje_formateado = f"{self.nombre_jugador}: {self.input_text.strip()}"
                        self.agregar_mensaje(mensaje_formateado)
                        if self.robot_local is not None:
                            self.robot_local.mostrar_mensaje(self.input_text.strip())
                        if self.game is not None:
                            self.game.enviar_chat(mensaje_formateado)
                    self.input_text = ""
                    self.activo = False
                else:
                    self.activo = True
                    self.colapsado = False  # se muestra solo para poder ver lo que escribís
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