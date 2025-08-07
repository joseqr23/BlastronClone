import pygame

class Tile:
    def __init__(self, x, y, width, height, color=None):
        self.rect = pygame.Rect(x, y, width, height)
        self.color = color  # Si es None, será invisible

    def draw(self, pantalla):
        if self.color:
            pygame.draw.rect(pantalla, self.color, self.rect)
