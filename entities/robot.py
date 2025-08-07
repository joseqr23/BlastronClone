import pygame
from utils.loader import load_spritesheet

class Robot:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vel_x = 0
        self.vel_y = 0
        self.width = 60
        self.height = 90
        self.on_ground = False
        self.facing_right = True
        self.jump_power = 15
        self.gravity = 1
        self.speed = 2.5

        # Vida
        self.vida = 200
        self.vida_maxima = 200

        self.animations = {
            "idle": load_spritesheet("assets/robots/idle.png", 1, self.width, self.height),
            "run": load_spritesheet("assets/robots/run.png", 6, self.width, self.height),
            "jump": load_spritesheet("assets/robots/jump.png", 1, self.width, self.height),
        }
        self.current_animation = "idle"
        self.frame_index = 0
        self.frame_timer = 0
        self.image = self.animations[self.current_animation][0]

    def get_rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)

    def update(self, keys):
        self.vel_x = 0
        if keys[pygame.K_LEFT]:
            self.vel_x = -self.speed
            self.facing_right = False
        elif keys[pygame.K_RIGHT]:
            self.vel_x = self.speed
            self.facing_right = True

        self.x += self.vel_x

        if keys[pygame.K_SPACE] and self.on_ground:
            self.vel_y = -self.jump_power
            self.on_ground = False

        self.vel_y += self.gravity
        self.y += self.vel_y

        # Animaciones
        if not self.on_ground:
            self.current_animation = "jump"
            self.frame_index = 0
        elif self.vel_x != 0:
            self.current_animation = "run"
            self.frame_timer += 1
            if self.frame_timer >= 5:
                self.frame_timer = 0
                self.frame_index = (self.frame_index + 1) % len(self.animations["run"])
        else:
            self.current_animation = "idle"
            self.frame_index = 0

        self.image = self.animations[self.current_animation][self.frame_index]
        if not self.facing_right:
            self.image = pygame.transform.flip(self.image, True, False)

    def draw(self, pantalla):
        pantalla.blit(self.image, (self.x, self.y))
        self.dibujar_barra_vida(pantalla)

    def dibujar_barra_vida(self, pantalla):
        barra_ancho = 60
        barra_alto = 8
        x_barra = self.x + self.width // 2 - barra_ancho // 2
        y_barra = self.y - 15

        vida_ratio = self.vida / self.vida_maxima
        ancho_vida = int(barra_ancho * vida_ratio)

        # Fondo gris
        pygame.draw.rect(pantalla, (100, 100, 100), (x_barra, y_barra, barra_ancho, barra_alto))
        # Vida verde
        pygame.draw.rect(pantalla, (0, 255, 0), (x_barra, y_barra, ancho_vida, barra_alto))
        # Borde negro
        pygame.draw.rect(pantalla, (0, 0, 0), (x_barra, y_barra, barra_ancho, barra_alto), 1)
