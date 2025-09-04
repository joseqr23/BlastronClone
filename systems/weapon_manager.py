from entities.weapons.granada import Granada
from entities.weapons.misil import Misil
import pickle

class WeaponManager:
    def __init__(self, game):
        self.game = game

    def disparar(self):
        origen, vel_x, vel_y = self.game.aim.get_datos_disparo()
        shooter = self.game.nombre_jugador  # dueño local

        if self.game.robot.arma_equipada == 'granada':
            ancho, alto = Granada.ANCHO, Granada.ALTO
            origen, vel_x, vel_y = self.game.aim.get_datos_disparo(ancho, alto)
            g = Granada(origen[0], origen[1], vel_x, vel_y)
            g.owner = shooter
            self.game.granadas.append(g)

        elif self.game.robot.arma_equipada == 'misil':
            ancho, alto = Misil.ANCHO, Misil.ALTO
            origen, vel_x, vel_y = self.game.aim.get_datos_disparo(ancho, alto)
            m = Misil(origen[0], origen[1], vel_x, vel_y)
            m.owner = shooter
            self.game.misiles.append(m)

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
                granada.rebote_con_robot(robot_estatico)
                if granada.explotado and granada.estado == "explode":
                    if robot_estatico not in granada.danados and granada.get_hitbox().colliderect(robot_estatico.get_rect()):
                        self.aplicar_dano(robot_estatico, 70) #robot_estatico.take_damage(70)
                        puntos = 70
                        if robot_estatico.health <= 0:
                            puntos *= 2
                        #self.game.puntajes[self.game.robot] += puntos
                        self.enviar_evento_puntaje(self.game.robot.nombre_jugador, puntos, robot_estatico)
                        granada.danados.add(robot_estatico)

            if not granada.explotado:
                granada.rebote_con_tiles(self.game.tiles)
                granada.rebote_con_robot(self.game.robot)
            elif granada.explotado and granada.estado == "explode" and not granada.ya_hizo_dano:
                # SOLO me pego daño local si YO soy el dueño del proyectil
                if getattr(granada, "owner", self.game.nombre_jugador) == self.game.nombre_jugador:
                    if granada.get_hitbox().colliderect(self.game.robot.get_rect()):
                        self.game.robot.take_damage(70)
                        granada.ya_hizo_dano = True

            if granada.estado == "done":
                self.game.granadas.remove(granada)

    # --- Misiles ---
    def _update_misiles(self):
        for misil in self.game.misiles[:]:
            misil.update(self.game.tiles, self.game.robot)
            for robot_estatico in self.game.robots_estaticos:
                misil.colisiona_con_robot(robot_estatico)
                if misil.explotado and misil.estado == "explode":
                    if robot_estatico not in misil.danados and misil.get_hitbox().colliderect(robot_estatico.get_rect()):
                        self.aplicar_dano(robot_estatico, 50) #robot_estatico.take_damage(50)
                        puntos = 50
                        if robot_estatico.health <= 0:
                            puntos *= 2
                        #self.game.puntajes[self.game.robot] += puntos
                        self.enviar_evento_puntaje(self.game.robot.nombre_jugador, puntos, robot_estatico)
                        misil.danados.add(robot_estatico)

            if not misil.explotado:
                misil.colisiona_con_tiles(self.game.tiles)
                misil.colisiona_con_robot(self.game.robot)
            elif misil.explotado and misil.estado == "explode" and not misil.ya_hizo_dano:
                # SOLO me pego daño local si YO soy el dueño del proyectil
                if getattr(misil, "owner", self.game.nombre_jugador) == self.game.nombre_jugador:
                    if misil.get_hitbox().colliderect(self.game.robot.get_rect()):
                        self.game.robot.take_damage(50)
                        misil.ya_hizo_dano = True

            if misil.estado == "done":
                self.game.misiles.remove(misil)

    def aplicar_dano(self, robot, cantidad):
        if robot.es_remoto:
            # Debug: quien está enviando el damage y a quién
            print(f"[DEBUG] enviar_dano: desde {self.game.nombre_jugador} -> {robot.nombre_jugador} amt={cantidad}")
            self.game.enviar_dano(robot.nombre_jugador, cantidad)
        else:
            print(f"[DEBUG] daño_local: {self.game.nombre_jugador} recibe {cantidad}")
            robot.take_damage(cantidad)

    def recibir_disparo_remoto(self, msg):
        """Crea un proyectil que disparó otro jugador y lo marca con su owner."""
        arma = msg.get("arma")
        x, y = msg.get("x"), msg.get("y")
        dx, dy = msg.get("dir_x"), msg.get("dir_y")
        owner = msg.get("owner") or msg.get("jugador")

        if arma == 'granada':
            g = Granada(x, y, dx, dy)
            g.owner = owner
            self.game.granadas.append(g)

        elif arma == 'misil':
            m = Misil(x, y, dx, dy)
            m.owner = owner
            self.game.misiles.append(m)

    def enviar_evento_puntaje(self, atacante, puntos, victima):
        # ❌ Quitar esto (duplicaba en el host)
        # self.game.puntajes[atacante] = self.game.puntajes.get(atacante, 0) + puntos

        # Armar mensaje para todos
        msg = {
            "tipo": "score",
            "atacante": atacante,
            "puntos": puntos,
            "victima": victima.nombre_jugador,
            "victima_dead": victima.health <= 0
        }
        try:
            self.game.sock.sendto(pickle.dumps(msg), (self.game.server_ip, self.game.port))
        except Exception:
            pass