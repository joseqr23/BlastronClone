# systems/weapon_manager.py
from entities.weapons.granada import Granada
from entities.weapons.misil import Misil
from utils.sound_manager import sound_manager
import pygame


class WeaponManager:
    """
    Host: dueño real de la física de proyectiles (colisión, rebote,
    explosión, daño). Cliente: no simula nada, solo dibuja lo que el host
    le manda por 'proy_sync' (ver multi_game.py).
    """

    def __init__(self, game):
        self.game = game

    # ------------------------------------------------------------------
    # Disparo
    # ------------------------------------------------------------------
    def disparar(self):
        tm = self.game.turn_manager
        if tm.jugador_actual() != self.game.nombre_jugador or not tm.puede_disparar():
            print(f"[DEBUG] {self.game.nombre_jugador} intentó disparar fuera de turno o ya disparó.")
            return

        arma = self.game.robot.arma_equipada
        if arma not in ("granada", "misil"):
            return

        ancho, alto = (Granada.ANCHO, Granada.ALTO) if arma == "granada" else (Misil.ANCHO, Misil.ALTO)
        origen, vel_x, vel_y = self.game.aim.get_datos_disparo(ancho, alto)

        msg = {
            "tipo": "disparo",
            "jugador": self.game.nombre_jugador,
            "arma": arma,
            "x": origen[0],
            "y": origen[1],
            "dir_x": vel_x,
            "dir_y": vel_y,
        }

        # Bloqueo local inmediato: evita que un doble-click dispare dos
        # veces mientras se espera la confirmación por red.
        tm.disparo_hecho = True

        if self.game.host:
            self.crear_proyectil_host(msg)
        else:
            self.game.enviar(msg)

    def crear_proyectil_host(self, msg):
        """Solo el host llama esto (directo al disparar localmente, o al
        recibir un 'disparo' de un cliente). Crea el proyectil canónico
        y arranca la fase post_disparo del turno."""
        game = self.game
        if not game.host:
            return

        jugador = msg["jugador"]
        arma = msg["arma"]
        x, y, dx, dy = msg["x"], msg["y"], msg["dir_x"], msg["dir_y"]
        pid = game._next_proy_id()

        if arma == "granada":
            g = Granada(x, y, dx, dy)
            g.owner = jugador
            g.proj_id = pid
            game.granadas.append(g)
        elif arma == "misil":
            m = Misil(x, y, dx, dy)
            m.owner = jugador
            m.proj_id = pid
            game.misiles.append(m)
        else:
            return

        sound_manager.disparo(arma)
        game.turn_manager.registrar_disparo()

    # ------------------------------------------------------------------
    # Update / draw
    # ------------------------------------------------------------------
    def update(self):
        if self.game.host:
            self._update_granadas()
            self._update_misiles()
        # El cliente no simula física de proyectiles: su estado llega por
        # red vía "proy_sync" y se aplica directo en multi_game.py.

    def draw(self, pantalla):
        for granada in self.game.granadas:
            granada.draw(pantalla)
        for misil in self.game.misiles:
            misil.draw(pantalla)

    def _robots_para_colision(self, owner):
        """Todos los robots contra los que un proyectil puede
        colisionar/rebotar: el robot local y TODOS los remotos, incluido
        el propio dueño del proyectil — así el auto-daño funciona igual
        para el host que para cualquier cliente.

        Esta lista se pasa a granada/misil.update(), que revisa colisión
        en CADA sub-paso del movimiento (no solo al final del frame). Eso
        evita el tunneling a alta velocidad. Misil.py se encarga por su
        cuenta de no autodetonar contra su propio dueño justo al salir
        (margen de gracia de ~250ms)."""
        return [self.game.robot] + list(self.game.robots_estaticos)

    # ------------------------------------------------------------------
    # Física — SOLO se ejecuta en el host
    # ------------------------------------------------------------------
    def _update_granadas(self):
        for granada in self.game.granadas[:]:
            robots = self._robots_para_colision(getattr(granada, "owner", None))
            # El rebote contra tiles y contra TODOS los robots ya ocurre
            # dentro de update(), sub-paso por sub-paso.
            granada.update(self.game.tiles, robots)

            # --- Daño/puntaje contra robots remotos (incluye auto-daño) ---
            for robot_estatico in self.game.robots_estaticos:
                if granada.explotado and granada.estado == "explode":
                    if robot_estatico not in granada.danados and granada.get_hitbox().colliderect(robot_estatico.get_rect()):
                        daño = 70
                        puntos = daño
                        if robot_estatico.health - daño <= 0:
                            puntos = daño * 2
                        self.aplicar_dano(robot_estatico, daño)
                        # No dar puntos si el dueño de la granada es la
                        # misma víctima (auto-daño).
                        if getattr(granada, "owner", None) != robot_estatico.nombre_jugador:
                            self.game.enviar_evento_puntaje(granada.owner, puntos, robot_estatico)
                        granada.danados.add(robot_estatico)

            # --- Daño/puntaje contra el robot local (incluye auto-daño) ---
            if granada.explotado and granada.estado == "explode" and not granada.ya_hizo_dano:
                collided_local = granada.get_hitbox().colliderect(self.game.robot.get_rect())
                if collided_local and self.game.robot not in granada.danados:
                    daño = 70
                    puntos = daño
                    if self.game.robot.health - daño <= 0:
                        puntos = daño * 2
                    print(f"[GRANADA] Host aplica {daño} a {self.game.nombre_jugador} por granada de {granada.owner}")
                    self.aplicar_dano(self.game.robot, daño)
                    # No dar puntos si el dueño de la granada es la misma
                    # víctima (auto-daño).
                    if getattr(granada, "owner", None) != self.game.robot.nombre_jugador:
                        self.game.enviar_evento_puntaje(granada.owner, puntos, self.game.robot)
                    granada.danados.add(self.game.robot)
                    granada.ya_hizo_dano = True

            if granada.estado == "done":
                try:
                    self.game.granadas.remove(granada)
                except ValueError:
                    pass

    def _update_misiles(self):
        for misil in self.game.misiles[:]:
            robots = self._robots_para_colision(getattr(misil, "owner", None))
            # El impacto contra tiles y contra TODOS los robots ya ocurre
            # dentro de update(), sub-paso por sub-paso.
            misil.update(self.game.tiles, robots)

            for robot_estatico in self.game.robots_estaticos:
                if misil.explotado and misil.estado == "explode":
                    if robot_estatico not in misil.danados and misil.get_hitbox().colliderect(robot_estatico.get_rect()):
                        daño = 50
                        puntos = daño
                        if robot_estatico.health - daño <= 0:
                            puntos = daño * 2
                        self.aplicar_dano(robot_estatico, daño)
                        if getattr(misil, "owner", None) != robot_estatico.nombre_jugador:
                            self.game.enviar_evento_puntaje(misil.owner, puntos, robot_estatico)
                        misil.danados.add(robot_estatico)

            if misil.explotado and misil.estado == "explode" and not misil.ya_hizo_dano:
                collided_local = misil.get_hitbox().colliderect(self.game.robot.get_rect())
                if collided_local and self.game.robot not in misil.danados:
                    daño = 50
                    puntos = daño
                    if self.game.robot.health - daño <= 0:
                        puntos = daño * 2
                    print(f"[MISIL] Host aplica {daño} a {self.game.nombre_jugador} por misil de {misil.owner}")
                    self.aplicar_dano(self.game.robot, daño)
                    if getattr(misil, "owner", None) != self.game.robot.nombre_jugador:
                        self.game.enviar_evento_puntaje(misil.owner, puntos, self.game.robot)
                    misil.danados.add(self.game.robot)
                    misil.ya_hizo_dano = True

            if misil.estado == "done":
                try:
                    self.game.misiles.remove(misil)
                except ValueError:
                    pass

    def aplicar_dano(self, robot, cantidad):
        """Solo se llama desde el host. Aplica el daño localmente y lo
        notifica a todos los clientes."""
        if not self.game.host:
            return
        robot.take_damage(cantidad)
        self.game.enviar({
            "tipo": "damage",
            "jugador": robot.nombre_jugador,
            "cantidad": cantidad,
            "quien": self.game.nombre_jugador,
        })
