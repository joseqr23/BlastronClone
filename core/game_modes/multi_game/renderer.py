# core/game_modes/multi_game/renderer.py

import pygame

from settings import ANCHO, ALTO
from utils.weapon_loader import config_arma


class MultiplayerRenderer:
    def __init__(self, game):
        self.game = game

    def draw_frame(self):
        game = self.game
        world = game.superficie_mundo
        game.draw_scene(world)
        game.robot.draw(world)
        for robot in game.robots_remotos.values(): robot.draw(world)
        game.weapon_manager.draw(world)
        self._draw_local_weapon(world)
        self._draw_remote_weapons(world)
        game.pantalla.blit(world, game._offset_shake())
        game.hud_manager.draw(game.pantalla)
        game.chat.draw(game.pantalla)
        game.timer_hud.draw(game.pantalla)
        if getattr(game.modo, "usa_turnos", True):
            game.hud_turnos.draw(game.pantalla)
        game.robot.draw_death_message(game.pantalla, game.fuente_muerte)
        for robot in game.robots_remotos.values(): robot.draw_death_message(game.pantalla, game.fuente_muerte)
        self._draw_menu_button()
        self._draw_mute_button()
        if game.confirmando_salida:
            self._draw_exit_confirmation()

    def _draw_menu_button(self):
        game = self.game
        game.rect_volver_menu = pygame.Rect(ANCHO - 100, ALTO - 60, 90, 22)
        pygame.draw.rect(game.pantalla, (60, 100, 180), game.rect_volver_menu, border_radius=8)
        pygame.draw.rect(game.pantalla, (255, 255, 255), game.rect_volver_menu, 2, border_radius=8)
        text = game.fuente_botones.render("Menú (ESC)", True, (255, 255, 255))
        game.pantalla.blit(text, text.get_rect(center=game.rect_volver_menu.center))

    def _draw_local_weapon(self, surface):
        game, robot = self.game, self.game.robot
        if robot.arma_equipada in (None, "nada"): return
        mouse = pygame.mouse.get_pos()
        game.aim.origen = robot.get_centro(); game.aim.update(mouse)
        config = config_arma(robot.arma_equipada)
        if not config: return
        game.aim.draw(surface, estilo=config.get("estilo_mira", "apuntar"))
        ammo = game.weapon_manager.municion_actual(robot.arma_equipada)
        if ammo is not None and ammo <= 0: return
        hidden = config.get("oculta_arma_al_disparar")
        if hidden is None: hidden = config.get("comportamiento") == "cuerpo_a_cuerpo"
        active = hidden and any(getattr(p, "owner", None) == robot.nombre_jugador and getattr(p, "tipo", None) == robot.arma_equipada and getattr(p, "estado", None) != "done" for p in game.proyectiles)
        if not active:
            game.aim.draw_arma_sostenida(surface, config.get("_weapon_img"), mouse,
                                         posicion_x=config.get("posicion_ancho_arma_sostenida", 0),
                                         posicion_y=config.get("posicion_alto_arma_sostenida", 0))

    def _draw_remote_weapons(self, surface):
        game = self.game
        for player, robot in game.robots_remotos.items():
            weapon = getattr(robot, "arma_equipada", None)
            if weapon in (None, "nada") or getattr(robot, "sin_municion", False): continue
            config = config_arma(weapon)
            if not config: continue
            hidden = config.get("oculta_arma_al_disparar")
            if hidden is None: hidden = config.get("comportamiento") == "cuerpo_a_cuerpo"
            active = hidden and any(getattr(p, "owner", None) == player and getattr(p, "tipo", None) == weapon and getattr(p, "estado", None) != "done" for p in game.proyectiles)
            if active: continue
            origin = robot.get_centro()
            mouse_virtual = (origin[0] + getattr(robot, "aim_dx", 0), origin[1] + getattr(robot, "aim_dy", 0))
            game.aim_remoto.origen = origin
            game.aim_remoto.draw_arma_sostenida(surface, config.get("_weapon_img"), mouse_virtual,
                                                 posicion_x=config.get("posicion_ancho_arma_sostenida", 0),
                                                 posicion_y=config.get("posicion_alto_arma_sostenida", 0))

    def _draw_mute_button(self):
        game = self.game
        game.rect_mute = pygame.Rect(ANCHO - 100, ALTO - 30, 90, 22)
        muted = not game.sound_manager.habilitado
        pygame.draw.rect(game.pantalla, (150, 60, 60) if muted else (60, 150, 90), game.rect_mute, border_radius=8)
        pygame.draw.rect(game.pantalla, (255, 255, 255), game.rect_mute, 2, border_radius=8)
        text = game.fuente_botones.render("Muteado (M)" if muted else "Sonido (M)", True, (255, 255, 255))
        game.pantalla.blit(text, text.get_rect(center=game.rect_mute.center))

    def _draw_exit_confirmation(self):
        game = self.game
        overlay = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 165))
        game.pantalla.blit(overlay, (0, 0))

        panel = pygame.Rect(0, 0, 360, 170)
        panel.center = (ANCHO // 2, ALTO // 2)
        pygame.draw.rect(game.pantalla, (37, 44, 60), panel, border_radius=12)
        pygame.draw.rect(game.pantalla, (108, 123, 158), panel, 2, border_radius=12)
        title_font = pygame.font.SysFont("Arial", 22, bold=True)
        text_font = pygame.font.SysFont("Arial", 14)
        title = title_font.render("¿Abandonar la partida?", True, (245, 245, 250))
        hint = text_font.render("Tu personaje se desconectará de la partida.", True, (190, 199, 216))
        game.pantalla.blit(title, title.get_rect(center=(panel.centerx, panel.y + 38)))
        game.pantalla.blit(hint, hint.get_rect(center=(panel.centerx, panel.y + 70)))

        game.rect_cancelar_salida = pygame.Rect(panel.x + 34, panel.bottom - 52, 132, 34)
        game.rect_confirmar_salida = pygame.Rect(panel.right - 166, panel.bottom - 52, 132, 34)
        for rect, label, color in (
            (game.rect_cancelar_salida, "Cancelar (ESC)", (72, 91, 130)),
            (game.rect_confirmar_salida, "Abandonar", (170, 70, 70)),
        ):
            pygame.draw.rect(game.pantalla, color, rect, border_radius=8)
            pygame.draw.rect(game.pantalla, (240, 240, 245), rect, 1, border_radius=8)
            text = game.fuente_botones.render(label, True, (255, 255, 255))
            game.pantalla.blit(text, text.get_rect(center=rect.center))
