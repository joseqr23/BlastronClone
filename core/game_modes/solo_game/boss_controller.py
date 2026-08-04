from .bot_controller import BotController


class BossController(BotController):
    """El jefe mantiene la IA base (BotController) intacta — movimiento,
    puntería y disparo son EXACTAMENTE los mismos. Solo se vuelve más
    agresivo y cambia de arma al perder vida (fases).

    distancia_acercamiento/distancia_ataque en el JSON del jefe pueden
    ser un número simple (mismo valor en todas las fases, igual que en
    un bot normal) O una lista paralela a "armas" (una distancia propia
    por cada arma que use en cada fase) — ver _valor_para_fase()."""

    DIFFICULTY_BASE = 4
    COLORES_FURIA = (
        (255, 170, 60),   # fase 1 — naranja
        (255, 90, 20),    # fase 2 — naranja-rojo intenso
        (255, 25, 10),     # fase 3+ — rojo furia
    )

    def __init__(self, robot, config, rng=None):
        super().__init__(robot, difficulty=self.DIFFICULTY_BASE, rng=rng,
                          distancia_acercamiento=self._valor_para_fase(config.distancia_acercamiento, 0),
                          distancia_ataque=self._valor_para_fase(config.distancia_ataque, 0))
        self.config = config
        self.phase = 0

    def update(self, target):
        health_ratio = self.robot.health / self.robot.vida_maxima
        while self.phase < len(self.config.fases) and health_ratio <= self.config.fases[self.phase]:
            self.phase += 1
            self.difficulty += 1
            if self.config.armas:
                self.robot.arma_equipada = self.config.armas[min(self.phase, len(self.config.armas) - 1)]
            # Recalcula las distancias para la fase/arma que se acaba de
            # equipar — mismo índice de fase que se usó arriba para el
            # arma, así quedan siempre sincronizadas entre sí.
            self.distancia_acercamiento = self._valor_para_fase(self.config.distancia_acercamiento, self.phase)
            self.distancia_ataque = self._valor_para_fase(self.config.distancia_ataque, self.phase)
            # Aura de furia: se queda activa para toda esta fase (no un
            # flash), y se vuelve más intensa/roja mientras más fases
            # pasa el jefe.
            color = self.COLORES_FURIA[min(self.phase - 1, len(self.COLORES_FURIA) - 1)]
            self.robot.activar_aura(color) #>> pendiente activar aura de furia en el jefe, pero no hay assets para eso todavía de momento es un efecto pobre con math
        return super().update(target)

    @staticmethod
    def _valor_para_fase(valor, fase):
        """Si 'valor' es una lista/tupla (una distancia por cada arma de
        "armas"), devuelve la que corresponde a esta fase, con el mismo
        clamp de índice que ya usa el jefe para elegir el arma
        (min(fase, len-1) — si hay más fases que distancias definidas,
        se queda en la última). Si es un número (o None), se devuelve
        tal cual: mismo valor en todas las fases, como hasta ahora."""
        if isinstance(valor, (list, tuple)):
            if not valor:
                return None
            return valor[min(fase, len(valor) - 1)]
        return valor

    def _distancia_ideal(self):
        if self.distancia_acercamiento is not None:
            # Override explícito del nivel (ya resuelto para esta fase
            # en update()): se respeta tal cual, sin piso de
            # agresividad extra — si pediste 0, es 0.
            return self.distancia_acercamiento
        return max(50, super()._distancia_ideal() - 35 * self.phase)

    def should_fire(self, distance):
        old = self.next_shot_at
        result = super().should_fire(distance)
        if result:
            self.next_shot_at = min(self.next_shot_at, old + 500)
        return result

    def on_round_start(self):
        """Reinicia TODO lo que las fases fueron acumulando durante la
        ronda anterior — sin esto, self.phase queda "adelantado" y el
        jefe se salta directo a un arma/distancia avanzada en vez de
        volver a empezar en fase 0, ronda tras ronda."""
        self.phase = 0
        self.difficulty = self.DIFFICULTY_BASE
        if self.config.armas:
            self.robot.arma_equipada = self.config.armas[0]
        self.distancia_acercamiento = self._valor_para_fase(self.config.distancia_acercamiento, 0)
        self.distancia_ataque = self._valor_para_fase(self.config.distancia_ataque, 0)
        self.robot.desactivar_aura()