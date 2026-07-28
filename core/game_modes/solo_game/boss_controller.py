# core/game_modes/solo_game/boss_controller.py
from .bot_controller import BotController

class BossController(BotController):
    """El jefe mantiene la IA base, pero se vuelve más agresivo al perder vida."""
    def __init__(self, robot, config, rng=None):
        super().__init__(robot, difficulty=4, rng=rng)
        self.config = config
        self.phase = 0

    def update(self, target):
        health_ratio = self.robot.health / self.robot.vida_maxima
        while self.phase < len(self.config.fases) and health_ratio <= self.config.fases[self.phase]:
            self.phase += 1
            self.difficulty += 1
            self.target_distance = max(90, self.target_distance - 35)
        return super().update(target)

    def should_fire(self, distance):
        old = self.next_shot_at
        result = super().should_fire(distance)
        if result:
            self.next_shot_at = min(self.next_shot_at, old + 500)
        return result
