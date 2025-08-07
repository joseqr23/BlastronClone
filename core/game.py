import pygame
import sys
from settings import ANCHO, ALTO, ALTURA_SUELO
from entities.robot import Robot

class Game:
    def __init__(self):
        pygame.init()
        self.pantalla = pygame.display.set_mode((ANCHO, ALTO))
        pygame.display.set_caption("Robot Animado")

        self.fondo = pygame.image.load("assets/maps/fondo.png").convert()
        self.fondo = pygame.transform.smoothscale(self.fondo, (ANCHO, ALTO))

        self.robot = Robot(x=ANCHO // 2 - 30, y=ALTO - 90 - ALTURA_SUELO)

        self.reloj = pygame.time.Clock()

    def run(self):
        while True:
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

            teclas = pygame.key.get_pressed()
            suelo_y = ALTO - self.robot.height - ALTURA_SUELO
            self.robot.update(teclas, suelo_y)

            self.pantalla.blit(self.fondo, (0, 0))
            self.robot.draw(self.pantalla)

            pygame.display.flip()
            self.reloj.tick(60)
