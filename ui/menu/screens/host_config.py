# ui/menu/screens/host_config.py

import pygame

from ..theme import *
from ..widgets import MapCarousel


class HostConfigScreen:
    DURACIONES = (3, 5, 10)
    MODOS = (("puntos", "POR PUNTOS", True), ("muertes", "POR MUERTES", True), ("lms", "LAST MAN STANDING", True))

    def __init__(self, state, assets, fonts, toast):
        self.state, self.fonts, self.toast = state, fonts, toast
        self.carousel = MapCarousel(assets.mapas, assets.mapa_thumbs, state.host.mapa_id)
        self.rect_back = self.rect_start = None
        self.rect_duration, self.rect_mode = {}, {}

    def handle_event(self, event, mouse_pos):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE: return "volver"
            if event.key == pygame.K_RETURN: return "empezar_host"
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect_back and self.rect_back.collidepoint(mouse_pos): return "volver"
            if self.rect_start and self.rect_start.collidepoint(mouse_pos): return "empezar_host"
            if self.carousel.handle_click(mouse_pos): self.state.host.mapa_id = self.carousel.selected_id
            for dur, rect in self.rect_duration.items():
                if rect.collidepoint(mouse_pos): self.state.host.duracion_min = dur
            for key, rect in self.rect_mode.items():
                if rect.collidepoint(mouse_pos): self.state.host.modo_partida = key
        return None

    def draw(self, surface, mouse_pos):
        margin, width = 60, surface.get_width() - 120; hover = False
        self.rect_back = pygame.Rect(margin, 16, 100, 32); over = self.rect_back.collidepoint(mouse_pos); hover |= over
        draw_panel(surface, self.rect_back, COL_OPTION_HOVER if over else COL_OPTION_IDLE, COL_ACCENT if over else COL_CARD_BORDER, 8, 2)
        text = self.fonts.config_seccion.render("← Volver", True, COL_TEXT); surface.blit(text, text.get_rect(center=self.rect_back.center))
        surface.blit(self.fonts.config_titulo.render("Configuración del Host", True, COL_TEXT), (margin, 54))
        surface.blit(self.fonts.subtitulo.render("Define cómo se jugará esta partida", True, COL_TEXT_DIM), (margin + 2, 92))
        pygame.draw.line(surface, COL_CARD_BORDER, (margin, 112), (surface.get_width() - margin, 112), 2)
        tiempo = pygame.Rect(margin, 122, width, 84); draw_panel(surface, tiempo)
        surface.blit(self.fonts.config_seccion.render("TIEMPO DE PARTIDA", True, COL_TEXT_DIM), (tiempo.x + 24, tiempo.y + 10))
        self.rect_duration = {}; x = tiempo.x + 24
        for dur in self.DURACIONES:
            rect = pygame.Rect(x, tiempo.y + 36, 120, 40); self.rect_duration[dur] = rect
            active, over = dur == self.state.host.duracion_min, rect.collidepoint(mouse_pos); hover |= over
            draw_panel(surface, rect, COL_OPTION_SELECTED if active else (COL_OPTION_HOVER if over else COL_OPTION_IDLE), COL_ACCENT if active else (COL_ACCENT_DIM if over else COL_CARD_BORDER), 10, 2 if active or over else 1)
            text = self.fonts.config_boton.render(f"{dur} MIN", True, COL_TEXT if active or over else COL_TEXT_DIM); surface.blit(text, text.get_rect(center=rect.center)); x += 134
        modes = pygame.Rect(margin, tiempo.bottom + 8, width, 98); draw_panel(surface, modes)
        surface.blit(self.fonts.config_seccion.render("MODO DE JUEGO", True, COL_TEXT_DIM), (modes.x + 24, modes.y + 10))
        self.rect_mode = {}; card_w = (width - 48 - 32) // 3; x = modes.x + 24
        for key, label, enabled in self.MODOS:
            rect = pygame.Rect(x, modes.y + 34, card_w, 56); self.rect_mode[key] = rect
            active, over = key == self.state.host.modo_partida, rect.collidepoint(mouse_pos); hover |= over
            draw_panel(surface, rect, COL_OPTION_SELECTED if active else (COL_OPTION_HOVER if over else COL_OPTION_IDLE), COL_ACCENT if active else (COL_ACCENT_DIM if over else COL_CARD_BORDER), 10, 2 if active or over else 1)
            text = self.fonts.opcion_desc.render(label, True, COL_TEXT if active or over else COL_TEXT_DIM); surface.blit(text, text.get_rect(center=rect.center)); x += card_w + 16
        maps = pygame.Rect(margin, modes.bottom + 8, width, 130)
        hover |= self.carousel.draw(surface, maps, mouse_pos, self.fonts); self.state.host.mapa_id = self.carousel.selected_id
        self.rect_start = pygame.Rect(0, 0, 300, 48); self.rect_start.center = (surface.get_width() // 2, maps.bottom + 42)
        over = self.rect_start.collidepoint(mouse_pos); hover |= over
        draw_panel(surface, self.rect_start, COL_ACCENT if over else COL_ACCENT_DIM, COL_ACCENT, 14, 2)
        text = self.fonts.config_boton.render("EMPEZAR PARTIDA", True, (25, 20, 15)); surface.blit(text, text.get_rect(center=self.rect_start.center))
        label = next(label for key, label, _ in self.MODOS if key == self.state.host.modo_partida)
        summary = self.fonts.opcion_desc.render(f"{self.state.host.duracion_min} minutos  •  {label.title()}", True, COL_TEXT_DIM)
        surface.blit(summary, summary.get_rect(midtop=(surface.get_width() // 2, self.rect_start.bottom + 8)))
        self.toast.draw(surface, margin)
        help_text = self.fonts.opcion_desc.render("Esc para volver   •   Enter para empezar con la configuración actual", True, COL_TEXT_DIM)
        surface.blit(help_text, help_text.get_rect(midbottom=(surface.get_width() // 2, surface.get_height() - 14)))
        return hover
