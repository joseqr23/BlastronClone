from entities.weapons.granada import Granada
from entities.weapons.misil import Misil


class WeaponManager:
    def __init__(self, game):
        self.game = game

    def disparar(self):
        if self.game.robot.arma_equipada == 'granada':
            ancho, alto = Granada.ANCHO, Granada.ALTO
            origen, vel_x, vel_y = self.game.aim.get_datos_disparo(ancho, alto)
            g = Granada(origen[0], origen[1], vel_x, vel_y)
            g.owner = self.game.robot.nombre_jugador
            self.game.granadas.append(g)
        elif self.game.robot.arma_equipada == 'misil':
            ancho, alto = Misil.ANCHO, Misil.ALTO
            origen, vel_x, vel_y = self.game.aim.get_datos_disparo(ancho, alto)
            m = Misil(origen[0], origen[1], vel_x, vel_y)
            m.owner = self.game.robot.nombre_jugador
            self.game.misiles.append(m)

    def update(self):
        self._update_granadas()
        self._update_misiles()

    def draw(self, pantalla):
        for granada in self.game.granadas:
            granada.draw(pantalla)
        for misil in self.game.misiles:
            misil.draw(pantalla)

    def _robots_para_colision(self):
        """update() de Granada/Misil ahora espera una LISTA de robots (no
        uno solo) y revisa colisión en cada sub-paso del movimiento — así
        se evita que a alta velocidad el proyectil traspase a un robot
        estático, igual que se corrigió en el modo multijugador."""
        return [self.game.robot] + list(self.game.robots_estaticos)

    # --- Granadas ---
    def _update_granadas(self):
        for granada in self.game.granadas[:]:
            # El rebote contra tiles y contra TODOS los robots ya ocurre
            # dentro de update(), sub-paso por sub-paso — ya no hace falta
            # llamar rebote_con_robot() aparte para cada robot_estatico.
            granada.update(self.game.tiles, self._robots_para_colision())

            for robot_estatico in self.game.robots_estaticos:
                if granada.explotado and granada.estado == "explode":
                    if robot_estatico not in granada.danados and granada.get_hitbox().colliderect(robot_estatico.get_rect()):
                        robot_estatico.take_damage(70)
                        puntos = 70
                        if robot_estatico.health <= 0:
                            puntos *= 2
                        self.game.puntajes[self.game.robot] += puntos
                        granada.danados.add(robot_estatico)

            if granada.explotado and granada.estado == "explode" and not granada.ya_hizo_dano:
                if granada.get_hitbox().colliderect(self.game.robot.get_rect()):
                    self.game.robot.take_damage(70)
                    granada.ya_hizo_dano = True

            if granada.estado == "done":
                self.game.granadas.remove(granada)

    # --- Misiles ---
    def _update_misiles(self):
        for misil in self.game.misiles[:]:
            # El impacto contra tiles y contra TODOS los robots ya ocurre
            # dentro de update(), sub-paso por sub-paso.
            misil.update(self.game.tiles, self._robots_para_colision())

            for robot_estatico in self.game.robots_estaticos:
                if misil.explotado and misil.estado == "explode":
                    if robot_estatico not in misil.danados and misil.get_hitbox().colliderect(robot_estatico.get_rect()):
                        robot_estatico.take_damage(50)
                        puntos = 50
                        if robot_estatico.health <= 0:
                            puntos *= 2
                        self.game.puntajes[self.game.robot] += puntos
                        misil.danados.add(robot_estatico)

            if misil.explotado and misil.estado == "explode" and not misil.ya_hizo_dano:
                if misil.get_hitbox().colliderect(self.game.robot.get_rect()):
                    self.game.robot.take_damage(50)
                    misil.ya_hizo_dano = True

            if misil.estado == "done":
                self.game.misiles.remove(misil)