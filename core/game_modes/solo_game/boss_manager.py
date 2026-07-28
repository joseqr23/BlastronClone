# core/game_modes/solo_game/boss_manager.py
from settings import ANCHO, ALTO, ALTURA_SUELO
from entities.players.robot import Robot
from .boss_controller import BossController


class BossManager:
    def __init__(self, game, config):
        self.game, self.config = game, config
        self.robot = None
        self.controller = None

    def spawn(self):
        sprite_path = f"assets/robots_boss/{self.config.sprite_folder}" if self.config.sprite_folder else None
        robot = Robot(ANCHO // 2, ALTO - ALTURA_SUELO - 90, "JEFE", self.config.robot_id,
                      vida_maxima=self.config.vida_maxima, puede_reaparecer=False, sprite_path=sprite_path)
        robot.es_jugador = False
        robot.damage_multiplier = self.config.damage_multiplier
        self.robot = robot
        self.controller = BossController(robot, self.config)
        return robot

    def update(self, target):
        if not self.robot:
            return None
        aim = self.controller.update(target)
        if aim and self.controller.should_fire(((self.robot.x - target.x) ** 2 + (self.robot.y - target.y) ** 2) ** 0.5):
            return self.robot, aim
        return None
