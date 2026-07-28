import pygame

from core.game_modes.solo_game import CampaignProgress
from ..theme import *


class SoloConfigScreen:
    """Selector de campaña; CampaignProgress conserva los desbloqueos."""
    def __init__(self, state, fonts, toast):
        self.state, self.fonts, self.toast = state, fonts, toast
        self.campaign = CampaignProgress()
        self.rect_back = self.rect_start = None
        self.level_rects = []

    def _unlocked_ids(self):
        return [level.id for level in self.campaign.levels if self.campaign.is_unlocked(level.id)]

    def _move(self, direction):
        ids = self._unlocked_ids()
        if self.state.solo.level_id not in ids:
            self.state.solo.level_id = ids[0]
        else:
            self.state.solo.level_id = ids[(ids.index(self.state.solo.level_id) + direction) % len(ids)]

    def handle_event(self, event, mouse_pos):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE: return "volver"
            if event.key in (pygame.K_LEFT, pygame.K_UP): self._move(-1)
            if event.key in (pygame.K_RIGHT, pygame.K_DOWN): self._move(1)
            if event.key == pygame.K_RETURN: return "empezar_solo"
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect_back and self.rect_back.collidepoint(mouse_pos): return "volver"
            if self.rect_start and self.rect_start.collidepoint(mouse_pos): return "empezar_solo"
            for level_id, rect, unlocked in self.level_rects:
                if rect.collidepoint(mouse_pos):
                    if unlocked: self.state.solo.level_id = level_id
                    else: self.toast.show("Completa el nivel anterior")
        return None

    def draw(self, surface, mouse_pos):
        margin = 60
        self.rect_back = pygame.Rect(margin, 16, 100, 32)
        hover = self.rect_back.collidepoint(mouse_pos)
        draw_panel(surface, self.rect_back, COL_OPTION_HOVER if hover else COL_OPTION_IDLE, COL_ACCENT if hover else COL_CARD_BORDER, 8, 2)
        text = self.fonts.config_seccion.render("Volver", True, COL_TEXT); surface.blit(text, text.get_rect(center=self.rect_back.center))
        surface.blit(self.fonts.config_titulo.render("Modo Solo", True, COL_TEXT), (margin, 54))
        subtitle = self.fonts.subtitulo.render("Completa niveles, gana estrellas y derrota jefes", True, COL_TEXT_DIM)
        surface.blit(subtitle, (margin + 2, 92))
        pygame.draw.line(surface, COL_CARD_BORDER, (margin, 112), (surface.get_width() - margin, 112), 2)
        self.level_rects = []
        card_w, card_h, gap = 180, 105, 18
        start_x = surface.get_width() // 2 - (3 * card_w + 2 * gap) // 2
        for index, level in enumerate(self.campaign.levels):
            row, col = divmod(index, 3)
            rect = pygame.Rect(start_x + col * (card_w + gap), 142 + row * (card_h + gap), card_w, card_h)
            unlocked = self.campaign.is_unlocked(level.id)
            selected = level.id == self.state.solo.level_id
            over = rect.collidepoint(mouse_pos) and unlocked
            draw_panel(surface, rect, COL_OPTION_SELECTED if selected else (COL_OPTION_HOVER if over else COL_OPTION_IDLE),
                       COL_ACCENT if selected else (COL_ACCENT_DIM if unlocked else COL_CARD_BORDER), 10, 2 if selected else 1)
            color = COL_TEXT if unlocked else COL_TEXT_DISABLED
            title = self.fonts.config_seccion.render(f"NIVEL {level.id}", True, color)
            detail = self.fonts.opcion_desc.render("JEFE" if level.boss else f"{level.bots} bot(s)", True, color)
            status = ("*" * self.campaign.stars_for(level.id)) or ("Bloqueado" if not unlocked else "Sin completar")
            progress = self.fonts.opcion_desc.render(status, True, COL_ACCENT if unlocked else COL_TEXT_DISABLED)
            surface.blit(title, (rect.x + 16, rect.y + 17)); surface.blit(detail, (rect.x + 16, rect.y + 47)); surface.blit(progress, (rect.x + 16, rect.y + 75))
            self.level_rects.append((level.id, rect, unlocked)); hover |= over
        self.rect_start = pygame.Rect(0, 0, 290, 48); self.rect_start.center = (surface.get_width() // 2, 410)
        over = self.rect_start.collidepoint(mouse_pos); hover |= over
        draw_panel(surface, self.rect_start, COL_ACCENT if over else COL_ACCENT_DIM, COL_ACCENT, 14, 2)
        text = self.fonts.config_boton.render("JUGAR NIVEL", True, (25, 20, 15)); surface.blit(text, text.get_rect(center=self.rect_start.center))
        self.toast.draw(surface, margin)
        help_text = self.fonts.opcion_desc.render("Flechas para elegir   Enter para jugar   Esc para volver", True, COL_TEXT_DIM)
        surface.blit(help_text, help_text.get_rect(midbottom=(surface.get_width() // 2, surface.get_height() - 14)))
        return hover
