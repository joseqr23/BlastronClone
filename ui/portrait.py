import pygame

class Portrait:
    def __init__(self, image_path, size=(50, 50)):
        image = pygame.image.load(image_path).convert_alpha()
        self.image = pygame.transform.smoothscale(image, size)

    def draw(self, pantalla, position):
        pantalla.blit(self.image, position)
