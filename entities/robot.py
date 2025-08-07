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

        # Animaciones
        self.animations = {
            "idle": load_spritesheet("assets/robots/idle.png", 1, self.width, self.height),
            "run": load_spritesheet("assets/robots/run.png", 6, self.width, self.height),
            "jump": load_spritesheet("assets/robots/jump.png", 1, self.width, self.height),
        }
        self.current_animation = "idle"
        self.frame_index = 0
        self.frame_timer = 0
        self.image = self.animations[self.current_animation][0]

    def set_animation(self, name):
        if self.current_animation != name:
            self.current_animation = name
            self.frame_index = 0
            self.frame_timer = 0

    def update(self, keys, suelo_y):
        # Movimiento lateral
        self.vel_x = 0
        if keys[pygame.K_LEFT]:
            self.vel_x = -self.speed
            self.facing_right = False
        elif keys[pygame.K_RIGHT]:
            self.vel_x = self.speed
            self.facing_right = True

        self.x += self.vel_x

        # Salto
        if keys[pygame.K_SPACE] and self.on_ground:
            self.vel_y = -self.jump_power
            self.on_ground = False

        # Gravedad
        self.y += self.vel_y
        self.vel_y += self.gravity

        # Suelo
        if self.y >= suelo_y:
            self.y = suelo_y
            self.vel_y = 0
            self.on_ground = True
        else:
            self.on_ground = False

        # Animación según estado
        if not self.on_ground:
            self.set_animation("jump")
        elif self.vel_x != 0:
            self.set_animation("run")
            self.frame_timer += 1
            if self.frame_timer >= 5:
                self.frame_timer = 0
                self.frame_index = (self.frame_index + 1) % len(self.animations["run"])
        else:
            self.set_animation("idle")

        # Frame actual
        if self.current_animation == "idle" or self.current_animation == "jump":
            self.frame_index = 0  # esas solo tienen 1 frame

        self.image = self.animations[self.current_animation][self.frame_index]
        if not self.facing_right:
            self.image = pygame.transform.flip(self.image, True, False)

    def draw(self, pantalla):
        pantalla.blit(self.image, (self.x, self.y))
