import pygame
from settings import ANCHO, ALTO, ALTURA_SUELO
from entities.players.robot import Robot
from levels.map_loader import load_static_map, load_static_map_laterales
from systems.collision import check_collisions, check_collisions_laterales_esquinas
from entities.weapons.granada import Granada
from systems.aim_indicator import AimIndicator

class Game:
    def __init__(self):
        pygame.init()
        self.pantalla = pygame.display.set_mode((ANCHO, ALTO))
        pygame.display.set_caption("Blastron Clone - Plataformas")
        self.reloj = pygame.time.Clock()

        self.robot = Robot(x=ANCHO // 2 - 30, y=ALTO - 90 - ALTURA_SUELO)
        self.tiles = load_static_map()
        self.tiles_laterales = load_static_map_laterales()
        self.granadas = []

        self.mouse_click_sostenido = False
        self.fondo = pygame.image.load("assets/maps/fondo.png").convert()
        self.fondo = pygame.transform.smoothscale(self.fondo, (ANCHO, ALTO))
        self.fuente_muerte = pygame.font.SysFont("Verdana", 48, bold=True)

        # Indicador de puntería
        self.aim = AimIndicator(self.robot.get_centro())

    def run(self):
        while True:
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    pygame.quit()
                    return

                if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                    if not self.mouse_click_sostenido:
                        # Disparar desde el origen del indicador
                        origen, vel_x, vel_y = self.aim.get_datos_disparo()
                        granada = Granada(origen[0], origen[1], vel_x, vel_y)
                        self.granadas.append(granada)
                        self.mouse_click_sostenido = True

                if evento.type == pygame.MOUSEBUTTONUP and evento.button == 1:
                    self.mouse_click_sostenido = False

            keys = pygame.key.get_pressed()
            self.robot.update(keys)
            if keys[pygame.K_BACKSPACE]:
                self.robot.take_damage(50)

            # Llamar a collisions
            check_collisions(self.robot, self.tiles) # Tu función original, para piso y techo
            check_collisions_laterales_esquinas(self.robot, self.tiles_laterales)  # Solo para esquinas lateralmente


            self.pantalla.blit(self.fondo, (0, 0))
            for tile in self.tiles:
                tile.draw(self.pantalla)
            for tile in self.tiles_laterales:
                tile.draw(self.pantalla)    

            self.robot.draw(self.pantalla)

            # Actualizar granadas
            for granada in self.granadas[:]:
                granada.update(self.tiles, self.robot)
                if not granada.explotado:
                    granada.rebote_con_tiles(self.tiles)  # Rebote con plataformas
                    granada.rebote_con_robot(self.robot)  # Rebote con robot

                if granada.explotado and granada.estado == "explode" and not granada.ya_hizo_dano:
                    if granada.get_hitbox().colliderect(self.robot.get_rect()):
                        self.robot.take_damage(50)
                        granada.ya_hizo_dano = True

                if granada.estado == "done":
                    self.granadas.remove(granada)

            for granada in self.granadas:
                granada.draw(self.pantalla)

            # Indicador siempre visible desde el centro del robot
            mouse_pos = pygame.mouse.get_pos()
            self.aim.origen = self.robot.get_centro()
            self.aim.update(mouse_pos)
            self.aim.draw(self.pantalla)

            self.robot.draw_death_message(self.pantalla, self.fuente_muerte)

            pygame.display.flip()
            self.reloj.tick(60)
