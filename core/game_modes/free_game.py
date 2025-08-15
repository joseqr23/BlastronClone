import pygame
from settings import ANCHO, ALTO, ALTURA_SUELO
from entities.players.robot import Robot
from entities.players.robot_estatico import RobotEstatico
from entities.weapons.granada import Granada
from entities.weapons.misil import Misil
from systems.collision import check_collisions, check_collisions_laterales_esquinas
from systems.aim_indicator import AimIndicator
from core.game_modes.base_game import BaseGame
from ui.hud import HUDPuntajes
from utils.paths import resource_path  # Para rutas seguras

class FreeGame(BaseGame):
    def __init__(self, nombre_jugador, personaje):
        super().__init__(nombre_jugador=nombre_jugador)
        self.robot = Robot(
            x=ANCHO // 2 - 30,
            y=ALTO - 90 - ALTURA_SUELO,
            nombre_jugador=nombre_jugador,
            nombre_robot=personaje
        )
        self.robots_estaticos = []
        self.aim = AimIndicator(self.robot.get_centro())
        self.puntajes[self.robot] = 0
        self.hud_puntajes = HUDPuntajes(self)

    def run(self):
        while True:
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    pygame.quit()
                    return

                # Pasar eventos al chat
                self.chat.handle_event(evento)

                arma_seleccionada = self.hud_armas.manejar_evento(evento)
                if arma_seleccionada is not None:
                    if arma_seleccionada == "spawn_robot":
                        nuevo_robot = RobotEstatico(400, 300)
                        self.robots_estaticos.append(nuevo_robot)
                    else:
                        self.robot.arma_equipada = arma_seleccionada

                if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                    if not self.mouse_click_sostenido:
                        clic_sobre_hud = any(
                            rect.collidepoint(evento.pos) for _, rect in self.hud_armas.botones
                        )
                        if not clic_sobre_hud and self.robot.arma_equipada not in [None, 'nada']:
                            self.disparar_arma()
                            self.mouse_click_sostenido = True

                if evento.type == pygame.MOUSEBUTTONUP and evento.button == 1:
                    self.mouse_click_sostenido = False

            keys = pygame.key.get_pressed()
            self.robot.update(keys)
            if keys[pygame.K_DELETE]:
                self.robot.take_damage(50)

            for robot_estatico in self.robots_estaticos:
                robot_estatico.update(self.tiles)

            check_collisions(self.robot, self.tiles)
            check_collisions_laterales_esquinas(self.robot, self.tiles_laterales)

            self.draw_scene()

            # Dibujar personajes
            self.robot.draw(self.pantalla)
            for robot_estatico in self.robots_estaticos:
                robot_estatico.draw(self.pantalla)

            # Armas
            self.actualizar_y_dibujar_granadas()
            self.actualizar_y_dibujar_misiles()

            # Indicador de mira
            if self.robot.arma_equipada not in [None, 'nada']:
                mouse_pos = pygame.mouse.get_pos()
                self.aim.origen = self.robot.get_centro()
                self.aim.update(mouse_pos)
                self.aim.draw(self.pantalla)

            # HUDs
            self.hud_armas.draw(self.pantalla, self.font)
            self.hud_puntajes.draw(self.pantalla)

            # Mensajes de muerte
            self.robot.draw_death_message(self.pantalla, self.fuente_muerte)
            for robot_estatico in self.robots_estaticos:
                robot_estatico.draw_death_message(self.pantalla, self.fuente_muerte)

            # Chat
            self.chat.draw(self.pantalla)

            pygame.display.flip()
            self.reloj.tick(60)

    def disparar_arma(self):
        origen, vel_x, vel_y = self.aim.get_datos_disparo()
        if self.robot.arma_equipada == 'granada':
            ancho, alto = Granada.ANCHO, Granada.ALTO
            origen, vel_x, vel_y = self.aim.get_datos_disparo(ancho, alto)
            self.granadas.append(Granada(origen[0], origen[1], vel_x, vel_y))
        elif self.robot.arma_equipada == 'misil':
            ancho, alto = Misil.ANCHO, Misil.ALTO
            origen, vel_x, vel_y = self.aim.get_datos_disparo(ancho, alto)
            self.misiles.append(Misil(origen[0], origen[1], vel_x, vel_y))

    def actualizar_y_dibujar_granadas(self):
        for granada in self.granadas[:]:
            granada.update(self.tiles, self.robot)
            for robot_estatico in self.robots_estaticos:
                granada.rebote_con_robot(robot_estatico)
                if granada.explotado and granada.estado == "explode":
                    if robot_estatico not in granada.danados and granada.get_hitbox().colliderect(robot_estatico.get_rect()):
                        robot_estatico.take_damage(70)
                        puntos = 70
                        if robot_estatico.health <= 0:
                            puntos *= 2
                        self.puntajes[self.robot] += puntos
                        granada.danados.add(robot_estatico)
            if not granada.explotado:
                granada.rebote_con_tiles(self.tiles)
                granada.rebote_con_robot(self.robot)
            elif granada.explotado and granada.estado == "explode" and not granada.ya_hizo_dano:
                if granada.get_hitbox().colliderect(self.robot.get_rect()):
                    self.robot.take_damage(70)
                    granada.ya_hizo_dano = True
            if granada.estado == "done":
                self.granadas.remove(granada)
        for granada in self.granadas:
            granada.draw(self.pantalla)

    def actualizar_y_dibujar_misiles(self):
        for misil in self.misiles[:]:
            misil.update(self.tiles, self.robot)
            for robot_estatico in self.robots_estaticos:
                misil.colisiona_con_robot(robot_estatico)
                if misil.explotado and misil.estado == "explode":
                    if robot_estatico not in misil.danados and misil.get_hitbox().colliderect(robot_estatico.get_rect()):
                        robot_estatico.take_damage(50)
                        puntos = 50
                        if robot_estatico.health <= 0:
                            puntos *= 2
                        self.puntajes[self.robot] += puntos
                        misil.danados.add(robot_estatico)
            if not misil.explotado:
                misil.colisiona_con_tiles(self.tiles)
                misil.colisiona_con_robot(self.robot)
            elif misil.explotado and misil.estado == "explode" and not misil.ya_hizo_dano:
                if misil.get_hitbox().colliderect(self.robot.get_rect()):
                    self.robot.take_damage(50)
                    misil.ya_hizo_dano = True
            if misil.estado == "done":
                self.misiles.remove(misil)
        for misil in self.misiles:
            misil.draw(self.pantalla)
