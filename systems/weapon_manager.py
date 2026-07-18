# systems/weapon_manager.py
from entities.weapons.granada import Granada
from entities.weapons.misil import Misil
import time
import pygame


class WeaponManager:
    def __init__(self, game):
        self.game = game

    def disparar(self):
        if (
            self.game.turn_manager.jugador_actual() != self.game.nombre_jugador
            or self.game.turn_manager.en_cooldown
        ):
            print(f"[DEBUG] {self.game.nombre_jugador} intentó disparar fuera de turno.")
            return

        shooter = self.game.nombre_jugador

        if self.game.robot.arma_equipada == 'granada':
            ancho, alto = Granada.ANCHO, Granada.ALTO
            origen, vel_x, vel_y = self.game.aim.get_datos_disparo(ancho, alto)
            g = Granada(origen[0], origen[1], vel_x, vel_y)
            g.owner = shooter
            self.game.granadas.append(g)
            self.game.enviar({
                "tipo": "disparo",
                "jugador": self.game.nombre_jugador,
                "arma": self.game.robot.arma_equipada,
                "x": origen[0],
                "y": origen[1],
                "dir_x": vel_x,
                "dir_y": vel_y,
            })

        elif self.game.robot.arma_equipada == 'misil':
            ancho, alto = Misil.ANCHO, Misil.ALTO
            origen, vel_x, vel_y = self.game.aim.get_datos_disparo(ancho, alto)
            m = Misil(origen[0], origen[1], vel_x, vel_y)
            m.owner = shooter
            self.game.misiles.append(m)
            self.game.enviar({
                "tipo": "disparo",
                "jugador": self.game.nombre_jugador,
                "arma": self.game.robot.arma_equipada,
                "x": origen[0],
                "y": origen[1],
                "dir_x": vel_x,
                "dir_y": vel_y,
            })

        # Disparo válido -> se acaba el turno
        if self.game.turn_manager.jugador_actual() == self.game.nombre_jugador:
            self.game.robot.vel_x = 0
            self.game.robot.current_animation = "idle"
            pygame.event.clear([pygame.KEYDOWN, pygame.KEYUP])
            self.game.robot.update([])

            self.game.enviar({"tipo": "turno_fin", "jugador": self.game.nombre_jugador})

            if self.game.host:
                self.game.turn_manager.forzar_fin_turno()
            else:
                self.game.turn_manager.en_cooldown = True
                self.game.turn_manager.cooldown_inicio = time.time()
                self.game.turn_manager.cooldown_restante_sync = self.game.turn_manager.cooldown

    def update(self):
        self._update_granadas()
        self._update_misiles()

    def draw(self, pantalla):
        for granada in self.game.granadas:
            granada.draw(pantalla)
        for misil in self.game.misiles:
            misil.draw(pantalla)

    # --- Granadas ---
    def _update_granadas(self):
        for granada in self.game.granadas[:]:
            granada.update(self.game.tiles, self.game.robot)

            for robot_estatico in self.game.robots_estaticos:
                if robot_estatico.nombre_jugador == getattr(granada, "owner", None):
                    continue
                granada.rebote_con_robot(robot_estatico)
                if granada.explotado and granada.estado == "explode":
                    if robot_estatico not in granada.danados and granada.get_hitbox().colliderect(robot_estatico.get_rect()):
                        daño = 70
                        puntos = daño
                        if robot_estatico.health - daño <= 0:
                            puntos = daño * 2
                        if self.game.host:
                            self.aplicar_dano(robot_estatico, daño)
                            self.game.enviar_evento_puntaje(granada.owner, puntos, robot_estatico)
                        granada.danados.add(robot_estatico)

            if not granada.explotado:
                granada.rebote_con_tiles(self.game.tiles)
                granada.rebote_con_robot(self.game.robot)
            elif granada.explotado and granada.estado == "explode" and not granada.ya_hizo_dano:
                collided_local = granada.get_hitbox().colliderect(self.game.robot.get_rect())
                if collided_local and self.game.robot not in granada.danados:
                    daño = 70
                    puntos = daño
                    if self.game.robot.health - daño <= 0:
                        puntos = daño * 2
                    if self.game.host:
                        print(f"[GRANADA] Host aplica {daño} a {self.game.nombre_jugador} por granada de {granada.owner}")
                        self.aplicar_dano(self.game.robot, daño)
                        self.game.enviar_evento_puntaje(granada.owner, puntos, self.game.robot)
                    else:
                        if getattr(granada, "owner", None) == self.game.nombre_jugador:
                            print(f"[GRANADA] Cliente {self.game.nombre_jugador} se hace {daño} (self-hit).")
                            self.game.robot.take_damage(daño)
                    granada.danados.add(self.game.robot)
                    granada.ya_hizo_dano = True

            if granada.estado == "done":
                try:
                    self.game.granadas.remove(granada)
                except ValueError:
                    pass

    def _update_misiles(self):
        for misil in self.game.misiles[:]:
            misil.update(self.game.tiles, self.game.robot)

            for robot_estatico in self.game.robots_estaticos:
                if robot_estatico.nombre_jugador == getattr(misil, "owner", None):
                    continue
                misil.colisiona_con_robot(robot_estatico)
                if misil.explotado and misil.estado == "explode":
                    if robot_estatico not in misil.danados and misil.get_hitbox().colliderect(robot_estatico.get_rect()):
                        daño = 50
                        puntos = daño
                        if robot_estatico.health - daño <= 0:
                            puntos = daño * 2
                        if self.game.host:
                            self.aplicar_dano(robot_estatico, daño)
                            self.game.enviar_evento_puntaje(misil.owner, puntos, robot_estatico)
                        misil.danados.add(robot_estatico)

            if not misil.explotado:
                misil.colisiona_con_tiles(self.game.tiles)
                misil.colisiona_con_robot(self.game.robot)
            elif misil.explotado and misil.estado == "explode" and not misil.ya_hizo_dano:
                collided_local = misil.get_hitbox().colliderect(self.game.robot.get_rect())
                if collided_local and self.game.robot not in misil.danados:
                    daño = 50
                    puntos = daño
                    if self.game.robot.health - daño <= 0:
                        puntos = daño * 2
                    if self.game.host:
                        print(f"[MISIL] Host aplica {daño} a {self.game.nombre_jugador} por misil de {misil.owner}")
                        self.aplicar_dano(self.game.robot, daño)
                        self.game.enviar_evento_puntaje(misil.owner, puntos, self.game.robot)
                    else:
                        if getattr(misil, "owner", None) == self.game.nombre_jugador:
                            print(f"[MISIL] Cliente {self.game.nombre_jugador} se hace {daño} (self-hit).")
                            self.game.robot.take_damage(daño)
                    misil.danados.add(self.game.robot)
                    misil.ya_hizo_dano = True

            if misil.estado == "done":
                try:
                    self.game.misiles.remove(misil)
                except ValueError:
                    pass

    def aplicar_dano(self, robot, cantidad):
        """Solo el host llama esto con autoridad real. Aplica el daño
        localmente y lo notifica a todos vía self.game.enviar()."""
        if self.game.host:
            robot.take_damage(cantidad)
            self.game.enviar({
                "tipo": "damage",
                "jugador": robot.nombre_jugador,
                "cantidad": cantidad,
                "quien": self.game.nombre_jugador,
            })
        else:
            if robot.es_remoto:
                self.game.enviar_dano(robot.nombre_jugador, cantidad)

    def recibir_disparo_remoto(self, msg):
        jugador = msg.get("jugador")
        if jugador == self.game.nombre_jugador:
            return
        arma = msg.get("arma")
        x, y = msg.get("x"), msg.get("y")
        dx, dy = msg.get("dir_x"), msg.get("dir_y")
        if arma == 'granada':
            g = Granada(x, y, dx, dy)
            g.owner = jugador
            self.game.granadas.append(g)
        elif arma == 'misil':
            m = Misil(x, y, dx, dy)
            m.owner = jugador
            self.game.misiles.append(m)
