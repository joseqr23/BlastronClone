import pygame
from settings import ANCHO, ALTO, ALTURA_SUELO
from entities.players.robot import Robot
from systems.collision import check_collisions, check_collisions_laterales_esquinas
from systems.aim_indicator import AimIndicator
from core.game_modes.base_game import BaseGame
from ui.hud import HUDPuntajes

from systems.event_handler import EventHandler
from systems.weapon_manager import WeaponManager
from systems.hud_manager import HUDManager


class FreeGame(BaseGame):
    def __init__(self, nombre_jugador, personaje):
        super().__init__(nombre_jugador=nombre_jugador)

        # Jugador principal
        self.robot = Robot(
            x=ANCHO // 2 - 30,
            y=ALTO - 90 - ALTURA_SUELO,
            nombre_jugador=nombre_jugador,
            nombre_robot=personaje
        )

        self.robots_estaticos = []
        self.aim = AimIndicator(self.robot.get_centro())
        self.puntajes[self.robot] = 0

        # HUD individual de puntajes (lo usa el HUDManager)
        self.hud_puntajes = HUDPuntajes(self)

        # Sistemas
        self.weapon_manager = WeaponManager(self)
        self.hud_manager = HUDManager(self)
        self.event_handler = EventHandler(self)

    def run(self):
        while True:
            # --- Entrada ---
            if not self.event_handler.handle_events():
                return  # usuario cerró ventana

            # --- Actualización ---
            keys = pygame.key.get_pressed()
            self.robot.update(keys)
            if keys[pygame.K_DELETE]:
                self.robot.take_damage(50)

            for r in self.robots_estaticos:
                r.update(self.tiles)

            # limpiar robots muertos
            self.robots_estaticos = [r for r in self.robots_estaticos if not r.debe_eliminarse()]

            # colisiones
            check_collisions(self.robot, self.tiles)
            check_collisions_laterales_esquinas(self.robot, self.tiles_laterales)

            # armas
            self.weapon_manager.update()

            # --- Render ---
            self.draw_scene()

            # personajes
            self.robot.draw(self.pantalla)
            for r in self.robots_estaticos:
                r.draw(self.pantalla)

            # armas
            self.weapon_manager.draw(self.pantalla)

            # indicador de mira
            if self.robot.arma_equipada not in [None, 'nada']:
                mouse_pos = pygame.mouse.get_pos()
                self.aim.origen = self.robot.get_centro()
                self.aim.update(mouse_pos)
                self.aim.draw(self.pantalla)

            # HUDs
            self.hud_manager.draw(self.pantalla)

            # mensajes de muerte
            self.robot.draw_death_message(self.pantalla, self.fuente_muerte)
            for r in self.robots_estaticos:
                r.draw_death_message(self.pantalla, self.fuente_muerte)

            # chat
            self.chat.draw(self.pantalla)

            pygame.display.flip()
            self.reloj.tick(60)
