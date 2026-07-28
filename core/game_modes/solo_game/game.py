# core/game_modes/solo_game/game.py
"""Partida local de campaña. No depende de FreeGame ni de MultiGame."""
import math
import pygame

from settings import ANCHO, ALTO, ALTURA_SUELO
from core.game_modes.base_game import BaseGame
from entities.players.robot import Robot
from entities.weapons.proyectil import Proyectil
from systems.aim_indicator import AimIndicator
from systems.collision import (check_collisions, check_collisions_laterales_esquinas,
                               check_colision_bloque_solido)
from systems import collision
from systems.event_handler import EventHandler
from utils.colors import ColorManager
from utils.sound_manager import sound_manager
from utils.weapon_loader import config_arma

from .bot_manager import BotManager
from .boss_manager import BossManager
from .campaign import CampaignProgress
from .results import LevelResult
from .rewards import calculate_stars


class SoloCombatManager:
    """Combate local multi-actor; WeaponManager libre solo conoce al jugador."""
    def __init__(self, game):
        self.game = game

    def disparar(self):
        robot = self.game.robot
        if robot.arma_equipada not in (None, "nada"):
            self.fire(robot, self.game.aim.direccion)

    def fire(self, robot, direction):
        weapon = robot.arma_equipada or "misil"
        config = config_arma(weapon)
        if not config:
            return False
        dx, dy = direction
        length = math.hypot(dx, dy)
        if not length:
            return False
        speed = config.get("velocidad_proyectil", 20)
        vx, vy = dx / length * speed, dy / length * speed
        width, height = config.get("ancho_proyectil", 40), config.get("alto_proyectil", 40)
        origin = robot.get_centro()
        projectile = Proyectil(weapon, origin[0] - width / 2, origin[1] - height / 2,
                               vx, vy, owner=robot.nombre_jugador,
                               facing_right=robot.facing_right,
                               angulo_ataque=math.degrees(math.atan2(dy, dx)))
        self.game.proyectiles.append(projectile)
        sound_manager.disparo(weapon)
        return True

    def update(self):
        candidates = self.game.all_robots()
        for projectile in self.game.proyectiles[:]:
            projectile.update(self.game.tiles + self.game.tiles_impenetrables, candidates)
            for robot in projectile.robots_afectados(candidates):
                before = robot.is_dead
                damage = getattr(projectile, "da" + chr(0xF1) + "o") * getattr(self.game.robot_by_name(projectile.owner), "damage_multiplier", 1)
                robot.take_damage(damage)
                projectile.danados.add(robot)
                if projectile.owner == self.game.robot.nombre_jugador:
                    self.game.puntajes[self.game.robot] += int(damage) * (2 if not before and robot.is_dead else 1)
            if projectile.estado == "done":
                self.game.proyectiles.remove(projectile)

    def draw(self, surface):
        for projectile in self.game.proyectiles:
            projectile.draw(surface)


class SoloGame(BaseGame):
    def __init__(self, nombre_jugador, personaje, level_id=1, campaign=None):
        self.campaign = campaign or CampaignProgress()
        self.level = self.campaign.get_level(level_id)
        super().__init__(nombre_jugador=nombre_jugador, personaje=personaje, mapa_id=self.level.mapa)
        ColorManager.reset()
        self.host = True  # compatibilidad con utilidades locales que consultan este atributo.
        self.robot = Robot(ANCHO // 2, ALTO - ALTURA_SUELO - 90, nombre_jugador, personaje,
                           vida_maxima=250, puede_reaparecer=False)
        self.robot.es_jugador = True
        self.chat.robot_local = self.robot
        self.robot.arma_equipada = "misil"
        self.robots_estaticos = []  # requerido por EventHandler; no participa en campaña.
        self.bots = []
        self.aim = AimIndicator(self.robot.get_centro())
        self.bot_manager = BotManager(self, self.level.dificultad, seed=self.level.id)
        self.bots.extend(self.bot_manager.spawn(self.level.bots))
        for index, bot in enumerate(self.bots):
            bot.arma_equipada = self.level.armas_bots[index % len(self.level.armas_bots)]
        self.boss_manager = BossManager(self, self.level.boss) if self.level.boss else None
        self.boss = self.boss_manager.spawn() if self.boss_manager else None
        if self.boss:
            self.boss.arma_equipada = self.level.boss.armas[0]
        self.puntajes[self.robot] = 0
        self.weapon_manager = SoloCombatManager(self)
        self.event_handler = EventHandler(self)
        self.volver_al_menu = False
        self.rect_volver_menu = self.rect_mute = None
        self.fuente_botones = pygame.font.SysFont("Arial", 14, bold=True)
        self.started_at = pygame.time.get_ticks()
        self.duration_ms = self.level.duracion_min * 60_000
        self.result = None

    def all_robots(self):
        return [self.robot, *self.bots, *([self.boss] if self.boss else [])]

    def robot_by_name(self, name):
        return next((robot for robot in self.all_robots() if robot.nombre_jugador == name), None)

    def _update_robot_physics(self, robot, keys=None):
        robot.update(keys)
        check_collisions(robot, self.tiles)
        check_collisions_laterales_esquinas(robot, self.tiles_laterales)
        check_colision_bloque_solido(robot, self.tiles_impenetrables)
        # El módulo existente conserva este nombre público con "ñ".
        hazardous_tiles = getattr(self, "tiles_da" + chr(0xF1) + "inas")
        getattr(collision, "check_zonas_da" + chr(0xF1) + "inas")(robot, hazardous_tiles, self.dano_zonas)

    def _finish(self, victory, reason):
        if self.result:
            return
        elapsed = pygame.time.get_ticks() - self.started_at
        health = max(0, self.robot.health) / self.robot.vida_maxima
        stars = calculate_stars(victory, health, elapsed / self.duration_ms)
        if victory:
            self.campaign.complete_level(self.level.id, stars)
        self.result = LevelResult(self.level.id, victory, stars, reason,
                                  self.campaign.next_level_id(self.level.id) if victory else None)

    def _check_result(self):
        if self.robot.is_dead:
            self._finish(False, "Tu robot fue derrotado")
        elif all(bot.is_dead for bot in self.bots) and (not self.boss or self.boss.is_dead):
            self._finish(True, "Nivel completado")
        elif pygame.time.get_ticks() - self.started_at >= self.duration_ms:
            self._finish(False, "Se acabó el tiempo")

    def _draw_overlay(self):
        elapsed = pygame.time.get_ticks() - self.started_at
        seconds = max(0, (self.duration_ms - elapsed) // 1000)
        text = self.fuente_botones.render(f"Nivel {self.level.id}   Tiempo {seconds // 60}:{seconds % 60:02d}", True, (255, 255, 255))
        self.pantalla.blit(text, (12, 12))
        self.rect_volver_menu = pygame.Rect(ANCHO - 105, ALTO - 60, 95, 24)
        self.rect_mute = pygame.Rect(ANCHO - 105, ALTO - 30, 95, 24)
        for rect, label, color in ((self.rect_volver_menu, "Menú (ESC)", (60, 100, 180)),
                                   (self.rect_mute, "Sonido (M)", (60, 150, 90))):
            pygame.draw.rect(self.pantalla, color, rect, border_radius=7)
            pygame.draw.rect(self.pantalla, (255, 255, 255), rect, 1, border_radius=7)
            label_surface = self.fuente_botones.render(label, True, (255, 255, 255))
            self.pantalla.blit(label_surface, label_surface.get_rect(center=rect.center))

    def _draw_result(self):
        if not self.result:
            return
        panel = pygame.Rect(ANCHO // 2 - 210, ALTO // 2 - 90, 420, 180)
        pygame.draw.rect(self.pantalla, (20, 25, 38), panel, border_radius=14)
        pygame.draw.rect(self.pantalla, (245, 190, 65) if self.result.victory else (210, 75, 75), panel, 3, border_radius=14)
        title = self.fuente_muerte.render("¡Victoria!" if self.result.victory else "Derrota", True, (255, 255, 255))
        detail = self.fuente_botones.render(f"{self.result.reason} — {self.result.stars} estrella(s)", True, (230, 230, 230))
        hint = self.fuente_botones.render("ESC para volver al menú", True, (190, 190, 190))
        self.pantalla.blit(title, title.get_rect(center=(panel.centerx, panel.y + 52)))
        self.pantalla.blit(detail, detail.get_rect(center=(panel.centerx, panel.y + 105)))
        self.pantalla.blit(hint, hint.get_rect(center=(panel.centerx, panel.y + 145)))

    def run(self):
        while True:
            if not self.event_handler.handle_events() or self.volver_al_menu:
                return "menu"
            if not self.result:
                keys = pygame.key.get_pressed()
                mouse_pos = pygame.mouse.get_pos()
                self.robot.facing_right = mouse_pos[0] >= self.robot.get_centro()[0]
                self.aim.origen = self.robot.get_centro()
                self.aim.update(mouse_pos)
                self._update_robot_physics(self.robot, keys)
                for bot in self.bots:
                    self._update_robot_physics(bot)
                if self.boss:
                    self._update_robot_physics(self.boss)
                for bot, direction in self.bot_manager.update(self.robot):
                    self.weapon_manager.fire(bot, direction)
                if self.boss_manager:
                    shot = self.boss_manager.update(self.robot)
                    if shot:
                        self.weapon_manager.fire(*shot)
                self.weapon_manager.update()
                self._check_result()
            self.draw_scene(self.superficie_mundo)
            for actor in self.all_robots():
                actor.draw(self.superficie_mundo)
            self.weapon_manager.draw(self.superficie_mundo)
            if not self.result and self.robot.arma_equipada not in (None, "nada"):
                self.aim.draw(self.superficie_mundo, estilo=(config_arma(self.robot.arma_equipada) or {}).get("estilo_mira", "apuntar"))
            self.pantalla.blit(self.superficie_mundo, self._offset_shake())
            self.draw_ui()
            self._draw_overlay()
            self._draw_result()
            pygame.display.flip()
            self.reloj.tick(60)
