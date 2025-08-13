import pygame
import math
from utils.loader import load_spritesheet

class Misil:
    ANCHO = 40
    ALTO = 40
    def __init__(self, x, y, vel_x, vel_y):
        self.x = x
        self.y = y
        self.width = Misil.ANCHO
        self.height = Misil.ALTO

        self.danados = set()  # Robots que ya recibieron daño de esta explosión
        
        # Tiempos
        self.tiempo_explosion = pygame.time.get_ticks() + 3000 # 3 segundos para explosion
        self.tiempo_explosion_otros = pygame.time.get_ticks() # inmediato para otras entidades
        self.tiempo_post_explosion = 300 # milisegundos antes de que pueda explotar
        self.tiempo_eliminar = None

        # Cargar Sprites
        self.frames = load_spritesheet("assets/weapons/misil_sprite.png", 3, self.width, self.height)
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

        self.ya_hizo_dano = False
        self.tiempo_creacion = pygame.time.get_ticks()

    def get_rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)

    def update(self, tiles, robot):
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

            # Dividir el movimiento en pasos para evitar tunneling
            pasos = int(max(abs(self.vel_x), abs(self.vel_y)) // 5) + 1
            dx = self.vel_x / pasos
            dy = self.vel_y / pasos

            for _ in range(pasos):
                self.x += dx
                self.y += dy
                self.colisiona_con_tiles(tiles)
                self.colisiona_con_robot(robot)

            self.vel_x *= self.friccion_aire

        # Eliminar después de explotar
        if self.explotado and ahora >= self.tiempo_eliminar:
            self.estado = "done"
            self.muerta = True

    def draw(self, pantalla):
        if self.estado in ("idle", "warning"):
            # Elegir frame según estado
            frame = self.frames[0] if self.estado == "idle" else self.frames[1]

            # Calcular ángulo de rotación (atan2 usa Y negativo porque en pygame la Y crece hacia abajo)
            angulo = math.degrees(math.atan2(-self.vel_y, self.vel_x))

            # Rotar manteniendo tamaño original
            imagen_rotada = pygame.transform.rotozoom(frame, angulo, 1)

            # Centrar rotación en el medio del misil
            rect_centrado = imagen_rotada.get_rect(center=(self.x + self.width // 2, self.y + self.height // 2))
            pantalla.blit(imagen_rotada, rect_centrado.topleft)

        elif self.estado == "explode":
            escala_factor = 2  # Duplicar tamaño
            imagen_explode = pygame.transform.scale(
                self.frames[2],
                (self.width * escala_factor, self.height * escala_factor)
            )
            x_centrado = int(self.x - (self.width * (escala_factor - 1) / 2))
            y_centrado = int(self.y - (self.height * (escala_factor - 1) / 2))
            pantalla.blit(imagen_explode, (x_centrado, y_centrado))

    def get_hitbox(self):
        # Extiende el rect original en ancho y alto para zona de daño
        padding_x = 4 # definir ancho de explosion
        padding_y = 8 # alto de explosion
        rect = self.get_rect()
        hitbox = pygame.Rect(
            rect.left - padding_x,
            rect.top - padding_y,
            rect.width + 2 * padding_x,
            rect.height + 2 * padding_y
        )
        return hitbox


    def colisiona_con_tiles(self, tiles):
        rect = self.get_rect()

        for tile in tiles:
            if rect.colliderect(tile.rect):
                # Forzar explosión inmediata
                if not self.explotado:
                    self.estado = "explode"
                    self.explotado = True
                    self.tiempo_eliminar = pygame.time.get_ticks() + self.tiempo_post_explosion
                return  # No seguir revisando, ya explotó

    def colisiona_con_robot(self, robot):
        ahora = pygame.time.get_ticks()

        # Si el robot es el jugador, esperar hasta tiempo_explosion
        if getattr(robot, "es_jugador", False):
            if ahora < self.tiempo_explosion:
                return
        else:  # Otras entidades: usar tiempo_explosion_otros
            if ahora < self.tiempo_explosion_otros:
                return

        rect = self.get_rect()
        robot_rect = robot.get_hitbox_lateral()
        if rect.colliderect(robot_rect):
            if not self.explotado:
                self.estado = "explode"
                self.explotado = True
                self.tiempo_eliminar = ahora + self.tiempo_post_explosion