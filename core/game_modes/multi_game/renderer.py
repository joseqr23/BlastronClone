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
        game.hud_turnos.draw(game.pantalla)
        game.robot.draw_death_message(game.pantalla, game.fuente_muerte)
        for robot in game.robots_remotos.values(): robot.draw_death_message(game.pantalla, game.fuente_muerte)
        self._draw_mute_button()

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
