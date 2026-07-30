# core/game_modes/solo_game/boss_controller.py
from .bot_controller import BotController


class BossController(BotController):
    """El jefe mantiene la IA base (BotController) intacta — movimiento,
    puntería y disparo son EXACTAMENTE los mismos. Solo se vuelve más
    agresivo y cambia de arma al perder vida (fases)."""
    def __init__(self, robot, config, rng=None):
        super().__init__(robot, difficulty=4, rng=rng,
                          distancia_acercamiento=config.distancia_acercamiento,
                          distancia_ataque=config.distancia_ataque)
        self.config = config
        self.phase = 0

    def update(self, target):
        health_ratio = self.robot.health / self.robot.vida_maxima
        while self.phase < len(self.config.fases) and health_ratio <= self.config.fases[self.phase]:
            self.phase += 1
            self.difficulty += 1
            if self.config.armas:
                self.robot.arma_equipada = self.config.armas[min(self.phase, len(self.config.armas) - 1)]
        return super().update(target)

    def _distancia_ideal(self):
        if self.distancia_acercamiento is not None:
            # Override explícito del nivel: se respeta tal cual, sin piso
            # de agresividad por fase — si pediste 0, es 0.
            return self.distancia_acercamiento
        return max(50, super()._distancia_ideal() - 35 * self.phase)

    def should_fire(self, distance):
        old = self.next_shot_at
        result = super().should_fire(distance)
        if result:
            self.next_shot_at = min(self.next_shot_at, old + 500)
        return result