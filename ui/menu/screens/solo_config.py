# ui/menu/screens/solo_config.py
import math
from pathlib import Path

import pygame

from core.game_modes.solo_game import CampaignProgress
from utils.paths import resource_path
from ..theme import *

PAGE_SIZE = 6  # 3x2 por "mundo" — cada mundo es una página del carrusel
MAX_ESTRELLAS_DIFICULTAD = 5

# Caché de fondos en memoria a nivel de módulo: distintos niveles que
# comparten mapa (ej. "playa" en el nivel 2 y el 4) reusan la misma
# superficie ya escalada, y no se recarga desde disco frame a frame.
_CACHE_FONDOS: dict[tuple[str, int, int], "pygame.Surface | None"] = {}


def _cargar_fondo_mapa(mapa_id: str, size: tuple[int, int]):
    """Miniatura del fondo del mapa (assets/maps/<mapa>/fondo.png) para
    usar como fondo de la tarjeta de nivel. Devuelve None si no existe
    o no se pudo cargar, y en ese caso la tarjeta cae al panel plano
    de siempre."""
    clave = (mapa_id, *size)
    if clave in _CACHE_FONDOS:
        return _CACHE_FONDOS[clave]
    ruta = Path(resource_path(f"assets/maps/{mapa_id}/fondo.png"))
    imagen = None
    if ruta.exists():
        try:
            imagen = pygame.transform.smoothscale(pygame.image.load(str(ruta)).convert(), size)
        except pygame.error:
            imagen = None
    _CACHE_FONDOS[clave] = imagen
    return imagen


class SoloConfigScreen:
    """Selector de campaña; CampaignProgress conserva los desbloqueos."""
    def __init__(self, state, fonts, toast):
        self.state, self.fonts, self.toast = state, fonts, toast
        self.campaign = CampaignProgress()
        self.rect_back = self.rect_start = None
        self.rect_prev_page = self.rect_next_page = None
        self.level_rects = []
        self.page = 0
        self._frames_desde_refresh = 0
        # Fuente propia para las estrellas de dificultad — más grande
        # que el resto del texto de la tarjeta, a propósito.
        self.fuente_estrellas = pygame.font.SysFont("Arial", 20, bold=True)

    def _unlocked_ids(self):
        return [level.id for level in self.campaign.levels if self.campaign.is_unlocked(level.id)]

    def _total_pages(self):
        return max(1, math.ceil(len(self.campaign.levels) / PAGE_SIZE))

    def _pagina_de_nivel(self, level_id):
        for indice, level in enumerate(self.campaign.levels):
            if level.id == level_id:
                return indice // PAGE_SIZE
        return 0

    def _move(self, direction):
        ids = self._unlocked_ids()
        if not ids:
            return
        if self.state.solo.level_id not in ids:
            self.state.solo.level_id = ids[0]
        else:
            self.state.solo.level_id = ids[(ids.index(self.state.solo.level_id) + direction) % len(ids)]
        # Si el nuevo nivel seleccionado vive en otra página, la sigue
        # automáticamente — no hace falta que el jugador use el carrusel
        # a mano solo para mover la selección con las flechas.
        self.page = self._pagina_de_nivel(self.state.solo.level_id)

    def _cambiar_pagina(self, direction):
        total = self._total_pages()
        self.page = (self.page + direction) % total

    def handle_event(self, event, mouse_pos):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE: return "volver"
            if event.key in (pygame.K_LEFT, pygame.K_UP): self._move(-1)
            if event.key in (pygame.K_RIGHT, pygame.K_DOWN): self._move(1)
            if event.key == pygame.K_RETURN: return "empezar_solo"
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect_back and self.rect_back.collidepoint(mouse_pos): return "volver"
            if self.rect_start and self.rect_start.collidepoint(mouse_pos): return "empezar_solo"
            if self.rect_prev_page and self.rect_prev_page.collidepoint(mouse_pos):
                self._cambiar_pagina(-1); return None
            if self.rect_next_page and self.rect_next_page.collidepoint(mouse_pos):
                self._cambiar_pagina(1); return None
            for level_id, rect, unlocked in self.level_rects:
                if rect.collidepoint(mouse_pos):
                    if unlocked: self.state.solo.level_id = level_id
                    else: self.toast.show("Completa el nivel anterior")
        return None

    def _dibujar_estrellas_dificultad(self, surface, pos, dificultad, unlocked):
        x, y = pos
        color_lleno = COL_ACCENT if unlocked else COL_TEXT_DISABLED
        color_vacio = COL_CARD_BORDER
        dificultad = max(0, min(MAX_ESTRELLAS_DIFICULTAD, dificultad))
        for i in range(MAX_ESTRELLAS_DIFICULTAD):
            color = color_lleno if i < dificultad else color_vacio
            estrella = self.fuente_estrellas.render("*", True, color)
            surface.blit(estrella, (x + i * 16, y))

    def draw(self, surface, mouse_pos):
        # Refresca el progreso ~2 veces por segundo — así si el jugador
        # vuelve del juego a este menú (misma instancia de pantalla), el
        # desbloqueo del siguiente nivel se refleja solo, sin reabrir el
        # menú. Es una lectura de un JSON chico, no un costo real.
        self._frames_desde_refresh += 1
        if self._frames_desde_refresh >= 30:
            self._frames_desde_refresh = 0
            self.campaign.refresh()
            if self.state.solo.level_id not in self._unlocked_ids():
                unlocked = self._unlocked_ids()
                if unlocked:
                    self.state.solo.level_id = unlocked[-1]

        margin = 60
        self.rect_back = pygame.Rect(margin, 16, 100, 32)
        hover = self.rect_back.collidepoint(mouse_pos)
        draw_panel(surface, self.rect_back, COL_OPTION_HOVER if hover else COL_OPTION_IDLE, COL_ACCENT if hover else COL_CARD_BORDER, 8, 2)
        text = self.fonts.config_seccion.render("Volver", True, COL_TEXT); surface.blit(text, text.get_rect(center=self.rect_back.center))
        surface.blit(self.fonts.config_titulo.render("Modo Solo", True, COL_TEXT), (margin, 54))
        subtitle = self.fonts.subtitulo.render("Completa niveles, gana estrellas y derrota jefes", True, COL_TEXT_DIM)
        surface.blit(subtitle, (margin + 2, 92))
        pygame.draw.line(surface, COL_CARD_BORDER, (margin, 112), (surface.get_width() - margin, 112), 2)
        titulo_mundo = self.fonts.config_seccion.render(self.campaign.nombre_mundo(self.page).upper(), True, COL_ACCENT)
        surface.blit(titulo_mundo, titulo_mundo.get_rect(midtop=(surface.get_width() // 2, 120)))

        self.level_rects = []
        card_w, card_h, gap = 200, 132, 18
        start_x = surface.get_width() // 2 - (3 * card_w + 2 * gap) // 2
        grid_top = 152  # antes 142 — le deja aire al título "MUNDO N" de arriba

        total_pages = self._total_pages()
        self.page = max(0, min(self.page, total_pages - 1))
        inicio = self.page * PAGE_SIZE
        pagina = self.campaign.levels[inicio:inicio + PAGE_SIZE]

        for indice, level in enumerate(pagina):
            row, col = divmod(indice, 3)
            rect = pygame.Rect(start_x + col * (card_w + gap), grid_top + row * (card_h + gap), card_w, card_h)
            unlocked = self.campaign.is_unlocked(level.id)
            selected = level.id == self.state.solo.level_id
            over = rect.collidepoint(mouse_pos) and unlocked

            fondo = _cargar_fondo_mapa(level.mapa, (card_w, card_h))
            if fondo:
                surface.blit(fondo, rect.topleft)
                velo = pygame.Surface(rect.size, pygame.SRCALPHA)
                velo.fill((8, 8, 12, 165 if unlocked else 205))
                surface.blit(velo, rect.topleft)
            else:
                draw_panel(surface, rect, COL_OPTION_SELECTED if selected else (COL_OPTION_HOVER if over else COL_OPTION_IDLE),
                          COL_ACCENT if selected else (COL_ACCENT_DIM if unlocked else COL_CARD_BORDER), 10, 2 if selected else 1)

            borde = COL_ACCENT if selected else (COL_ACCENT_DIM if (unlocked and over) else COL_CARD_BORDER)
            pygame.draw.rect(surface, borde, rect, 3 if selected else 2, border_radius=10)

            color = COL_TEXT if unlocked else COL_TEXT_DISABLED
            id_txt = self.fonts.opcion_desc.render(f"NIVEL {level.id}", True, color)
            surface.blit(id_txt, (rect.x + 14, rect.y + 10))

            # Nombre del nivel — independiente del id y del nombre de la
            # carpeta del mapa. Si el JSON no trae "nombre", se usa el
            # nombre del mapa como fallback.
            nombre = level.nombre or level.mapa.capitalize()
            nombre_txt = self.fonts.config_seccion.render(nombre, True, color)
            surface.blit(nombre_txt, (rect.x + 14, rect.y + 29))

            self._dibujar_estrellas_dificultad(surface, (rect.x + 14, rect.y + 60), level.dificultad, unlocked)

            # level.bots es una tupla de BotConfig — se cuenta con len(),
            # nunca se interpola la tupla directo o Python muestra el
            # repr() de cada BotConfig en la tarjeta.
            detail = self.fonts.opcion_desc.render("JEFE" if level.boss else f"{len(level.bots)} bot(s)", True, color)
            surface.blit(detail, (rect.x + 14, rect.y + 85))

            if unlocked:
                estrellas_ganadas = self.campaign.stars_for(level.id)
                status = ("*" * estrellas_ganadas) if estrellas_ganadas else "Sin completar"
                status_color = COL_ACCENT
            else:
                status = "Bloqueado"
                status_color = COL_TEXT_DISABLED
            status_txt = self.fonts.opcion_desc.render(status, True, status_color)
            surface.blit(status_txt, (rect.x + 14, rect.y + 107))

            self.level_rects.append((level.id, rect, unlocked))
            hover |= over

        filas = math.ceil(len(pagina) / 3) if pagina else 1
        grid_alto = filas * card_h + (filas - 1) * gap
        centro_y = grid_top + grid_alto // 2

        self.rect_prev_page = self.rect_next_page = None
        pie_y = grid_top + grid_alto + 20
        if total_pages > 1:
            self.rect_prev_page = pygame.Rect(start_x - 52, centro_y - 20, 40, 40)
            self.rect_next_page = pygame.Rect(start_x + 3 * card_w + 2 * gap + 12, centro_y - 20, 40, 40)
            for rect_flecha, simbolo in ((self.rect_prev_page, "<"), (self.rect_next_page, ">")):
                over_flecha = rect_flecha.collidepoint(mouse_pos)
                draw_panel(surface, rect_flecha, COL_OPTION_HOVER if over_flecha else COL_OPTION_IDLE,
                          COL_ACCENT if over_flecha else COL_CARD_BORDER, 20, 2)
                flecha_txt = self.fonts.config_seccion.render(simbolo, True, COL_TEXT)
                surface.blit(flecha_txt, flecha_txt.get_rect(center=rect_flecha.center))
                hover |= over_flecha
            pagina_txt = self.fonts.opcion_desc.render(f"{self.campaign.nombre_mundo(self.page)} ({self.page + 1}/{total_pages})", True, COL_TEXT_DIM)
            surface.blit(pagina_txt, pagina_txt.get_rect(midtop=(surface.get_width() // 2, pie_y)))
            pie_y += 26

        self.rect_start = pygame.Rect(0, 0, 290, 48); self.rect_start.center = (surface.get_width() // 2, pie_y + 26)
        over = self.rect_start.collidepoint(mouse_pos); hover |= over
        draw_panel(surface, self.rect_start, COL_ACCENT if over else COL_ACCENT_DIM, COL_ACCENT, 14, 2)
        text = self.fonts.config_boton.render("JUGAR NIVEL", True, (25, 20, 15)); surface.blit(text, text.get_rect(center=self.rect_start.center))
        self.toast.draw(surface, margin)
        help_text = self.fonts.opcion_desc.render("Flechas para elegir   Enter para jugar   Esc para volver", True, COL_TEXT_DIM)
        surface.blit(help_text, help_text.get_rect(midbottom=(surface.get_width() // 2, surface.get_height() - 14)))
        return hover