import math
import pygame
from utils.loader import load_spritesheet

class Misil:
    def __init__(self, x, y, vel_x, vel_y):
        self.x = x
        self.y = y
        self.width = 40
        self.height = 40

        # Estado y animación
        self.frames = load_spritesheet("assets/weapons/misil_sprite.png", 3, self.width, self.height)
        self.estado = "fly"  # fly -> explode -> done
        self.frame_index = 0
        self.timer = 0
        self.vel_anim = 100  # ms por frame

        # Física
        self.vel_x = vel_x
        self.vel_y = vel_y
        self.gravity = 0.3
        self.friccion_aire = 0.99

        # Tiempos
        self.tiempo_post_explosion = 300
        self.tiempo_eliminar = None
        self.spawn_time = pygame.time.get_ticks()
        self.min_arming_time = 200

        # Flags
        self.muerto = False
        self.ya_hizo_dano = False
        self.explotado = False

    def get_rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)

    def get_hitbox(self):
        padding_x = 4
        padding_y = 8
        rect = self.get_rect()
        return pygame.Rect(
            rect.left - padding_x,
            rect.top - padding_y,
            rect.width + 2 * padding_x,
            rect.height + 2 * padding_y
        )

    def update(self, tiles, robot):
        ahora = pygame.time.get_ticks()

        if self.estado == "fly":
            self.vel_y += self.gravity
            velocidad_max = max(abs(self.vel_x), abs(self.vel_y))
            pasos = int(velocidad_max // 4) + 1
            dx = self.vel_x / pasos
            dy = self.vel_y / pasos

            for _ in range(pasos):
                self.x += dx
                self.y += dy
                if ahora - self.spawn_time >= self.min_arming_time:
                    if self.colisiona_con_tiles(tiles) or self.colisiona_con_robot(robot):
                        self.explotar()
                        break

            self.vel_x *= self.friccion_aire

            if ahora - self.timer > self.vel_anim:
                self.timer = ahora
                self.frame_index = (self.frame_index + 1) % 2

        elif self.estado == "explode":
            if ahora >= self.tiempo_eliminar:
                self.estado = "done"
                self.muerto = True

    def explotar(self):
        if self.estado != "explode":
            self.estado = "explode"
            self.explotado = True
            self.frame_index = 2
            self.tiempo_eliminar = pygame.time.get_ticks() + self.tiempo_post_explosion
            self.vel_x = 0
            self.vel_y = 0

    def draw(self, pantalla):
        if self.estado == "fly":
            # Calcular ángulo según dirección del misil
            angulo = math.degrees(math.atan2(-self.vel_y, self.vel_x))
            
            # Rotar el frame actual
            imagen_rotada = pygame.transform.rotozoom(self.frames[self.frame_index], angulo, 1)
            rect_centrado = imagen_rotada.get_rect(center=(self.x + self.width // 2, self.y + self.height // 2))
            pantalla.blit(imagen_rotada, rect_centrado.topleft)

        elif self.estado == "explode":
            escala_factor = 1.5
            imagen_explode = pygame.transform.scale(
                self.frames[self.frame_index],
                (int(self.width * escala_factor), int(self.height * escala_factor))
            )
            x_centrado = int(self.x - (self.width * (escala_factor - 1) / 2))
            y_centrado = int(self.y - (self.height * (escala_factor - 1) / 2))
            pantalla.blit(imagen_explode, (x_centrado, y_centrado))
            

    def colisiona_con_tiles(self, tiles):
        rect = self.get_rect()
        for tile in tiles:
            if rect.colliderect(tile.rect):
                return True
        return False

    def colisiona_con_robot(self, robot):
        rect = self.get_rect()
        if rect.colliderect(robot.get_hitbox_lateral()):
            return True
        return False

    