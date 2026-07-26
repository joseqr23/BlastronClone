# core/game_modes/free_game.py
import pygame
from settings import ANCHO, ALTO, ALTURA_SUELO
from entities.players.robot import Robot # Robots
from systems.collision import check_collisions, check_collisions_laterales_esquinas # Colisiones
from systems.aim_indicator import AimIndicator # Mira de armas
from core.game_modes.base_game import BaseGame # Base de juego
from ui.hud import HUDPuntajes # Hud

from systems.event_handler import EventHandler # Manejador de eventos 
from systems.weapon_manager_free import WeaponManager # Manejador de armas
from systems.hud_manager import HUDManager # Manejador de HUD

from utils.weapon_loader import config_arma 
from utils.colors import ColorManager

class FreeGame(BaseGame):
    def __init__(self, nombre_jugador, personaje):
        super().__init__(nombre_jugador=nombre_jugador)
        ColorManager.reset()
        # Jugador principal
        self.robot = Robot(
            x=ANCHO // 2 - 30,
            y=ALTO - 90 - ALTURA_SUELO,
            nombre_jugador=nombre_jugador,
            nombre_robot=personaje
        )

        self.chat.robot_local = self.robot

        self.robots_estaticos = []
        self.aim = AimIndicator(self.robot.get_centro())
        self.puntajes[self.robot] = 0

        # HUD individual de puntajes (lo usa el HUDManager)
        self.hud_puntajes = HUDPuntajes(self)

        # Sistemas
        self.weapon_manager = WeaponManager(self)
        self.hud_manager = HUDManager(self)
        self.event_handler = EventHandler(self)
        self.volver_al_menu = False
        self.rect_volver_menu = None
        self.rect_mute = None
        self.fuente_botones = pygame.font.SysFont("Arial", 10, bold=True)

    def run(self):
        while True:
            if not self.robot.is_dead and self.robot.arma_equipada not in [None, 'nada']:
                mouse_pos = pygame.mouse.get_pos()
                self.robot.facing_right = mouse_pos[0] >= self.robot.get_centro()[0]

            # --- Entrada ---
            if not self.event_handler.handle_events():
                return  # usuario cerró ventana
            if self.volver_al_menu:
                return "menu"

            # --- Actualización ---
            keys = pygame.key.get_pressed()
            self.robot.update(keys)
            if keys[pygame.K_DELETE]:
                self.robot.take_damage(50)

            for r in self.robots_estaticos:
                r.update(self.tiles, self.tiles_laterales)

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
                config = config_arma(self.robot.arma_equipada)
                estilo_mira = config.get("estilo_mira", "apuntar") if config else "apuntar"
                self.aim.draw(self.pantalla, estilo=estilo_mira)
                municion = self.weapon_manager.municion_actual(self.robot.arma_equipada)
                sin_municion = municion is not None and municion <= 0
                if config and not sin_municion:
                    oculta_al_disparar = config.get("oculta_arma_al_disparar")
                    if oculta_al_disparar is None:
                        oculta_al_disparar = (config.get("comportamiento") == "cuerpo_a_cuerpo")
                    tiene_proyectil_activo = oculta_al_disparar and any(
                        getattr(p, "owner", None) == self.robot.nombre_jugador
                        and getattr(p, "tipo", None) == self.robot.arma_equipada
                        and getattr(p, "estado", None) != "done"
                        for p in self.proyectiles
                    )
                    if not tiene_proyectil_activo:
                        self.aim.draw_arma_sostenida(
                            self.pantalla, config.get("_weapon_img"), mouse_pos,
                            posicion_x=config.get("posicion_ancho_arma_sostenida", 0),
                            posicion_y=config.get("posicion_alto_arma_sostenida", 0),
                        )

            # HUDs
            self.hud_manager.draw(self.pantalla)

            # Mensajes de muerte
            self.robot.draw_death_message(self.pantalla, self.fuente_muerte)
            for r in self.robots_estaticos:
                r.draw_death_message(self.pantalla, self.fuente_muerte)

            # Chat
            self.chat.draw(self.pantalla)

            # Botones de esquina: volver al menú y mute (abajo a la
            # derecha, para no taparse con el HUD de armas que vive
            # arriba a la derecha)
            self.rect_volver_menu = pygame.Rect(ANCHO - 100, ALTO - 60, 90, 22)
            pygame.draw.rect(self.pantalla, (60, 100, 180), self.rect_volver_menu, border_radius=8)
            pygame.draw.rect(self.pantalla, (255, 255, 255), self.rect_volver_menu, width=2, border_radius=8)
            texto_menu = self.fuente_botones.render("Menú (ESC)", True, (255, 255, 255))
            self.pantalla.blit(texto_menu, texto_menu.get_rect(center=self.rect_volver_menu.center))

            self.rect_mute = pygame.Rect(ANCHO - 100, ALTO - 30, 90, 22)
            muteado = not self.sound_manager.habilitado
            color_mute = (150, 60, 60) if muteado else (60, 150, 90)
            pygame.draw.rect(self.pantalla, color_mute, self.rect_mute, border_radius=8)
            pygame.draw.rect(self.pantalla, (255, 255, 255), self.rect_mute, width=2, border_radius=8)
            texto_mute = self.fuente_botones.render("Muteado (M)" if muteado else "Sonido (M)", True, (255, 255, 255))
            self.pantalla.blit(texto_mute, texto_mute.get_rect(center=self.rect_mute.center))

            pygame.display.flip()
            self.reloj.tick(60)
