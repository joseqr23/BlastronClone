import pygame
import math
from utils.loader import load_spritesheet

class Granada:
    def __init__(self, x, y, vel_x, vel_y):
        self.x = x
        self.y = y
        self.width = 40
        self.height = 40

        # Tiempos
        self.tiempo_explosion = pygame.time.get_ticks() + 3000
        self.tiempo_post_explosion = 500
        self.tiempo_eliminar = None

        # Cargar sprites
        self.frames = load_spritesheet("assets/weapons/grenade.png", 3, self.width, self.height)
        self.estado = "idle"
        self.frame_index = 0
        self.timer = 0
        self.explotado = False
        self.muerta = False

        # Física
        self.vel_x = vel_x
        self.vel_y = vel_y
        self.gravity = 0.5
        self.friccion_aire = 0.99
        self.friccion_rebote = 0.6

        self.ya_hizo_dano = False

    def get_rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)

    def update(self):
        ahora = pygame.time.get_ticks()

        # Cambiar estado según tiempo
        if not self.explotado and ahora >= self.tiempo_explosion:
            self.estado = "explode"
            self.explotado = True
            self.tiempo_eliminar = ahora + self.tiempo_post_explosion
        elif not self.explotado and self.tiempo_explosion - ahora <= 500:
            self.estado = "warning"
        elif not self.explotado:
            self.estado = "idle"

        # Física
        if not self.explotado:
            self.vel_y += self.gravity
            self.x += self.vel_x
            self.y += self.vel_y

            self.vel_x *= self.friccion_aire

        # Eliminar después de explotar
        if self.explotado and ahora >= self.tiempo_eliminar:
            self.estado = "done"
            self.muerta = True

    def draw(self, pantalla):
        if self.estado == "idle":
            imagen = self.frames[0]
        elif self.estado == "warning":
            imagen = self.frames[1]
        elif self.estado == "explode":
            imagen = self.frames[2]
        else:
            return
        pantalla.blit(imagen, (int(self.x), int(self.y)))

    def rebote_con_tiles(self, tiles):
        rect = self.get_rect()
        for tile in tiles:
            if rect.colliderect(tile.rect):
                # Rebote en el piso
                if self.vel_y >= 0 and rect.bottom <= tile.rect.bottom:
                    self.y = tile.rect.top - self.height
                    self.vel_y *= -self.friccion_rebote

                # Rebote en el techo
                elif self.vel_y < 0 and rect.top >= tile.rect.bottom:
                    self.y = tile.rect.bottom
                    self.vel_y *= -self.friccion_rebote

                # Rebote lateral derecha
                elif abs(rect.right - tile.rect.left) < 10 and self.vel_x > 0:
                    self.x = tile.rect.left - self.width
                    self.vel_x *= -self.friccion_rebote

                # Rebote lateral izquierda
                elif abs(rect.left - tile.rect.right) < 10 and self.vel_x < 0:
                    self.x = tile.rect.right
                    self.vel_x *= -self.friccion_rebote

                # Evitar micro rebotes infinitos
                if abs(self.vel_x) < 0.1:
                    self.vel_x = 0
                if abs(self.vel_y) < 0.1:
                    self.vel_y = 0
