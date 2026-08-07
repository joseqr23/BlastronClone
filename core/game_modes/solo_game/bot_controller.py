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

class _ObjetivoPuntual:
    """Wrapper liviano para que BotController persiga/apunte a un PUNTO
    del mapa (la pelota suelta, o el aro) con la misma lógica de
    movimiento y puntería que ya usa para perseguir a un jugador — sin
    duplicar nada de esa lógica en otro lado."""
    __slots__ = ("x", "y", "is_dead")

    def __init__(self, x, y):
        self.x, self.y, self.is_dead = x, y, False

    def get_centro(self):
        return (self.x, self.y)

    def get_rect(self):
        return pygame.Rect(int(self.x) - 5, int(self.y) - 5, 10, 10)


class BotController:
    DURACION_RETIRADA_MS = 3000
    DISTANCIA_MAX_DISPARO = 580
    ATASCO_CHECK_MS = 600
    ATASCO_UMBRAL_PX = 4
    CONTACTO_CUERPO_A_CUERPO = 0    # 0 = literalmente pegados / superpuestos
    TOLERANCIA_ATAQUE_CUERPO_A_CUERPO = 24  # margen para atacar una vez que llegó ahí
    TIEMPO_VUELO_MIN_BASKET = 20
    FACTOR_ARCO_BASKET = 3.6  # más alto = arco más lobeado, más margen para pasar la pared del aro

    def __init__(self, robot, difficulty: int, rng: random.Random | None = None,
                 distancia_acercamiento=None, distancia_ataque=None, persigue_sin_tregua=False):
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
        self.persigue_sin_tregua = persigue_sin_tregua  # modo libre: nunca se retira tras golpear
        # Override opcional del intervalo entre golpes/disparos — None =
        # usar la fórmula por dificultad de siempre. Lo fija ModoBasket
        # para que el manazo de los bots respete cooldown_ataque_ms.
        self.cooldown_disparo_ms = None
        # Distancia MÍNIMA para poder disparar (ver should_fire) — None =
        # sin piso, comportamiento de siempre. Lo usa ModoBasket para que
        # el bot no encestre parado literalmente debajo del aro.
        self.distancia_minima_disparo = None
        # Punto real al que apuntar/lanzar en Basket — separado del
        # "target" que se le pasa a update() para MOVERSE (que puede ser
        # un punto de parada distinto al aro, ver game._objetivo_basket).
        # None = usar el target de movimiento también para apuntar
        # (comportamiento de siempre).
        self.punto_mira_basket = None

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

        if not self.persigue_sin_tregua and ahora < self.retirada_hasta_ms:
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

        if self.distancia_minima_disparo is not None and distance < self.distancia_minima_disparo:
            return False

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

        self.next_shot_at = now + (self.cooldown_disparo_ms if self.cooldown_disparo_ms is not None
                                   else max(450, 1500 - self.difficulty * 180))
        if es_cuerpo_a_cuerpo and not self.persigue_sin_tregua:
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
        """Explosivas: elevación simple (aproximación, alcanza para que
        no falle). Basket: física exacta (ver _calcular_arco_basket) —
        apunta a self.punto_mira_basket si está fijado (el aro real),
        no necesariamente al mismo punto al que el bot está caminando
        (que puede ser un punto de parada a un costado del aro — ver
        game._objetivo_basket). Cualquier otro tipo apunta directo al
        centro real del objetivo."""
        config = self._config_arma_actual()
        tipo = config.get("tipo") if config else None
        dx, dy = target[0] - origin[0], target[1] - origin[1]
        if tipo == "Explosivas":
            elevacion = min(90, distance * 0.18)
            return (dx, dy - elevacion)
        if tipo == "Basket":
            objetivo_real = self.punto_mira_basket or target
            return self._calcular_arco_basket(origin, objetivo_real)
        return (dx, dy)

    def _calcular_arco_basket(self, origin, target):
        """Devuelve (vel_x, vel_y) EXACTOS para que el balón llegue justo
        al punto objetivo, resolviendo la recurrencia DISCRETA real de
        Proyectil.update() — no la aproximación continua 0.5*g*t².

        Vertical: vel_y += gravedad y LUEGO se desplaza, una vez por
        frame -> tras n frames el desplazamiento total es
        n*vel_y0 + g*n*(n+1)/2 (no g*n²/2). Se despeja vel_y0 de eso.

        Horizontal: vel_x se multiplica por friccion_aire cada frame
        DESPUÉS de desplazar — la distancia total NO es vel_x0*n, es una
        serie geométrica. Sin compensar esto, el balón se quedaba corto
        en distancia horizontal (el síntoma de "poca fuerza") — con
        friccion_aire=0.995 la pérdida acumulada en 20-40 frames es
        significativa, no despreciable."""
        config = self._config_arma_actual()
        gravedad = config.get("gravedad", 0.35) if config else 0.35
        friccion_aire = config.get("friccion_aire", 1.0) if config else 1.0
        velocidad_base = config.get("velocidad_proyectil", 14) if config else 14
        dx = target[0] - origin[0]
        dy = target[1] - origin[1]
        distancia_horizontal = max(1, abs(dx))
        n = max(self.TIEMPO_VUELO_MIN_BASKET,
                int((distancia_horizontal / max(1, velocidad_base)) * self.FACTOR_ARCO_BASKET))

        vel_y = (dy - gravedad * n * (n + 1) / 2) / n

        if abs(friccion_aire - 1.0) < 1e-6:
            vel_x = dx / n
        else:
            factor_serie = (1 - friccion_aire ** n) / (1 - friccion_aire)
            vel_x = dx / factor_serie if factor_serie else dx / n

        return (vel_x, vel_y)

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

    def on_round_start(self):
        """Se llama al arrancar cada ronda de un modo por rondas (ver
        ModoMejorDeTres._iniciar_ronda). Un bot normal no tiene estado
        que arrastre entre rondas, así que no hace nada — solo existe
        para que BossController (y cualquier IA futura con fases) tenga
        dónde resetearse."""
        pass