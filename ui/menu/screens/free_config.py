import pygame

from ..theme import *
from ..widgets import MapCarousel


class FreeConfigScreen:
    """Pantalla preparada para añadir más reglas de práctica después."""
    def __init__(self, state, assets, fonts, toast):
        self.state, self.fonts, self.toast = state, fonts, toast
        self.carousel = MapCarousel(assets.mapas, assets.mapa_thumbs, state.libre.mapa_id)
        self.rect_back = self.rect_start = None

    def handle_event(self, event, mouse_pos):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE: return "volver"
            if event.key == pygame.K_RETURN: return "empezar_libre"
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect_back and self.rect_back.collidepoint(mouse_pos): return "volver"
            if self.rect_start and self.rect_start.collidepoint(mouse_pos): return "empezar_libre"
            if self.carousel.handle_click(mouse_pos): self.state.libre.mapa_id = self.carousel.selected_id
        return None

    def draw(self, surface, mouse_pos):
        margin, width = 60, surface.get_width() - 120
        self.rect_back = pygame.Rect(margin, 16, 100, 32); hover = self.rect_back.collidepoint(mouse_pos)
        draw_panel(surface, self.rect_back, COL_OPTION_HOVER if hover else COL_OPTION_IDLE, COL_ACCENT if hover else COL_CARD_BORDER, 8, 2)
        text = self.fonts.config_seccion.render("← Volver", True, COL_TEXT); surface.blit(text, text.get_rect(center=self.rect_back.center))
        surface.blit(self.fonts.config_titulo.render("Modo Libre", True, COL_TEXT), (margin, 54))
        surface.blit(self.fonts.subtitulo.render("Elige el mapa para practicar armas y movimiento", True, COL_TEXT_DIM), (margin + 2, 92))
        pygame.draw.line(surface, COL_CARD_BORDER, (margin, 112), (surface.get_width() - margin, 112), 2)
        maps = pygame.Rect(margin, 132, width, 130)
        hover |= self.carousel.draw(surface, maps, mouse_pos, self.fonts); self.state.libre.mapa_id = self.carousel.selected_id
        self.rect_start = pygame.Rect(0, 0, 300, 48); self.rect_start.center = (surface.get_width() // 2, maps.bottom + 42)
        over = self.rect_start.collidepoint(mouse_pos); hover |= over
        draw_panel(surface, self.rect_start, COL_ACCENT if over else COL_ACCENT_DIM, COL_ACCENT, 14, 2)
        text = self.fonts.config_boton.render("EMPEZAR MODO LIBRE", True, (25, 20, 15)); surface.blit(text, text.get_rect(center=self.rect_start.center))
        self.toast.draw(surface, margin)
        help_text = self.fonts.opcion_desc.render("Esc para volver   •   Enter para empezar", True, COL_TEXT_DIM)
        surface.blit(help_text, help_text.get_rect(midbottom=(surface.get_width() // 2, surface.get_height() - 14)))
        return hover
