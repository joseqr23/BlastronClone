import pygame
from settings import ANCHO, ALTO, ALTURA_SUELO
from entities.robot import Robot
from levels.map_loader import load_static_map
from systems.collision import check_collisions
from entities.granada import Granada

class Game:
    def __init__(self):
        pygame.init()
        self.pantalla = pygame.display.set_mode((ANCHO, ALTO))
        pygame.display.set_caption("Blastron Clone - Plataformas")
        self.reloj = pygame.time.Clock()

        self.robot = Robot(x=ANCHO // 2 - 30, y=ALTO - 90 - ALTURA_SUELO)
        self.tiles = load_static_map()

        self.granadas = [] # Granadas

        self.fondo = pygame.image.load("assets/maps/fondo.png").convert()
        self.fondo = pygame.transform.smoothscale(self.fondo, (ANCHO, ALTO))
        
        self.fuente_muerte = pygame.font.SysFont("Verdana", 48, bold=True)

    def run(self):
        while True:
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    pygame.quit()
                    return

            keys = pygame.key.get_pressed()
            self.robot.update(keys)

            # Probar que baje la vida
            # if keys[pygame.K_DOWN]:
            #     self.robot.vida = max(0, self.robot.vida - 1)

            if pygame.mouse.get_pressed()[0]:  # Botón izquierdo
                mouse_x, mouse_y = pygame.mouse.get_pos()
                granada = Granada(self.robot.x + self.robot.width // 2, self.robot.y, mouse_x, mouse_y)
                self.granadas.append(granada)


            if keys[pygame.K_d]:
                self.robot.take_damage(50)


            check_collisions(self.robot, self.tiles)

            self.pantalla.blit(self.fondo, (0, 0))

            for tile in self.tiles:
                tile.draw(self.pantalla)

            self.robot.draw(self.pantalla)

            for granada in self.granadas:
              granada.update()
              granada.draw(self.pantalla)
                
            self.robot.draw_death_message(self.pantalla, self.fuente_muerte)

            pygame.display.flip()
            self.reloj.tick(60)
