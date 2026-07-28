# core/game_modes/solo_game/bot_controller.py
"""IA deliberadamente simple: movimiento, puntería y decisión de tiro."""
import math
import random
import pygame


class BotController:
    def __init__(self, robot, difficulty: int, rng: random.Random | None = None):
        self.robot = robot
        self.difficulty = max(1, difficulty)
        self.rng = rng or random.Random()
        self.target_distance = max(120, 310 - self.difficulty * 30)
        self.next_shot_at = 0

    def update(self, target) -> tuple[float, float] | None:
        if self.robot.is_dead or target is None or target.is_dead:
            return None
        origin = self.robot.get_centro()
        target_pos = target.get_centro()
        dx, dy = target_pos[0] - origin[0], target_pos[1] - origin[1]
        distance = math.hypot(dx, dy)
        self.robot.facing_right = dx >= 0
        self.robot.vel_x = 0
        if distance > self.target_distance + 35:
            self.robot.vel_x = self.robot.speed * (1 if dx > 0 else -1)
        elif distance < self.target_distance - 35:
            self.robot.vel_x = -self.robot.speed * (1 if dx > 0 else -1)
        if self.robot.on_ground and dy < -55 and self.rng.random() < 0.015 * self.difficulty:
            self.robot.vel_y = -self.robot.jump_power
            self.robot.on_ground = False
        return self._aim(origin, target_pos, distance)

    def should_fire(self, distance: float) -> bool:
        now = pygame.time.get_ticks()
        if now < self.next_shot_at or distance > 580:
            return False
        chance = min(0.26 + self.difficulty * 0.10, 0.75)
        if self.rng.random() > chance:
            self.next_shot_at = now + 350
            return False
        self.next_shot_at = now + max(450, 1500 - self.difficulty * 180)
        return True

    def _aim(self, origin, target, distance):
        # Elevación suave: suficiente para que misiles/granadas no apunten al suelo.
        dx, dy = target[0] - origin[0], target[1] - origin[1]
        return (dx, dy - min(95, distance * 0.18))
