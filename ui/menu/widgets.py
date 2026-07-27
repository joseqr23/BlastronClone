import pygame

from .theme import *


def draw_text_input_contents(surface, text_input):
    """Dibuja TextInput usando el estilo del menú, sin dibujar otro fondo."""
    left = text_input.rect.x + text_input.PADDING_X
    top = text_input.rect.y + (text_input.rect.height - text_input.font.get_height()) // 2
    sel_i, sel_j = text_input._sel_bounds()
    if text_input._has_selection():
        pre_w = text_input.font.size(text_input.text[:sel_i])[0]
        sel_w = text_input.font.size(text_input.text[sel_i:sel_j])[0]
        sel_rect = pygame.Rect(left + pre_w, top, sel_w, text_input.font.get_height())
        sel_rect.width = min(sel_rect.width, text_input.rect.right - sel_rect.x - 3)
        pygame.draw.rect(surface, text_input.color_sel_bg, sel_rect)
    surface.blit(text_input.font.render(text_input.text, True, COL_TEXT), (left, top))
    if text_input.active and (text_input.cursor_visible or text_input._has_selection()):
        caret_x = left + text_input.font.size(text_input.text[:text_input.caret_pos])[0]
        pygame.draw.line(surface, COL_ACCENT, (caret_x, top), (caret_x, top + text_input.font.get_height()), 2)


def draw_input(surface, text_input):
    text_input.color_border = COL_INPUT_BORDER_ACTIVE if text_input.active else COL_INPUT_BORDER
    pygame.draw.rect(surface, COL_INPUT_BG, text_input.rect, border_radius=8)
    pygame.draw.rect(surface, text_input.color_border, text_input.rect, width=2, border_radius=8)
    draw_text_input_contents(surface, text_input)


class Toast:
    def __init__(self):
        self.texto = None
        self.started_at = 0

    def show(self, texto):
        self.texto = texto
        self.started_at = pygame.time.get_ticks()

    def draw(self, surface, x):
        if not self.texto:
            return
        elapsed = pygame.time.get_ticks() - self.started_at
        if elapsed >= 2200:
            self.texto = None
            return
        alpha = 255 if elapsed < 1800 else max(0, 255 - int((elapsed - 1800) / 400 * 255))
        font = pygame.font.SysFont("Arial", 13)
        aviso = font.render(self.texto, True, (255, 210, 150))
        caja = pygame.Surface((aviso.get_width() + 24, aviso.get_height() + 14), pygame.SRCALPHA)
        pygame.draw.rect(caja, (60, 40, 20, min(230, alpha)), caja.get_rect(), border_radius=8)
        caja.blit(aviso, (12, 7))
        caja.set_alpha(alpha)
        surface.blit(caja, (x, surface.get_height() - 40))


class MapCarousel:
    """Selector compartido por Host y Modo Libre."""
    def __init__(self, mapas, thumbs, selected_id=None):
        self.mapas, self.thumbs = mapas, thumbs
        self.selected_id = selected_id or (mapas[0][0] if mapas else None)
        self.offset = 0
        self.rect_items = {}
        self.rect_left = self.rect_right = None
        self.items_per_page = 1
        self.max_offset = 0

    def handle_click(self, mouse_pos):
        if self.rect_left and self.rect_left.collidepoint(mouse_pos):
            self.offset = max(0, self.offset - self.items_per_page)
            return True
        if self.rect_right and self.rect_right.collidepoint(mouse_pos):
            self.offset = min(self.max_offset, self.offset + self.items_per_page)
            return True
        for mapa_id, rect in self.rect_items.items():
            if rect.collidepoint(mouse_pos):
                self.selected_id = mapa_id
                return True
        return False

    def draw(self, surface, rect, mouse_pos, fonts):
        draw_panel(surface, rect)
        surface.blit(fonts.config_seccion.render("MAPA", True, COL_TEXT_DIM), (rect.x + 24, rect.y + 10))
        self.rect_items, self.rect_left, self.rect_right = {}, None, None
        thumb_w, thumb_h, gap, arrow_w = 90, 56, 14, 28
        left, right, y = rect.x + 24, rect.right - 24, rect.y + 34
        raw_capacity = max(1, (right - left) // (thumb_w + gap))
        arrows = len(self.mapas) > raw_capacity
        self.items_per_page = max(1, ((right - left) - 2 * (arrow_w + 12)) // (thumb_w + gap)) if arrows else raw_capacity
        self.max_offset = max(0, len(self.mapas) - self.items_per_page)
        self.offset = max(0, min(self.offset, self.max_offset))
        x = left + (arrow_w + 12 if arrows else 0)
        hover = False
        for mapa_id, nombre, _ in self.mapas[self.offset:self.offset + self.items_per_page]:
            thumb_rect = pygame.Rect(x, y, thumb_w, thumb_h)
            over = thumb_rect.collidepoint(mouse_pos)
            pygame.draw.rect(surface, COL_INPUT_BG, thumb_rect, border_radius=8)
            if self.thumbs.get(mapa_id):
                surface.blit(self.thumbs[mapa_id], self.thumbs[mapa_id].get_rect(center=thumb_rect.center))
            pygame.draw.rect(surface, COL_ACCENT if mapa_id == self.selected_id else (COL_ACCENT_DIM if over else COL_CARD_BORDER), thumb_rect, 2, border_radius=8)
            label = fonts.opcion_desc.render(nombre, True, COL_TEXT if mapa_id == self.selected_id else COL_TEXT_DIM)
            surface.blit(label, label.get_rect(midtop=(thumb_rect.centerx, thumb_rect.bottom + 4)))
            self.rect_items[mapa_id] = pygame.Rect(x, y, thumb_w, thumb_h + 18)
            hover |= over
            x += thumb_w + gap
        if arrows:
            cy = y + thumb_h // 2
            self.rect_left = pygame.Rect(left, cy - 14, arrow_w, 28) if self.offset > 0 else None
            self.rect_right = pygame.Rect(right - arrow_w, cy - 14, arrow_w, 28) if self.offset < self.max_offset else None
            for button, symbol in ((self.rect_left, "<"), (self.rect_right, ">")):
                if not button: continue
                over = button.collidepoint(mouse_pos)
                draw_panel(surface, button, COL_OPTION_HOVER if over else COL_INPUT_BG, COL_ACCENT if over else COL_INPUT_BORDER, 6, 2)
                surface.blit(fonts.flecha.render(symbol, True, COL_TEXT), fonts.flecha.render(symbol, True, COL_TEXT).get_rect(center=button.center))
                hover |= over
        return hover
