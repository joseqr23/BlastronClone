# core/game_modes/multi_game/results.py

import math
import pygame

from settings import ANCHO, ALTO
from utils.colors import ColorManager


class ResultsScreen:
    def __init__(self, game): self.game = game

    def show(self, label="Puntaje"):
        game = self.game
        game.sound_manager.iniciar_musica("assets/sfx/resultado.mp3")
        podium = game.modo.podio()
        rank_font = pygame.font.SysFont("Arial", 28, bold=True); name_font = pygame.font.SysFont("Arial", 18, bold=True)
        value_font = pygame.font.SysFont("Arial", 16); title_font = pygame.font.SysFont("Arial", 36, bold=True)
        button_font = pygame.font.SysFont("Arial", 18, bold=True)
        heights, base_y, block_w, gap = {1: 160, 2: 110, 3: 70}, ALTO - 60, 110, 20
        positions, current_x = [], 60
        for rank, players in podium:
            height = heights.get(rank, max(30, heights[3] - (rank - 3) * 40))
            for i, (player, value) in enumerate(players): positions.append((current_x + i * (block_w + gap) + block_w // 2, base_y - height, height, player, value, rank))
            current_x += block_w * len(players) + gap * (len(players) - 1) + gap * 2
        button = pygame.Rect(ANCHO - 200, 15, 180, 45); started = pygame.time.get_ticks(); clock = pygame.time.Clock(); back_to_menu = True
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: return False
                if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN): return back_to_menu
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and button.collidepoint(event.pos): return back_to_menu
            now, frame = pygame.time.get_ticks(), (pygame.time.get_ticks() - started) // 150
            game.pantalla.fill((30, 30, 40))
            title = title_font.render("¡Fin de la partida!", True, (255, 215, 0)); game.pantalla.blit(title, title.get_rect(center=(ANCHO // 2, 50)))
            for cx, top, height, player, value, rank in positions:
                if rank == 1: self._draw_first_place_glow(cx, top - 45, now)
                color = (200, 170, 60) if rank == 1 else ((180, 180, 190) if rank == 2 else ((160, 110, 70) if rank == 3 else (90, 90, 100)))
                pygame.draw.rect(game.pantalla, color, (cx - block_w // 2, top, block_w, height))
                sprite_top = top; robot = game.robot if player == game.nombre_jugador else game.robots_remotos.get(player)
                if robot:
                    anim = robot.animations.get("celebration", robot.animations["idle"]) if rank == 1 else (robot.animations["idle"] if rank == 2 else robot.animations.get("defeated", robot.animations["idle"]))
                    image = anim[int(frame) % len(anim)]
                    if not robot.facing_right: image = pygame.transform.flip(image, True, False)
                    image_rect = image.get_rect(midbottom=(cx, top)); game.pantalla.blit(image, image_rect); sprite_top = image_rect.top
                name = name_font.render(player, True, ColorManager.get_color(player)); game.pantalla.blit(name, name.get_rect(center=(cx, sprite_top - 15)))
                rank_text = rank_font.render(f"{rank}°", True, (255, 255, 255)); game.pantalla.blit(rank_text, rank_text.get_rect(center=(cx, base_y + 20)))
                value_text = value_font.render(f"{label}: {value}", True, (255, 255, 255)); game.pantalla.blit(value_text, value_text.get_rect(center=(cx, base_y + 42)))
            over = button.collidepoint(pygame.mouse.get_pos())
            pygame.draw.rect(game.pantalla, (90, 140, 220) if over else (60, 100, 180), button, border_radius=8)
            pygame.draw.rect(game.pantalla, (255, 255, 255), button, 2, border_radius=8)
            text = button_font.render("Volver al menú", True, (255, 255, 255)); game.pantalla.blit(text, text.get_rect(center=button.center))
            pygame.display.flip(); clock.tick(30)

    def _draw_first_place_glow(self, cx, cy, now):
        pulse = .5 + .5 * math.sin(now / 200); radius = int(70 + pulse * 15)
        glow = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow, (255, 230, 120, int(60 + pulse * 60)), (radius, radius), radius)
        self.game.pantalla.blit(glow, (cx - radius, cy - radius), special_flags=pygame.BLEND_RGBA_ADD)
