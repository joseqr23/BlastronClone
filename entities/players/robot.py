# entities/players/robot.py
import pygame
from utils.loader import load_spritesheet
from utils.sound_manager import sound_manager
import time
import random
import os
from utils.colors import ColorManager
from utils.paths import resource_path
import math

class Robot:
    COLORES_NOMBRES = [
        (0, 0, 255),     # Azul
        (0, 200, 0),     # Verde
        (200, 0, 0),     # Rojo
        (255, 140, 0),   # Naranja
        (128, 0, 128),   # Morado
    ]

    def __init__(self, x, y, nombre_jugador, nombre_robot, es_remoto=False, vida_maxima=200, puede_reaparecer=True,
                 sprite_path=None, ancho=80, alto=110, velocidad=3.0, salto=15, ancho_aura=None, alto_aura=None):
        self.spawn_x = x
        self.spawn_y = y
        self.nombre_jugador = nombre_jugador
        self.nombre_robot = nombre_robot
        self.es_remoto = es_remoto
        self.vida_maxima = vida_maxima
        self.puede_reaparecer = puede_reaparecer
        self.width = ancho
        self.height = alto
        self.velocidad_base = velocidad
        self.salto_base = salto
        self.font_nombre = pygame.font.SysFont("Arial", 16, bold=True)  # Fuente para el nombre

        self.color_nombre = ColorManager.get_color(nombre_jugador)

        self.mensaje_chat = None
        self.mensaje_chat_expira = 0

        self.ancho_aura = ancho_aura or int(ancho * 1.4)
        self.alto_aura = alto_aura or int(alto * 1.4)
        self._aura_frame_index = 0
        self._aura_frame_timer = 0
        
        # Animaciones dinámicas según robot_name. El recorte del PNG
        # SIEMPRE usa la resolución nativa del arte (60x90, la de todos
        # los sprites existentes) — nunca self.width/self.height — para
        # no romperse si un robot (p.ej. un jefe) pide un tamaño final
        # distinto. Después, si self.width/self.height difiere de lo
        # nativo, se reescala cada frame ya recortado (ver más abajo).
        base_path = sprite_path or f"assets/robots/{self.nombre_robot}"
        idle_file = "idle.png" if os.path.exists(resource_path(base_path, "idle.png")) else "iddle.png"

        def _cargar_animacion(nombre_archivo, frames, tamano=None):
            """Detecta la resolución REAL del PNG (igual que ya hace
            weapon_loader.py con las armas) y recorta cada frame a su
            tamaño nativo para luego escalarlo al tamaño lógico pedido —
            self.width/self.height por defecto, o 'tamano' si se pasa
            explícito (usado por el aura, que puede ser más grande que el
            propio robot)."""
            ruta = f"{base_path}/{nombre_archivo}"
            hoja = pygame.image.load(ruta).convert_alpha()
            ancho_real = hoja.get_width() // frames
            alto_real = hoja.get_height()
            frames_img = load_spritesheet(ruta, frames, ancho_real, alto_real)
            ancho_final, alto_final = tamano or (self.width, self.height)
            if (ancho_real, alto_real) == (ancho_final, alto_final):
                return frames_img
            return [pygame.transform.smoothscale(f, (ancho_final, alto_final)) for f in frames_img]

        self.animations = {
            "idle": _cargar_animacion(idle_file, 1),
            "run": _cargar_animacion("run.png", 6),
            "jump": _cargar_animacion("jump.png", 1),
            "death": _cargar_animacion("death.png", 6),
        }
        # Opcionales — si el robot aún no tiene estos sprites, cae a
        # "idle" sin romper nada (solo se usan en la pantalla de podio).
        try:
            self.animations["celebration"] = _cargar_animacion("celebration.png", 6)
        except Exception:
            self.animations["celebration"] = self.animations["idle"]
        try:
            self.animations["defeated"] = _cargar_animacion("defeated.png", 6)
        except Exception:
            self.animations["defeated"] = self.animations["idle"]
        try:
            self.animations["aura_fuego"] = _cargar_animacion("aura_fuego.png", 3, tamano=(self.ancho_aura, self.alto_aura))
        except Exception:
            self.animations["aura_fuego"] = None
            
        # Inicializa la imagen para que nunca sea None
        self.image = self.animations["idle"][0] if "idle" in self.animations else pygame.Surface((self.width, self.height))
        if self.image is None:
            self.image = pygame.Surface((self.width, self.height))
            self.image.fill((255, 0, 255))  # Color de emergencia si no carga el spritesheet
        # self.death_sound = pygame.mixer.Sound("assets/sfx/death.mp3")
        # self.death_sound.set_volume(0.5)
        self.arma_equipada = None  # 'granada', 'misil', o None
        self.punto_reaparicion = None  # (x,y) fijo opcional — ver ModoBasket._asignar_equipo
        self.es_jugador = True

        # Aura pulsante opcional (ver activar_aura/desactivar_aura) — la
        # usan IAs con fases (BossController) para dar sensación de
        # furia al cambiar de fase, sin necesitar un sprite nuevo.
        self._aura_color = None
        self._aura_inicio = 0
        self._aura_hasta = None
        self._aura_pulso_ms = 550

        # Configuración inicial del robot
        self.reset()

    def reset(self):
        self.x = self.spawn_x
        self.y = self.spawn_y
        self.vel_x = 0
        self.vel_y = 0
        self.on_ground = False
        self.facing_right = True
        self.jump_power = self.salto_base
        self.gravity = 1
        self.speed = self.velocidad_base
        self.health = self.vida_maxima
        self.is_dead = False
        self.dead_timer = 0
        self.current_animation = "idle"
        self.frame_index = 0
        self.frame_timer = 0
        self.aturdido_hasta = 0
        self._aura_color = None  # una furia de la ronda/vida anterior no debe seguir en la nueva
        # Reaparecer en posición aleatoria
        # 0        100                       800       1000
        # |---------|-------------------------|----------|
        #           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
        #               zona de aparición
        if self.punto_reaparicion:
            self.x, self.y = self.punto_reaparicion
        else:
            min_x = 130 # 100
            max_x = 810 # 800
            self.x = random.randint(min_x, max_x)
            self.y = 0  # empieza desde arriba y caerá
        # Asegura que la imagen esté inicializada
        if hasattr(self, "animations") and "idle" in self.animations:
            self.image = self.animations["idle"][0]
        else:
            self.image = pygame.Surface((self.width, self.height))
            self.image.fill((255, 0, 255))

    def get_rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)

    def take_damage(self, amount):
        if not self.is_dead:
            self.health = max(0, self.health - amount)
            if self.health <= 0:
                self.die()
            else:
                sound_manager.dano()

    def die(self):
        self.is_dead = True
        self.frame_index = 0
        self.dead_timer = pygame.time.get_ticks()
        sound_manager.muerte()

    def manejar_controles(self, keys):
        if pygame.time.get_ticks() < self.aturdido_hasta:
            if (keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w]) and self.on_ground:
                self.vel_y = -self.jump_power
                self.on_ground = False
                sound_manager.salto()
            return
        self.vel_x = 0
        # Con un arma equipada, la orientación (facing_right) la controla
        # la mira (ver el bloque en free_game.py/multi_game.py), no el
        # movimiento — así se puede caminar hacia atrás mientras se
        # apunta al lado contrario. Sin arma, se mantiene el
        # comportamiento de siempre.
        sin_arma = self.arma_equipada in (None, "nada")
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.vel_x = -self.speed
            if sin_arma:
                self.facing_right = False
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vel_x = self.speed
            if sin_arma:
                self.facing_right = True
        if (keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w]) and self.on_ground:
            self.vel_y = -self.jump_power
            self.on_ground = False
            sound_manager.salto()

    def aplicar_fisica(self):
        self.x_anterior = self.x
        self.x += self.vel_x
        self.vel_y += self.gravity
        self.y += self.vel_y
        # Fricción del empuje: mientras dura el aturdimiento, decae el
        # impulso horizontal en vez de cortarlo en seco al terminar.
        if pygame.time.get_ticks() < self.aturdido_hasta:
            self.vel_x *= 0.9

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

    def update(self, keys=None):
        
        if self.is_dead:
            self.current_animation = "death"
            self.frame_timer += 1
            if self.frame_timer >= 10:
                self.frame_timer = 0
                if self.frame_index < len(self.animations["death"]) - 1:
                    self.frame_index += 1
            # Reinicia tras 2 segundos muerto
            if self.puede_reaparecer and pygame.time.get_ticks() - self.dead_timer > 2000:
                self.reset()
            self.image = self.animations["death"][self.frame_index]
            if not self.facing_right:
                self.image = pygame.transform.flip(self.image, True, False)
            return
        
        if self.es_remoto:
            return  # no recalcular nada, solo usar valores recibidos
        
        if keys:  # Solo maneja controles si keys es proporcionado
            self.manejar_controles(keys)
        self.aplicar_fisica()
        self.actualizar_animacion()

    def draw(self, pantalla):
        self._dibujar_aura(pantalla)
        if self.es_remoto:
            # Forzar a usar el frame recibido por red
            anim = self.animations.get(self.current_animation, self.animations["idle"])
            idx = int(self.frame_index) % len(anim)
            self.image = anim[idx]
            if not self.facing_right:
                self.image = pygame.transform.flip(self.image, True, False)
        pantalla.blit(self.image, (self.x, self.y))
        # Barra de vida
        bar_width = 60
        bar_height = 10
        health_ratio = max(self.health / self.vida_maxima, 0)
        health_color = (200, 0, 0) if self.health < 60 else (0, 200, 0)
        pygame.draw.rect(pantalla, (50, 50, 50), (self.x, self.y - 15, bar_width, bar_height))
        pygame.draw.rect(pantalla, health_color, (self.x, self.y - 15, bar_width * health_ratio, bar_height))
        texto_nombre = self.font_nombre.render(self.nombre_jugador, True, self.color_nombre)  # Nombre encima
        texto_rect = texto_nombre.get_rect(center=(self.x + self.width // 2, self.y - 25))
        pantalla.blit(texto_nombre, texto_rect)

        if self.mensaje_chat and pygame.time.get_ticks() < self.mensaje_chat_expira:
            fuente_burbuja = pygame.font.SysFont("Arial", 14)
            texto_render = fuente_burbuja.render(self.mensaje_chat, True, (0, 0, 0))
            burbuja_rect = texto_render.get_rect()
            burbuja_rect.inflate_ip(16, 16)
            burbuja_rect.midbottom = (self.x + self.width // 2, self.y - 35)
            pygame.draw.rect(pantalla, (255, 255, 255), burbuja_rect, border_radius=10)
            pygame.draw.rect(pantalla, (0, 0, 0), burbuja_rect, width=2, border_radius=10)
            pantalla.blit(texto_render, texto_render.get_rect(center=burbuja_rect.center))
        elif self.mensaje_chat:
            self.mensaje_chat = None

    def draw_death_message(self, pantalla, fuente, duracion_ms=3000):
        if not self.is_dead:
            return
        transcurrido = pygame.time.get_ticks() - self.dead_timer
        if transcurrido >= duracion_ms:
            return

        fuente_grande = pygame.font.SysFont(None, 40, bold=True) # Tamaño de mensaje "Ha sido detonado"
        texto = f"¡{self.nombre_jugador} ha sido detonado!"

        # Fade-in rápido (200ms) y fade-out al final (500ms)
        fade_in = min(1.0, transcurrido / 200)
        restante = duracion_ms - transcurrido
        fade_out = min(1.0, restante / 500)
        alpha = int(255 * min(fade_in, fade_out))

        color_texto = (255, 60, 60)
        color_borde = (0, 0, 0)

        render_texto = fuente_grande.render(texto, True, color_texto)
        render_borde = fuente_grande.render(texto, True, color_borde)

        ancho, alto = render_texto.get_size()
        padding_x, padding_y = 24, 14
        superficie = pygame.Surface((ancho + padding_x * 2, alto + padding_y * 2), pygame.SRCALPHA)

        # Fondo oscuro translúcido con borde rojo — se lee bien sobre
        # cualquier fondo de mapa.
        pygame.draw.rect(superficie, (20, 20, 20, 160), superficie.get_rect(), border_radius=12)
        pygame.draw.rect(superficie, (255, 60, 60, 200), superficie.get_rect(), width=2, border_radius=12)

        centro = (superficie.get_width() // 2, superficie.get_height() // 2)
        grosor = 2
        for dx in (-grosor, 0, grosor):
            for dy in (-grosor, 0, grosor):
                if dx == 0 and dy == 0:
                    continue
                superficie.blit(render_borde, render_borde.get_rect(center=(centro[0] + dx, centro[1] + dy)))
        superficie.blit(render_texto, render_texto.get_rect(center=centro))

        superficie.set_alpha(alpha)

        # Pequeño "pop" de escala al aparecer
        escala = 0.85 + 0.15 * fade_in
        if escala != 1.0:
            nuevo_tam = (max(1, int(superficie.get_width() * escala)), max(1, int(superficie.get_height() * escala)))
            superficie = pygame.transform.smoothscale(superficie, nuevo_tam)

        rect = superficie.get_rect(center=(pantalla.get_width() // 2, pantalla.get_height() // 2 - 20)) # >> -0 << es para la posicion del mensaje "ha sido detonado"   
        pantalla.blit(superficie, rect)

    def get_centro(self):
        return (self.x + self.width // 2, self.y + self.height // 2)

    def get_hitbox_lateral(self):
        rect = self.get_rect()
        nuevo_ancho = 20
        nuevo_x = rect.x + (rect.width - nuevo_ancho) // 2
        return pygame.Rect(nuevo_x, rect.y, nuevo_ancho, rect.height)
    
    def aplicar_empuje(self, vel_x=0, vel_y=0, duracion_ms=250):
        """Impulso externo (knockback) — usado por weapon_manager al
        golpear con un arma que define empuje_ancho/empuje_alto en su
        config.json. duracion_ms controla cuánto tiempo el teclado deja
        de pisar el vel_x horizontal (ver manejar_controles)."""
        if vel_x:
            self.vel_x = vel_x
            self.aturdido_hasta = pygame.time.get_ticks() + duracion_ms
        if vel_y:
            self.vel_y = vel_y

    def activar_aura(self, color, duracion_ms=None, pulso_ms=550):
        """Aura pulsante de color detrás del sprite. duracion_ms=None
        (default) la deja activa indefinidamente, hasta que se llame
        desactivar_aura() o el robot haga reset() — pensado para "modo
        furia" de una fase completa, no un flash de un instante. Si le
        pasas un número, se apaga sola pasado ese tiempo."""
        self._aura_color = color
        self._aura_inicio = pygame.time.get_ticks()
        self._aura_hasta = (self._aura_inicio + duracion_ms) if duracion_ms else None
        self._aura_pulso_ms = pulso_ms

    def desactivar_aura(self):
        self._aura_color = None

    def _dibujar_aura(self, pantalla):
        if not self._aura_color:
            return
        ahora = pygame.time.get_ticks()
        if self._aura_hasta is not None and ahora >= self._aura_hasta:
            self._aura_color = None
            return

        anim_aura = self.animations.get("aura_fuego")
        if anim_aura:
            self._aura_frame_timer += 1
            if self._aura_frame_timer >= 6:  # velocidad del ciclo — ajusta a gusto
                self._aura_frame_timer = 0
                self._aura_frame_index = (self._aura_frame_index + 1) % len(anim_aura)
            frame = anim_aura[self._aura_frame_index]
            centro = (int(self.x + self.width / 2), int(self.y + self.height / 2))
            pantalla.blit(frame, frame.get_rect(center=centro))
            return  # no dibuja también el círculo matemático encima


        # Pulso suave 0 -> 1 -> 0 en bucle (no es un parpadeo brusco).
        t = ((ahora - self._aura_inicio) % self._aura_pulso_ms) / self._aura_pulso_ms
        fase = math.sin(t * math.pi)

        centro = (int(self.x + self.width / 2), int(self.y + self.height / 2))
        radio_base = max(self.width, self.height) * 0.55

        for escala, alpha_max in ((1.0, 90), (1.25, 55), (1.55, 28)):
            radio = max(1, int(radio_base * (escala + 0.12 * fase)))
            alpha = int(alpha_max * (0.5 + 0.5 * fase))
            capa = pygame.Surface((radio * 2, radio * 2), pygame.SRCALPHA)
            pygame.draw.circle(capa, (*self._aura_color, alpha), (radio, radio), radio)
            # Blend aditivo: los colores se suman a lo que ya hay detrás
            # en vez de taparlo — así se ve como un resplandor de verdad
            # (más brillante donde se solapa) en vez de un círculo plano.
            pantalla.blit(capa, capa.get_rect(center=centro), special_flags=pygame.BLEND_RGBA_ADD)

    def mostrar_mensaje(self, texto, duracion_ms=4000):
        self.mensaje_chat = texto
        self.mensaje_chat_expira = pygame.time.get_ticks() + duracion_ms

    def redimensionar(self, ancho, alto):
        """Reescala los sprites ya cargados a un nuevo tamaño lógico (ej. al
        cambiar de modo de partida dentro del lobby, después de que el
        Robot ya se construyó con el tamaño por defecto). No vuelve a leer
        el disco — reescala lo que ya está en memoria, así que un cambio
        de tamaño repetido pierde algo de nitidez, pero para un cambio
        puntual de modo es imperceptible."""
        if (ancho, alto) == (self.width, self.height):
            return
        for clave, frames in self.animations.items():
            if clave == "aura_fuego" or not frames:
                continue  # el aura usa su propio tamaño (ancho_aura/alto_aura), no el del robot
            self.animations[clave] = [pygame.transform.smoothscale(f, (ancho, alto)) for f in frames]
        self.width, self.height = ancho, alto
        anim_actual = self.animations.get(self.current_animation)
        if anim_actual:
            self.image = anim_actual[min(self.frame_index, len(anim_actual) - 1)]