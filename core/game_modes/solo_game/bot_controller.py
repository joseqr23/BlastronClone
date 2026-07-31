# core/game_modes/solo_game/bot_controller.py

"""IA de bots/jefe: movimiento, puntería y decisión de tiro.

Compartida por bots normales y el jefe — BossController hereda TODO de
acá; solo sobreescribe la distancia ideal (más agresivo por fase) y el
ritmo de disparo.
"""
import math
import random
import pygame
from utils.weapon_loader import config_arma


class BotController:
    DURACION_RETIRADA_MS = 3000
    DISTANCIA_MAX_DISPARO = 580
    ATASCO_CHECK_MS = 600
    ATASCO_UMBRAL_PX = 4
    CONTACTO_CUERPO_A_CUERPO = 0    # 0 = literalmente pegados / superpuestos
    TOLERANCIA_ATAQUE_CUERPO_A_CUERPO = 24  # margen para atacar una vez que llegó ahí

    def __init__(self, robot, difficulty: int, rng: random.Random | None = None,
                 distancia_acercamiento=None, distancia_ataque=None):
        self.robot = robot
        self.difficulty = max(1, difficulty)
        self.rng = rng or random.Random()
        self.next_shot_at = 0
        self.retirada_hasta_ms = 0
        self._ultima_pos_x = None
        self._ultimo_avance_ms = 0
        # Overrides opcionales desde el JSON del nivel — None = se
        # calcula automáticamente según el arma, como hasta ahora.
        self.distancia_acercamiento = distancia_acercamiento
        self.distancia_ataque = distancia_ataque

    # ------------------------------------------------------------------
    def _distancia_ideal(self):
        if self.distancia_acercamiento is not None:
            return self.distancia_acercamiento
        config = self._config_arma_actual()
        if self._es_cuerpo_a_cuerpo(config):
            return self.CONTACTO_CUERPO_A_CUERPO
        base = max(160, 340 - self.difficulty * 25)
        return max(base, self._distancia_segura_explosion() * 1.4)

    def _distancia_segura_explosion(self):
        config = self._config_arma_actual()
        if not config:
            return 0
        ancho = config.get("hitbox_ancho_explosion") or config.get("ancho_explosion", 0)
        alto = config.get("hitbox_alto_explosion") or config.get("alto_explosion", 0)
        return max(ancho, alto) / 2

    def _distancia_borde(self, target):
        origen, obj = self.robot.get_rect(), target.get_rect()
        dx = max(obj.left - origen.right, origen.left - obj.right, 0)
        dy = max(obj.top - origen.bottom, origen.top - obj.bottom, 0)
        return math.hypot(dx, dy)

    # ------------------------------------------------------------------
    def update(self, target) -> tuple[float, float] | None:
        if self.robot.is_dead or target is None or target.is_dead:
            return None

        ahora = pygame.time.get_ticks()
        origin, target_pos = self.robot.get_centro(), target.get_centro()
        dx, dy = target_pos[0] - origin[0], target_pos[1] - origin[1]
        self.robot.facing_right = dx >= 0

        if ahora < self.robot.aturdido_hasta:
            return self._aim(origin, target_pos, math.hypot(dx, dy))

        self.robot.vel_x = 0
        distance = self._distancia_borde(target)
        es_cuerpo_a_cuerpo = self._es_cuerpo_a_cuerpo(self._config_arma_actual())

        if ahora < self.retirada_hasta_ms:
            self.robot.vel_x = -self.robot.speed * (1 if dx > 0 else -1)
        else:
            objetivo = self._distancia_ideal()
            # Cuerpo a cuerpo: SIN margen de tolerancia — sigue
            # acercándose hasta que el hueco entre ambos sea 0 de
            # verdad (tocándose), en vez de detenerse un margen antes
            # como hace el movimiento a distancia (que sí necesita ese
            # colchón para no temblar entre acercarse/alejarse).
            margen = 0 if es_cuerpo_a_cuerpo else 15
            if distance > objetivo + margen:
                self.robot.vel_x = self.robot.speed * (1 if dx > 0 else -1)
            elif distance < objetivo - margen:
                self.robot.vel_x = -self.robot.speed * (1 if dx > 0 else -1)

        self._revisar_atasco(ahora)

        if self.robot.on_ground and dy < -55 and self.rng.random() < 0.015 * self.difficulty:
            self.robot.vel_y = -self.robot.jump_power
            self.robot.on_ground = False

        return self._aim(origin, target_pos, math.hypot(dx, dy))

    def _revisar_atasco(self, ahora):
        """Si el bot quiere moverse (vel_x != 0) pero su posición real
        casi no cambió en el último intervalo, probablemente chocó
        contra un tile/estructura — salta para intentar destrabarse."""
        if self._ultima_pos_x is None:
            self._ultima_pos_x, self._ultimo_avance_ms = self.robot.x, ahora
            return

        if self.robot.vel_x == 0:
            self._ultima_pos_x, self._ultimo_avance_ms = self.robot.x, ahora
            return

        if abs(self.robot.x - self._ultima_pos_x) > self.ATASCO_UMBRAL_PX:
            self._ultima_pos_x, self._ultimo_avance_ms = self.robot.x, ahora
            return

        if ahora - self._ultimo_avance_ms >= self.ATASCO_CHECK_MS:
            if self.robot.on_ground:
                self.robot.vel_y = -self.robot.jump_power
                self.robot.on_ground = False
            self._ultimo_avance_ms = ahora  # evita reintentar todos los frames

    # ------------------------------------------------------------------
    def should_fire(self, target) -> bool:
        now = pygame.time.get_ticks()
        if now < self.next_shot_at or now < self.retirada_hasta_ms:
            return False

        distance = self._distancia_borde(target)
        config = self._config_arma_actual()
        es_cuerpo_a_cuerpo = self._es_cuerpo_a_cuerpo(config)

        if self.distancia_ataque is not None:
            limite = self.distancia_ataque
        elif es_cuerpo_a_cuerpo:
            limite = self.TOLERANCIA_ATAQUE_CUERPO_A_CUERPO
        else:
            limite = self.DISTANCIA_MAX_DISPARO

        if distance > limite:
            return False
        if not es_cuerpo_a_cuerpo and self.distancia_ataque is None and distance < self._distancia_segura_explosion():
            return False

        chance = min(0.26 + self.difficulty * 0.10, 0.75)
        if self.rng.random() > chance:
            self.next_shot_at = now + 350
            return False

        self.next_shot_at = now + max(450, 1500 - self.difficulty * 180)
        if es_cuerpo_a_cuerpo:
            self.retirada_hasta_ms = now + self.DURACION_RETIRADA_MS
        return True

    # ------------------------------------------------------------------
    def _config_arma_actual(self):
        if not self.robot.arma_equipada:
            return None
        return config_arma(self.robot.arma_equipada)

    @staticmethod
    def _es_cuerpo_a_cuerpo(config):
        if not config:
            return False
        return config.get("comportamiento") in ("cuerpo_a_cuerpo", "cuerpo_a_cuerpo_direccional")

    def _aim(self, origin, target, distance):
        """Explosivas: se apunta con una elevación de arco (para que la
        trayectoria curva no falle el impacto). Cualquier otro tipo —
        Armas de fuego, Especiales, Cuerpo a cuerpo, o sin "tipo"
        definido — apunta directo al centro real del objetivo."""
        config = self._config_arma_actual()
        tipo = config.get("tipo") if config else None
        dx, dy = target[0] - origin[0], target[1] - origin[1]
        if tipo == "Explosivas":
            elevacion = min(90, distance * 0.18)
            return (dx, dy - elevacion)
        return (dx, dy)

    def _alcance_cuerpo_a_cuerpo(self, config):
        """Qué tan lejos (borde a borde) debe estar el bot para que su
        golpe cuerpo a cuerpo realmente conecte — derivado del propio
        arma (el mismo hitbox/offset que usa Proyectil.get_hitbox()
        para decidir si golpea), no un número fijo. Así el alcance se
        ajusta solo por arma, y funciona igual de bien sin importar qué
        tan grande sea el robot que la porta (ej. un jefe)."""
        ancho_hitbox = config.get("hitbox_ancho_explosion") or config.get("hitbox_ancho_proyectil", 40)
        offset = abs(config.get("posicion_ancho_explosion", 0)) or abs(config.get("posicion_ancho_proyectil", 0))
        return max(20, offset + ancho_hitbox / 2)