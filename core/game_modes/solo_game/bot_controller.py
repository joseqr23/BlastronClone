"""IA de bots/jefe: movimiento, puntería y decisión de tiro.

Compartida por bots normales y el jefe — BossController (ver
boss_controller.py) hereda TODO de acá; solo sobreescribe la distancia
ideal (para volverse más agresivo por fase) y el ritmo de disparo. No
hay ninguna lógica de movimiento/puntería/disparo duplicada entre bot y
jefe — viven en un único lugar.
"""
import math
import random
import pygame
from utils.weapon_loader import config_arma


class BotController:
    RANGO_CUERPO_A_CUERPO = 55       # distancia a la que un golpe cuerpo a cuerpo conecta de verdad
    DURACION_RETIRADA_MS = 3000      # cuánto huye tras golpear, en tiempo REAL (no en turnos)
    DISTANCIA_MAX_DISPARO = 580      # más allá de esto, ni se molesta con armas a distancia

    def __init__(self, robot, difficulty: int, rng: random.Random | None = None):
        self.robot = robot
        self.difficulty = max(1, difficulty)
        self.rng = rng or random.Random()
        self.next_shot_at = 0
        self.retirada_hasta_ms = 0  # 0 = no está huyendo ahora mismo

    # ------------------------------------------------------------------
    # Distancias objetivo — según el arma equipada AHORA MISMO
    # ------------------------------------------------------------------
    def _distancia_ideal(self):
        config = self._config_arma_actual()
        if self._es_cuerpo_a_cuerpo(config):
            # Se pega lo más posible al jugador — bien DENTRO del rango
            # de golpe (no justo en el borde), para que nunca se quede
            # "a un par de píxeles" sin poder atacar.
            return self.RANGO_CUERPO_A_CUERPO * 0.6
        # A distancia: ni tan lejos que no acierte, ni tan cerca que la
        # propia explosión de su arma lo alcance también a él.
        base = max(160, 340 - self.difficulty * 25)
        return max(base, self._distancia_segura_explosion() * 1.4)

    def _distancia_segura_explosion(self):
        """Radio aproximado de la explosión del arma actual — evita que
        un bot con arma de área dispare literalmente pegado al jugador
        y se lastime con su propia onda expansiva."""
        config = self._config_arma_actual()
        if not config:
            return 0
        ancho = config.get("hitbox_ancho_explosion") or config.get("ancho_explosion", 0)
        alto = config.get("hitbox_alto_explosion") or config.get("alto_explosion", 0)
        return max(ancho, alto) / 2

    # ------------------------------------------------------------------
    # Movimiento
    # ------------------------------------------------------------------
    def update(self, target) -> tuple[float, float] | None:
        if self.robot.is_dead or target is None or target.is_dead:
            return None

        origin, target_pos = self.robot.get_centro(), target.get_centro()
        dx, dy = target_pos[0] - origin[0], target_pos[1] - origin[1]
        distance = math.hypot(dx, dy)
        self.robot.facing_right = dx >= 0
        self.robot.vel_x = 0

        ahora = pygame.time.get_ticks()
        if ahora < self.retirada_hasta_ms:
            # Huyendo tras un golpe reciente — se aleja sin importar la
            # distancia objetivo normal, hasta que se cumpla el tiempo.
            self.robot.vel_x = -self.robot.speed * (1 if dx > 0 else -1)
        else:
            objetivo = self._distancia_ideal()
            if distance > objetivo + 15:
                self.robot.vel_x = self.robot.speed * (1 if dx > 0 else -1)
            elif distance < objetivo - 15:
                self.robot.vel_x = -self.robot.speed * (1 if dx > 0 else -1)
            # dentro de ±15px del objetivo: se queda quieto, ya está en
            # buena posición para atacar — sin dejar un hueco entre esta
            # zona y el alcance real de golpe/disparo.

        if self.robot.on_ground and dy < -55 and self.rng.random() < 0.015 * self.difficulty:
            self.robot.vel_y = -self.robot.jump_power
            self.robot.on_ground = False

        return self._aim(origin, target_pos, distance)

    # ------------------------------------------------------------------
    # Disparo
    # ------------------------------------------------------------------
    def should_fire(self, distance: float) -> bool:
        now = pygame.time.get_ticks()
        if now < self.next_shot_at or now < self.retirada_hasta_ms:
            return False

        config = self._config_arma_actual()
        es_cuerpo_a_cuerpo = self._es_cuerpo_a_cuerpo(config)

        if es_cuerpo_a_cuerpo:
            if distance > self.RANGO_CUERPO_A_CUERPO:
                return False
        else:
            if distance > self.DISTANCIA_MAX_DISPARO:
                return False
            # No dispara un arma de área si está tan cerca que su propia
            # explosión también lo alcanzaría a él.
            if distance < self._distancia_segura_explosion():
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
    # Helpers
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
        """Apunta al centro real del objetivo. Solo se agrega elevación
        artificial para armas con gravedad de verdad (misil, granada) —
        proporcional a cuánta gravedad tiene el arma, así un
        rifle/escopeta/francotirador (gravedad 0) siempre apunta
        certero al centro, en vez de sistemáticamente demasiado alto."""
        config = self._config_arma_actual()
        gravedad = config.get("gravedad", 0) if config else 0
        dx, dy = target[0] - origin[0], target[1] - origin[1]
        if gravedad <= 0:
            return (dx, dy)
        elevacion = min(90, distance * 0.15) * min(1.0, gravedad)
        return (dx, dy - elevacion)

    