# ui/multiplayer_lobby/widgets.py
import pygame


class LobbyConfigWidgets:
    """Controles del Host. El carrusel muestra cualquier cantidad de mapas."""
    DURACIONES = (3, 5, 10)
    MODOS = (("best_of_three", "Mejor de 3"), ("libre", "Libre"), ("lms", "Last man standing"), ("muertes", "Muertes"), ("puntos", "Puntos"))

    def __init__(self, assets):
        self.assets = assets
        self.offset = 0
        self.visible_count = 1
        self.map_rects = {}
        self.duration_rects = {}
        self.mode_rects = {}
        self.left_rect = self.right_rect = None

    def handle_click(self, position, config):
        if self.left_rect and self.left_rect.collidepoint(position):
            self.offset = max(0, self.offset - self.visible_count)
            return None
        if self.right_rect and self.right_rect.collidepoint(position):
            self.offset = min(max(0, len(self.assets.mapas) - self.visible_count), self.offset + self.visible_count)
            return None
        for mapa_id, rect in self.map_rects.items():
            if rect.collidepoint(position):
                return {"mapa_id": mapa_id}
        for duration, rect in self.duration_rects.items():
            if rect.collidepoint(position):
                return {"duracion_min": duration}
        for mode, rect in self.mode_rects.items():
            if rect.collidepoint(position):
                return {"modo_partida": mode}
        return None

    def draw(self, surface, rect, config, editable):
        title_font = pygame.font.SysFont("Arial", 15, bold=True)
        text_font = pygame.font.SysFont("Arial", 13)
        small_font = pygame.font.SysFont("Arial", 11)
        pygame.draw.rect(surface, (38, 44, 59), rect, border_radius=12)
        pygame.draw.rect(surface, (255, 140, 0) if editable else (72, 82, 106), rect, width=2, border_radius=12)
        surface.blit(title_font.render("CONFIGURACIÓN", True, (240, 240, 245)), (rect.x + 14, rect.y + 12))
 
        # Layout vertical de las 3 secciones (mapa / tiempo / modo) con
        # separación PROPORCIONAL al espacio real del panel, en vez de
        # offsets fijos en píxeles — antes quedaban pegadas arriba y todo
        # el espacio sobrante del panel se acumulaba sin usar, al final.
        map_h, duration_h, mode_h = 88, 34, 34
        content_top = rect.y + 40
        content_bottom = rect.bottom - 18
 
        alto_fijo = map_h + duration_h + mode_h
        espacio_libre = max(0, (content_bottom - content_top) - alto_fijo)
        gap = max(18, espacio_libre // 3)  # 2 separaciones internas + margen inferior
 
        map_y = content_top
        duration_y = map_y + map_h + gap
        mode_y = duration_y + duration_h + gap
 
        self._draw_map_carousel(
            surface, pygame.Rect(rect.x + 12, map_y, rect.width - 24, map_h),
            config, title_font, text_font, small_font
        )
        self._draw_duration(
            surface, pygame.Rect(rect.x + 14, duration_y, rect.width - 28, duration_h),
            config, text_font
        )
        self._draw_modes(
            surface, pygame.Rect(rect.x + 14, mode_y, rect.width - 28, mode_h),
            config, text_font
        )
 
        if not editable:
            overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
            overlay.fill((15, 18, 25, 105))
            surface.blit(overlay, rect.topleft)
            message = text_font.render("El Host configura la partida", True, (235, 235, 240))
            surface.blit(message, message.get_rect(midbottom=(rect.centerx, rect.bottom - 12)))

    def _draw_map_carousel(self, surface, rect, config, title_font, text_font, small_font):
        self.map_rects = {}
        maps = self.assets.mapas
        if not maps:
            surface.blit(text_font.render("No hay mapas disponibles", True, (210, 130, 120)), (rect.x, rect.y + 30))
            return
 
        surface.blit(text_font.render("MAPA", True, (174, 183, 202)), (rect.x, rect.y + 3))
        arrow_size, item_w, item_h, gap = 26, 78, 65, 8
        first_x = rect.x + 34
        usable_w = rect.right - 34 - first_x
        self.visible_count = max(1, usable_w // (item_w + gap))
        max_offset = max(0, len(maps) - self.visible_count)
        self.offset = min(self.offset, max_offset)
        self.left_rect = pygame.Rect(rect.x, rect.y + 29, arrow_size, arrow_size) if self.offset > 0 else None
        self.right_rect = pygame.Rect(rect.right - arrow_size, rect.y + 29, arrow_size, arrow_size) if self.offset < max_offset else None
 
        for button, symbol in ((self.left_rect, "<"), (self.right_rect, ">")):
            if not button:
                continue
            pygame.draw.rect(surface, (54, 63, 84), button, border_radius=6)
            pygame.draw.rect(surface, (115, 130, 165), button, width=1, border_radius=6)
            rendered = title_font.render(symbol, True, (245, 245, 250))
            surface.blit(rendered, rendered.get_rect(center=button.center))
 
        visibles = maps[self.offset:self.offset + self.visible_count]
        # Centra el grupo de miniaturas visibles dentro del espacio
        # reservado (usable_w), en vez de pegarlas a la izquierda — así
        # no queda un hueco muerto entre la última miniatura y la flecha
        # derecha cuando el ancho disponible no es múltiplo exacto de
        # (item_w + gap). Con el carrusel lleno (todos los mapas caben a
        # la vez) esto además centra el conjunto completo, en vez de
        # dejarlo desalineado hacia la izquierda.
        fila_w = len(visibles) * item_w + max(0, len(visibles) - 1) * gap
        x = first_x + max(0, (usable_w - fila_w) // 2)
 
        for mapa_id, nombre, _ in visibles:
            item = pygame.Rect(x, rect.y + 20, item_w, item_h)
            self.map_rects[mapa_id] = item
            active = mapa_id == config.mapa_id
            pygame.draw.rect(surface, (25, 30, 42), item, border_radius=7)
            thumb = self.assets.map_thumbs.get(mapa_id)
            if thumb:
                image = pygame.transform.smoothscale(thumb, (item_w - 6, 43))
                surface.blit(image, image.get_rect(midtop=(item.centerx, item.y + 3)))
            pygame.draw.rect(surface, (255, 140, 0) if active else (84, 94, 120), item, width=2, border_radius=7)
            label = self._fit_text(small_font, nombre, item.width - 2)
            surface.blit(label, label.get_rect(midtop=(item.centerx, item.bottom + 3)))
            x += item_w + gap

    def _draw_duration(self, surface, rect, config, font):
        self.duration_rects = {}
        surface.blit(font.render("TIEMPO", True, (174, 183, 202)), (rect.x, rect.y + 8))
        x = rect.x + 62
        for duration in self.DURACIONES:
            button = pygame.Rect(x, rect.y, 58, 31)
            self.duration_rects[duration] = button
            self._button(surface, button, f"{duration} min", duration == config.duracion_min, font)
            x += 65

    def _draw_modes(self, surface, rect, config, font):
        self.mode_rects = {}
        surface.blit(font.render("MODO", True, (174, 183, 202)), (rect.x, rect.y + 8))
        x = rect.x + 52
        available = rect.right - x - 14
        n = len(self.MODOS)
        gap = 7
        ancho_boton = max(58, (available - gap * (n - 1)) // n)
        for mode, label in self.MODOS:
            button = pygame.Rect(x, rect.y, ancho_boton, 31)
            self.mode_rects[mode] = button
            self._button(surface, button, label, mode == config.modo_partida, font)
            x += ancho_boton + gap

    @staticmethod
    def _button(surface, rect, label, active, font):
        pygame.draw.rect(surface, (155, 87, 28) if active else (54, 63, 84), rect, border_radius=7)
        pygame.draw.rect(surface, (220, 135, 55) if active else (84, 94, 120), rect, width=1, border_radius=7)
        text = font.render(label, True, (255, 255, 255))
        surface.blit(text, text.get_rect(center=rect.center))

    @staticmethod
    def _fit_text(font, value, max_width):
        text = str(value)
        while len(text) > 1 and font.size(text)[0] > max_width:
            text = text[:-2] + "…"
        return font.render(text, True, (225, 230, 240))
