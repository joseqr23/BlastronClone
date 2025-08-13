import pygame
from utils.loader import load_spritesheet
import time
import random

class Robot:
    COLORES_NOMBRES = [
        (0, 0, 255),     # Azul
        (0, 200, 0),     # Verde
        (200, 0, 0),     # Rojo
        (255, 140, 0),   # Naranja
        (128, 0, 128),   # Morado
    ]

    def __init__(self, x, y, nombre_jugador):
        self.spawn_x = x
        self.spawn_y = y
        self.nombre = nombre_jugador
        
        self.font_nombre = pygame.font.SysFont("Arial", 16, bold=True)  # Fuente para el nombre
        self.color_nombre = self.COLORES_NOMBRES[hash(nombre_jugador) % len(self.COLORES_NOMBRES)] # Asignar color único según el nombre
        
        self.reset()
        self.width = 60
        self.height = 90

        self.animations = {
            "idle": load_spritesheet("assets/robots/idle.png", 1, self.width, self.height),
            "run": load_spritesheet("assets/robots/run.png", 6, self.width, self.height),
            "jump": load_spritesheet("assets/robots/jump.png", 1, self.width, self.height),
            "death": load_spritesheet("assets/robots/death.png", 6, self.width, self.height),
        }

        self.death_sound = pygame.mixer.Sound("assets/sfx/death.mp3")
        self.death_sound.set_volume(0.5)

        self.arma_equipada = None  # 'granada', 'misil', o None
        self.es_jugador = True
        
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

        # Reaparecer en posición aleatoria
        min_x = 100
        max_x = 800
        self.x = random.randint(min_x, max_x)
        self.y = 0  # Empieza desde arriba y caerá hasta tocar plataforma

        self.vel_x = 0
        self.vel_y = 0
        self.health = 200
        self.is_dead = False
        self.frame_index = 0
        self.current_animation = "idle"

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
        self.death_sound.play()

    def manejar_controles(self, keys):
        self.vel_x = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.vel_x = -self.speed
            self.facing_right = False
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vel_x = self.speed
            self.facing_right = True

        if (keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w]) and self.on_ground:
            self.vel_y = -self.jump_power
            self.on_ground = False

    def aplicar_fisica(self):
        self.x += self.vel_x
        self.vel_y += self.gravity
        self.y += self.vel_y

    def actualizar_animacion(self):
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

        self.manejar_controles(keys)
        self.aplicar_fisica()
        self.actualizar_animacion()

    def draw(self, pantalla):
        pantalla.blit(self.image, (self.x, self.y))

        # Barra de vida
        bar_width = 60
        bar_height = 10
        health_ratio = max(self.health / 200, 0)
        health_color = (200, 0, 0) if self.health < 60 else (0, 200, 0)

        pygame.draw.rect(pantalla, (50, 50, 50), (self.x, self.y - 15, bar_width, bar_height))
        pygame.draw.rect(pantalla, health_color, (self.x, self.y - 15, bar_width * health_ratio, bar_height))

        texto_nombre = self.font_nombre.render(self.nombre, True, self.color_nombre) # Nombre encima (color único por jugador)
        texto_rect = texto_nombre.get_rect(center=(self.x + self.width // 2, self.y - 25))
        pantalla.blit(texto_nombre, texto_rect)

    def draw_death_message(self, pantalla, fuente):
        if self.is_dead:
            fuente_grande = pygame.font.SysFont(None, 40)
            texto = fuente_grande.render(f"¡{self.nombre} ha sido detonado!", True, (255, 0, 0))
            rect = texto.get_rect(center=(pantalla.get_width() // 2, pantalla.get_height() // 2 - 200))
            pantalla.blit(texto, rect)

    def get_centro(self):
        return (self.x + self.width // 2, self.y + self.height // 2)

    def get_hitbox_lateral(self):
        rect = self.get_rect()
        nuevo_ancho = 20
        nuevo_x = rect.x + (rect.width - nuevo_ancho) // 2
        return pygame.Rect(nuevo_x, rect.y, nuevo_ancho, rect.height)