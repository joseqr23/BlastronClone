# core/game_modes/solo_game/bot_manager.py
import random
from settings import ANCHO, ALTO, ALTURA_SUELO
from entities.players.robot import Robot
from .bot_controller import BotController


class BotManager:
    ROBOTS = ("alfonso", "cartman", "cholo", "correnetali", "eren", "estaly", "netali", "rosadito")

    def __init__(self, game, difficulty: int, seed: int | None = None):
        self.game = game
        self.difficulty = difficulty
        self.rng = random.Random(seed)
        self.controllers: dict[Robot, BotController] = {}

    def spawn(self, amount: int) -> list[Robot]:
        bots = []
        for index in range(amount):
            name = f"Bot {index + 1}"
            robot_id = self.ROBOTS[index % len(self.ROBOTS)]
            health = 140 + self.difficulty * 35
            bot = Robot(ANCHO // 2, ALTO - ALTURA_SUELO - 90, name, robot_id,
                        vida_maxima=health, puede_reaparecer=False)
            bot.es_jugador = False
            self.controllers[bot] = BotController(bot, self.difficulty, self.rng)
            bots.append(bot)
        return bots

    def update(self, target) -> list[tuple[Robot, tuple[float, float]]]:
        shots = []
        for bot, controller in list(self.controllers.items()):
            aim = controller.update(target)
            if aim is None:
                continue
            distance = ((bot.get_centro()[0] - target.get_centro()[0]) ** 2 +
                        (bot.get_centro()[1] - target.get_centro()[1]) ** 2) ** 0.5
            if controller.should_fire(distance):
                shots.append((bot, aim))
        return shots
