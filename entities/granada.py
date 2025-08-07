import pygame
import math
from utils.loader import load_spritesheet

class Granada:
    def __init__(self, x, y, objetivo_x, objetivo_y):
        self.x = x
        self.y = y
        self.width = 40
        self.height = 40

        # Cargar sprites
        self.frames = load_spritesheet("assets/weapons/grenade.png", 3, self.width, self.height)
        self.estado = "idle"  # puede ser idle, warning, explode
        self.frame_index = 0
        self.timer = 0
        self.explotar_en = 180  # frames antes de explotar (3 segundos a 60fps)
        self.explotado = False

        # Física
        self.vel_x, self.vel_y = self.calcular_velocidad(objetivo_x, objetivo_y)
        self.gravity = 0.5

    def calcular_velocidad(self, objetivo_x, objetivo_y):
        # Calcula velocidad inicial para lanzar hacia objetivo
        dx = objetivo_x - self.x
        dy = objetivo_y - self.y
        distancia = math.hypot(dx, dy)
        if distancia == 0:
            return 0, 0
        fuerza = 10  # ajustable
        return (dx / distancia) * fuerza, (dy / distancia) * fuerza

    def get_rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)

    def update(self):
        if self.explotado:
            return

        self.vel_y += self.gravity
        self.x += self.vel_x
        self.y += self.vel_y

        self.timer += 1
        if self.timer > self.explotar_en:
            self.estado = "explode"
            self.explotado = True
        elif self.timer > self.explotar_en - 30:
            self.estado = "warning"

    def draw(self, pantalla):
        if self.estado == "idle":
            imagen = self.frames[0]
        elif self.estado == "warning":
            imagen = self.frames[1]
        elif self.estado == "explode":
            imagen = self.frames[2]

        pantalla.blit(imagen, (int(self.x), int(self.y)))
