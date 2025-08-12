import pygame
from settings import ANCHO, ALTO, ALTURA_SUELO
from entities.players.robot import Robot
from entities.players.robot_estatico import RobotEstatico
from levels.map_loader import load_static_map, load_static_map_laterales
from systems.collision import check_collisions, check_collisions_laterales_esquinas
from entities.weapons.granada import Granada
from entities.weapons.misil import Misil
from systems.aim_indicator import AimIndicator
from ui.hud import HUDArmas

class Game:
    def __init__(self):
        pygame.init()
        self.pantalla = pygame.display.set_mode((ANCHO, ALTO))
        pygame.display.set_caption("Blastron Clone - Plataformas")
        self.reloj = pygame.time.Clock()

        self.robot = Robot(x=ANCHO // 2 - 30, y=ALTO - 90 - ALTURA_SUELO)
        self.tiles = load_static_map()
        self.tiles_laterales = load_static_map_laterales()
        
        # Armas
        self.granadas = []  # Lista para granadas
        self.misiles = []  # Lista para misiles

        self.mouse_click_sostenido = False
        self.fondo = pygame.image.load("assets/maps/fondo.png").convert()
        self.fondo = pygame.transform.smoothscale(self.fondo, (ANCHO, ALTO))
        self.fuente_muerte = pygame.font.SysFont("Verdana", 48, bold=True)

        # Indicador de puntería
        self.aim = AimIndicator(self.robot.get_centro())

        # Hud armas
        self.hud_armas = HUDArmas(['granada', 'misil'], posicion=(10, 10))
        self.font = pygame.font.SysFont('Arial', 20)

    def run(self):
        self.robots_estaticos = []  # Lista para robots estáticos

        while True:
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    pygame.quit()
                    return

                # Manejar selección de arma desde HUD
                arma_seleccionada = self.hud_armas.manejar_evento(evento)
                if arma_seleccionada is not None:
                    if arma_seleccionada == "spawn_robot":
                        # Crear robot estático en el centro de la pantalla
                        nuevo_robot = RobotEstatico(400, 300)
                        self.robots_estaticos.append(nuevo_robot)
                    else:
                        self.robot.arma_equipada = arma_seleccionada

                if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                    if not self.mouse_click_sostenido:
                        # Verificar si el click fue dentro de algún botón del HUD
                        clic_sobre_hud = False
                        pos_click = evento.pos
                        for _, rect in self.hud_armas.botones:
                            if rect.collidepoint(pos_click):
                                clic_sobre_hud = True
                                break

                        # Solo disparar si NO se clickeó sobre el HUD y hay arma equipada
                        if not clic_sobre_hud and self.robot.arma_equipada not in [None, 'nada']:
                            origen, vel_x, vel_y = self.aim.get_datos_disparo()
                            if self.robot.arma_equipada == 'granada':
                                granada = Granada(origen[0], origen[1], vel_x, vel_y)
                                self.granadas.append(granada)
                            elif self.robot.arma_equipada == 'misil':
                                misil = Misil(origen[0], origen[1], vel_x, vel_y)
                                self.misiles.append(misil)

                            self.mouse_click_sostenido = True

                if evento.type == pygame.MOUSEBUTTONUP and evento.button == 1:
                    self.mouse_click_sostenido = False

            keys = pygame.key.get_pressed()
            self.robot.update(keys)
            if keys[pygame.K_BACKSPACE]:
                self.robot.take_damage(50)

            # Actualizar robots estáticos (solo gravedad/colisiones)
            for robot_estatico in self.robots_estaticos:
                robot_estatico.update(self.tiles)

            # Colisiones jugador
            check_collisions(self.robot, self.tiles)
            check_collisions_laterales_esquinas(self.robot, self.tiles_laterales)

            # Dibujar fondo y plataformas
            self.pantalla.blit(self.fondo, (0, 0))
            for tile in self.tiles:
                tile.draw(self.pantalla)
            for tile in self.tiles_laterales:
                tile.draw(self.pantalla)

            # Dibujar robots
            self.robot.draw(self.pantalla)
            for robot_estatico in self.robots_estaticos:
                robot_estatico.draw(self.pantalla)

            # Actualizar y dibujar granadas
            for granada in self.granadas[:]:
                granada.update(self.tiles, self.robot)
                for robot_estatico in self.robots_estaticos:
                    granada.rebote_con_robot(robot_estatico)
                    if granada.explotado and granada.estado == "explode" and not granada.ya_hizo_dano:
                        if granada.get_hitbox().colliderect(robot_estatico.get_rect()):
                            robot_estatico.take_damage(70)
                            granada.ya_hizo_dano = True

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

            # Actualizar y dibujar misiles
            for misil in self.misiles[:]:
                misil.update(self.tiles, self.robot)
                for robot_estatico in self.robots_estaticos:
                    misil.colisiona_con_robot(robot_estatico)
                    if misil.explotado and misil.estado == "explode" and not misil.ya_hizo_dano:
                        if misil.get_hitbox().colliderect(robot_estatico.get_rect()):
                            robot_estatico.take_damage(50)
                            misil.ya_hizo_dano = True

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

            # Mostrar puntería si arma equipada
            if self.robot.arma_equipada not in [None, 'nada']:
                mouse_pos = pygame.mouse.get_pos()
                self.aim.origen = self.robot.get_centro()
                self.aim.update(mouse_pos)
                self.aim.draw(self.pantalla)

            # HUD
            self.hud_armas.draw(self.pantalla, self.font)

            # Mensajes de muerte
            self.robot.draw_death_message(self.pantalla, self.fuente_muerte)
            for robot_estatico in self.robots_estaticos:
                robot_estatico.draw_death_message(self.pantalla, self.fuente_muerte)

            pygame.display.flip()
            self.reloj.tick(60)
