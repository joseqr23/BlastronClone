# core/game_modes/solo_game/npc_manager.py
"""Spawnea bots y jefe con la MISMA lógica: un solo self.controllers
compartido, y un solo pool de nombres usados que cubre a ambos — así un
bot y el jefe nunca pueden pisarse el nombre entre sí (antes cada
manager deduplicaba por su cuenta, sin saber nada del otro).

SoloGame ya no necesita meter la mano dentro de self.controllers desde
afuera para conectar al jefe con su IA (como hacía antes con
`self.bot_manager.controllers[robot_jefe] = self.boss_manager.controller`)
— spawn_boss() lo hace internamente, igual que spawn_bots().
"""
import random

from settings import ANCHO, ALTO, ALTURA_SUELO
from entities.players.robot import Robot
from .bot_controller import BotController
from .boss_controller import BossController
from .level_config import DEFAULT_ROBOTS

# Se mantiene el nombre por compatibilidad con cualquier código externo
# (p.ej. pantallas de selección) que ya referencie NpcManager.ROBOTS.
ROBOTS = DEFAULT_ROBOTS


class NpcManager:
    ROBOTS = ROBOTS

    def __init__(self, game, bots_config, dificultad: int, seed: int | None = None):
        self.game = game
        self.bots_config = list(bots_config)
        self.dificultad = dificultad
        self.rng = random.Random(seed)
        self.controllers: dict[Robot, BotController] = {}
        self._nombres_usados: set[str] = set()

    def _nombre_unico(self, nombre_base: str) -> str:
        """Deduplica contra CUALQUIER npc ya creado (bot o jefe), sin
        importar el orden en que se llame spawn_bots()/spawn_boss()."""
        nombre, sufijo = nombre_base, 2
        while nombre in self._nombres_usados:
            nombre = f"{nombre_base} ({sufijo})"
            sufijo += 1
        self._nombres_usados.add(nombre)
        return nombre

    def spawn_bots(self) -> dict[str, Robot]:
        """Devuelve {nombre: Robot}, listo para volcar en game.robots_remotos."""
        bots = {}
        for indice, config in enumerate(self.bots_config):
            nombre = self._nombre_unico(config.nombre or f"Bot {indice + 1}")
            vida = config.vida_maxima or self.game.modo.vida_maxima
            robot = Robot(ANCHO // 2, ALTO - ALTURA_SUELO - 90, nombre, config.robot_id,
                          vida_maxima=vida, puede_reaparecer=self.game.modo.permite_reaparecer,
                          velocidad=config.velocidad, salto=config.salto)
            robot.es_jugador = False
            robot.arma_equipada = config.arma

            self.controllers[robot] = BotController(robot, self.dificultad, self.rng)
            bots[nombre] = robot
        return bots

    def spawn_boss(self, config) -> dict[str, Robot]:
        """Mismo shape que spawn_bots() (dict de 1 entrada) — así
        game.py hace robots_remotos.update(...) igual en ambos casos,
        sin ningún caso especial para el jefe."""
        nombre = self._nombre_unico(config.nombre)
        robot = Robot(
            ANCHO // 2, ALTO - ALTURA_SUELO - config.alto,
            nombre, config.robot_id,
            vida_maxima=config.vida_maxima, puede_reaparecer=self.game.modo.permite_reaparecer,
            ancho=config.ancho, alto=config.alto,
            velocidad=config.velocidad, salto=config.salto,
        )
        robot.es_jugador = False
        robot.damage_multiplier = config.damage_multiplier
        robot.arma_equipada = config.armas[0] if config.armas else "misil"

        self.controllers[robot] = BossController(robot, config, self.rng)
        return {nombre: robot}