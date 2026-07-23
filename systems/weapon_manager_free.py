"""
IMPORTANTE: este archivo NO decide a quién le hace daño una explosión —
esa decisión vive ÚNICAMENTE en Proyectil.robots_afectados(). Aquí solo
se itera esa lista y se aplica el daño/puntaje.
"""
from entities.weapons.proyectil import Proyectil
from utils.weapon_loader import config_arma
from utils.sound_manager import sound_manager


class WeaponManager:
    def __init__(self, game):
        self.game = game

    def disparar(self):
        arma = self.game.robot.arma_equipada
        config = config_arma(arma)
        if not config:
            return
        ancho = config.get("ancho_proyectil", 40)
        alto = config.get("alto_proyectil", 40)
        origen, vel_x, vel_y = self.game.aim.get_datos_disparo(ancho, alto)
        p = Proyectil(arma, origen[0], origen[1], vel_x, vel_y, owner=self.game.robot.nombre_jugador)
        self.game.proyectiles.append(p)
        sound_manager.disparo(arma)

    def update(self):
        self._update_proyectiles()

    def draw(self, pantalla):
        for p in self.game.proyectiles:
            p.draw(pantalla)

    def _robots_para_colision(self):
        """p.update() espera una LISTA de robots (no uno solo) y revisa
        colisión en cada sub-paso del movimiento — así se evita que a
        alta velocidad el proyectil traspase a un robot estático."""
        return [self.game.robot] + list(self.game.robots_estaticos)

    def _update_proyectiles(self):
        for p in self.game.proyectiles[:]:
            candidatos = self._robots_para_colision()
            # La colisión/rebote/impacto contra tiles y TODOS los robots
            # ya ocurre dentro de p.update(), sub-paso por sub-paso.
            p.update(self.game.tiles, candidatos)
            daño = p.daño

            # Proyectil decide TODO sobre a quién dañar. Aquí solo se aplica.
            for robot in p.robots_afectados(candidatos):
                robot.take_damage(daño)
                puntos = daño
                if robot.health <= 0:
                    puntos *= 2
                self.game.puntajes[self.game.robot] += puntos
                p.danados.add(robot)

            if p.estado == "done":
                self.game.proyectiles.remove(p)