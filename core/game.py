import pygame
from settings import ANCHO, ALTO, ALTURA_SUELO
from entities.players.robot import Robot
from levels.map_loader import load_static_map, load_static_map_laterales
from systems.collision import check_collisions, check_collisions_laterales_esquinas
from entities.weapons.granada import Granada
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
        self.granadas = []

        self.mouse_click_sostenido = False
        self.fondo = pygame.image.load("assets/maps/fondo.png").convert()
        self.fondo = pygame.transform.smoothscale(self.fondo, (ANCHO, ALTO))
        self.fuente_muerte = pygame.font.SysFont("Verdana", 48, bold=True)

        # Indicador de puntería
        self.aim = AimIndicator(self.robot.get_centro())

        # Hud armas
        self.hud_armas = HUDArmas(['granada', 'misil'], posicion=(10,10))
        self.font = pygame.font.SysFont('Arial', 20)

    def run(self):
        while True:
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    pygame.quit()
                    return

                # Manejar selección de arma desde HUD
                arma_seleccionada = self.hud_armas.manejar_evento(evento)
                if arma_seleccionada is not None:
                    self.robot.arma_equipada = arma_seleccionada

                if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                    if not self.mouse_click_sostenido:

                        # Verificar si el click fue dentro de algún botón del HUD armas
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
                                # Crear misil aquí cuando esté listo
                                pass

                            self.mouse_click_sostenido = True

                if evento.type == pygame.MOUSEBUTTONUP and evento.button == 1:
                    self.mouse_click_sostenido = False

            keys = pygame.key.get_pressed()
            self.robot.update(keys)
            if keys[pygame.K_BACKSPACE]:
                self.robot.take_damage(50)

            # Colisiones
            check_collisions(self.robot, self.tiles)  # Piso y techo
            check_collisions_laterales_esquinas(self.robot, self.tiles_laterales)  # Laterales

            # Dibujar fondo y plataformas
            self.pantalla.blit(self.fondo, (0, 0))
            for tile in self.tiles:
                tile.draw(self.pantalla)
            for tile in self.tiles_laterales:
                tile.draw(self.pantalla)

            # Dibujar robot
            self.robot.draw(self.pantalla)

            # Actualizar y dibujar granadas
            for granada in self.granadas[:]:
                granada.update(self.tiles, self.robot)
                if not granada.explotado:
                    granada.rebote_con_tiles(self.tiles)
                    granada.rebote_con_robot(self.robot)

                if granada.explotado and granada.estado == "explode" and not granada.ya_hizo_dano:
                    if granada.get_hitbox().colliderect(self.robot.get_rect()):
                        self.robot.take_damage(50)
                        granada.ya_hizo_dano = True

                if granada.estado == "done":
                    self.granadas.remove(granada)

            for granada in self.granadas:
                granada.draw(self.pantalla)

            # Aquí actualizar y dibujar misiles si los tienes
            # for misil in self.misiles[:]:
            #     misil.update(...)
            #     misil.draw(self.pantalla)
            #     ... gestión de daño y eliminación

            # Mostrar indicador de puntería solo si arma equipada no es None ni 'nada'
            if self.robot.arma_equipada not in [None, 'nada']:
                mouse_pos = pygame.mouse.get_pos()
                self.aim.origen = self.robot.get_centro()
                self.aim.update(mouse_pos)
                self.aim.draw(self.pantalla)

            # Dibujar HUD de armas
            self.hud_armas.draw(self.pantalla, self.font)

            # Mensaje de muerte del robot
            self.robot.draw_death_message(self.pantalla, self.fuente_muerte)

            pygame.display.flip()
            self.reloj.tick(60)
