import pygame
from utils.loader import load_spritesheet
import time

class Robot:
    def __init__(self, x, y):
        self.spawn_x = x
        self.spawn_y = y
        self.reset()

        self.width = 60
        self.height = 90

        self.animations = {
            "idle": load_spritesheet("assets/robots/idle.png", 1, self.width, self.height),
            "run": load_spritesheet("assets/robots/run.png", 6, self.width, self.height),
            "jump": load_spritesheet("assets/robots/jump.png", 1, self.width, self.height),
            "death": load_spritesheet("assets/robots/death.png", 6, self.width, self.height),
        }

    def reset(self):
        self.x = self.spawn_x
        self.y = self.spawn_y
        self.vel_x = 0
        self.vel_y = 0
        self.on_ground = False
        self.facing_right = True
        self.jump_power = 15
        self.gravity = 1
        self.speed = 2.5
        self.health = 200
        self.is_dead = False
        self.dead_timer = 0

        self.current_animation = "idle"
        self.frame_index = 0
        self.frame_timer = 0
        self.image = None

    def get_rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)

    def take_damage(self, amount):
        if not self.is_dead:
            self.health -= amount
            if self.health <= 0:
                self.die()

    def die(self):
        self.is_dead = True
        self.frame_index = 0
        self.dead_timer = pygame.time.get_ticks()

    def update(self, keys):
        if self.is_dead:
            self.current_animation = "death"
            self.frame_timer += 1
            if self.frame_timer >= 10:
                self.frame_timer = 0
                if self.frame_index < len(self.animations["death"]) - 1:
                    self.frame_index += 1

            # Reinicia tras 2 segundos muerto
            if pygame.time.get_ticks() - self.dead_timer > 2000:
                self.reset()
            self.image = self.animations["death"][self.frame_index]
            if not self.facing_right:
                self.image = pygame.transform.flip(self.image, True, False)
            return

        # Movimiento
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

        # Dibujar barra de vida encima del robot
        bar_width = 60
        bar_height = 10
        health_ratio = max(self.health / 200, 0)
        health_color = (200, 0, 0) if self.health < 60 else (0, 200, 0)

        # Fondo de la barra
        pygame.draw.rect(pantalla, (50, 50, 50), (self.x, self.y - 15, bar_width, bar_height))
        # Vida actual
        pygame.draw.rect(pantalla, health_color, (self.x, self.y - 15, bar_width * health_ratio, bar_height))
