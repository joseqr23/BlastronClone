# ui/menu/theme.py

import pygame
from dataclasses import dataclass

COL_BG_TOP = (24, 28, 38)
COL_BG_BOTTOM = (14, 16, 22)
COL_CARD = (32, 37, 50)
COL_CARD_BORDER = (54, 61, 80)
COL_ACCENT = (255, 140, 0)
COL_ACCENT_DIM = (150, 90, 30)
COL_TEXT = (235, 235, 240)
COL_TEXT_DIM = (160, 165, 175)
COL_TEXT_DISABLED = (95, 98, 108)
COL_INPUT_BG = (20, 23, 32)
COL_INPUT_BORDER = (70, 78, 100)
COL_INPUT_BORDER_ACTIVE = (255, 140, 0)
COL_OPTION_IDLE = (40, 46, 62)
COL_OPTION_HOVER = (52, 60, 82)
COL_OPTION_SELECTED = (60, 45, 30)
COL_PILL_BG = (20, 23, 32)
COL_PILL_ACTIVE = (255, 140, 0)


def lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def draw_vertical_gradient(surface, top_color=COL_BG_TOP, bottom_color=COL_BG_BOTTOM):
    width, height = surface.get_size()
    for y in range(height):
        pygame.draw.line(surface, lerp_color(top_color, bottom_color, y / max(height - 1, 1)), (0, y), (width, y))


def draw_panel(surface, rect, color=COL_CARD, border=COL_CARD_BORDER, radius=14, border_w=2):
    pygame.draw.rect(surface, color, rect, border_radius=radius)
    pygame.draw.rect(surface, border, rect, width=border_w, border_radius=radius)


@dataclass
class MenuFonts:
    titulo: object
    subtitulo: object
    label: object
    opcion: object
    opcion_desc: object
    input: object
    pill: object
    flecha: object
    badge: object
    config_titulo: object
    config_seccion: object
    config_boton: object

    @classmethod
    def create(cls):
        return cls(
            pygame.font.SysFont("Arial", 42, bold=True), pygame.font.SysFont("Arial", 16),
            pygame.font.SysFont("Arial", 17, bold=True), pygame.font.SysFont("Arial", 24, bold=True),
            pygame.font.SysFont("Arial", 13), pygame.font.SysFont("Arial", 22),
            pygame.font.SysFont("Arial", 16, bold=True), pygame.font.SysFont("Arial", 22, bold=True),
            pygame.font.SysFont("Arial", 11, bold=True), pygame.font.SysFont("Arial", 30, bold=True),
            pygame.font.SysFont("Arial", 15, bold=True), pygame.font.SysFont("Arial", 20, bold=True),
        )
