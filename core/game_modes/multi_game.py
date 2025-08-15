# core/game_modes/multi_game.py
import pygame
import time
import threading
import pickle
from core.network import Server, Client
from entities.players.robot import Robot
from entities.players.robot_estatico import RobotEstatico
from entities.weapons.granada import Granada
from entities.weapons.misil import Misil
from systems.collision import check_collisions, check_collisions_laterales_esquinas
from systems.aim_indicator import AimIndicator
from core.game_modes.base_game import BaseGame


class MultiGame(BaseGame):
    def __init__(self, nombre_jugador, personaje, is_host=True, ip='localhost', port=5000, partida_config=None):
        super().__init__(nombre_jugador=nombre_jugador, personaje=personaje)

        self.is_host = is_host
        self.partida_config = partida_config or {
            "tipo": "puntos",
            "tiempo_partida": 300,
            "tiempo_turno": 15,
            "nombre": "Sala1",
            "password": ""
        }

        # Jugadores
        self.robot = Robot(
            x=pygame.display.get_window_size()[0] // 2 - 30,
            y=pygame.display.get_window_size()[1] - 90 - 70,
            nombre_jugador=nombre_jugador,
            nombre_robot=personaje
        )
        self.robots_estaticos = []
        self.robots_multijugador = [self.robot]
        self.aim = AimIndicator(self.robot.get_centro())
        self.puntajes[self.robot] = 0

        # Red
        if self.is_host:
            self.server = Server(ip, port)
            self.server_thread = threading.Thread(target=self.server.run, daemon=True)
            self.server_thread.start()
        else:
            self.client = Client(ip, port, nombre_jugador)
            self.client.on_update_players = self.sync_players
            self.client.on_start_game = self.start_game_from_host
            self.client_thread = threading.Thread(target=self.listen_client, daemon=True)
            self.client_thread.start()

        # Turnos
        self.turn_index = 0
        self.turn_timer = 0
        self.turn_active = False

        # Tiempo de partida
        self.start_time = time.time()
        self.game_over = False

    # ---------------------
    # MULTIJUGADOR
    # ---------------------
    def listen_client(self):
        while True:
            try:
                data = self.client.sock.recv(4096)
                mensaje = pickle.loads(data)

                if isinstance(mensaje, dict):
                    # Turnos
                    self.turn_index = mensaje.get("turn_index", self.turn_index)
                    self.turn_timer = mensaje.get("turn_timer", self.turn_timer)
                    self.turn_active = True

                    # Nuevos jugadores
                    if "players" in mensaje:
                        self.sync_players(mensaje["players"])

                    # Proyectiles
                    if "proyectil" in mensaje:
                        info = mensaje["proyectil"]
                        if info["tipo"] == "granada":
                            g = Granada(info["x"], info["y"], info["vel_x"], info["vel_y"])
                            self.granadas.append(g)
                        elif info["tipo"] == "misil":
                            m = Misil(info["x"], info["y"], info["vel_x"], info["vel_y"])
                            self.misiles.append(m)

                    # Daños
                    if "daño" in mensaje:
                        info = mensaje["daño"]
                        jugador_afectado = info["jugador"]
                        cantidad = info["cantidad"]
                        killer = info["killer"]

                        for r in self.robots_multijugador + self.robots_estaticos:
                            if r.nombre == jugador_afectado:
                                r.take_damage(cantidad)
                                for rob in self.robots_multijugador:
                                    if rob.nombre == killer:
                                        self.puntajes[rob] += cantidad
                                break

                else:
                    self.chat.agregar_mensaje(str(mensaje))
            except:
                self.chat.agregar_mensaje("¡Conexión perdida!")
                break

    def sync_players(self, lista_nombres):
        nuevos_robots = []
        for i, nombre in enumerate(lista_nombres):
            if i == 0 and nombre == self.robot.nombre:
                nuevos_robots.append(self.robot)
            else:
                nuevo_robot = RobotEstatico(100 + i*100, self.robot.y, nombre_jugador=nombre)
                nuevos_robots.append(nuevo_robot)
        self.robots_multijugador = nuevos_robots
        for r in self.robots_multijugador:
            if r not in self.puntajes:
                self.puntajes[r] = 0

    def start_game_from_host(self, config):
        self.partida_config = config
        self.start_time = time.time()
        self.game_over = False
        self.turn_index = 0
        self.turn_timer = self.partida_config["tiempo_turno"]
        self.turn_active = True

    def send_chat(self, texto):
        if self.is_host:
            self.chat.agregar_mensaje(f"{self.nombre_jugador}: {texto}")
            self.server.broadcast(f"{self.nombre_jugador}: {texto}")
        else:
            self.client.sock.send(pickle.dumps(f"{self.nombre_jugador}: {texto}"))

    # ---------------------
    # TURNOS
    # ---------------------
    def start_turn(self):
        self.turn_index = (self.turn_index + 1) % len(self.robots_multijugador)
        self.turn_timer = self.partida_config["tiempo_turno"]
        self.turn_active = True

        if self.is_host:
            data = {"turn_index": self.turn_index, "turn_timer": self.turn_timer}
            self.server.broadcast(data)

    def update_turn(self, dt):
        if self.turn_active:
            self.turn_timer -= dt
            if self.turn_timer <= 0:
                self.turn_active = False
                self.start_turn()

    # ---------------------
    # ACTUALIZACIÓN
    # ---------------------
    def update(self, dt, keys):
        if not self.game_over:
            for robot in self.robots_multijugador:
                robot.update(keys)
            for robot_estatico in self.robots_estaticos:
                robot_estatico.update(self.tiles)

            for robot in self.robots_multijugador:
                check_collisions(robot, self.tiles)
                check_collisions_laterales_esquinas(robot, self.tiles_laterales)

            self.actualizar_y_dibujar_granadas()
            self.actualizar_y_dibujar_misiles()

            self.update_turn(dt)

            elapsed = time.time() - self.start_time
            if elapsed >= self.partida_config["tiempo_partida"]:
                self.game_over = True

    # ---------------------
    # DIBUJADO
    # ---------------------
    def draw(self, pantalla):
        self.draw_scene()
        for robot in self.robots_multijugador:
            robot.draw(pantalla)
        for robot_estatico in self.robots_estaticos:
            robot_estatico.draw(pantalla)

        if self.robot.arma_equipada not in [None, 'nada']:
            mouse_pos = pygame.mouse.get_pos()
            self.aim.origen = self.robot.get_centro()
            self.aim.update(mouse_pos)
            self.aim.draw(pantalla)

        self.hud_armas.draw(pantalla, self.font)

        for robot, pts in self.puntajes.items():
            text = self.font.render(f"{robot.nombre}: {pts}", True, (255, 255, 0))
            pantalla.blit(text, (10, 10 + 20 * (list(self.puntajes.keys()).index(robot) + 1)))

        if self.robots_multijugador:
            turno_robot = self.robots_multijugador[self.turn_index]
            turno_text = self.font.render(f"Turno: {turno_robot.nombre} ({int(self.turn_timer)}s)", True, (255, 255, 0))
            pantalla.blit(turno_text, (10, 10))

        self.chat.draw(pantalla)
        pygame.display.flip()

    # ---------------------
    # DISPAROS MULTIJUGADOR
    # ---------------------
    def disparar_arma(self):
        origen, vel_x, vel_y = self.aim.get_datos_disparo()
        proyectil_info = None

        if self.robot.arma_equipada == 'granada':
            ancho, alto = Granada.ANCHO, Granada.ALTO
            origen, vel_x, vel_y = self.aim.get_datos_disparo(ancho, alto)
            granada = Granada(origen[0], origen[1], vel_x, vel_y)
            self.granadas.append(granada)
            proyectil_info = {
                "tipo": "granada",
                "x": origen[0],
                "y": origen[1],
                "vel_x": vel_x,
                "vel_y": vel_y,
                "jugador": self.robot.nombre
            }

        elif self.robot.arma_equipada == 'misil':
            ancho, alto = Misil.ANCHO, Misil.ALTO
            origen, vel_x, vel_y = self.aim.get_datos_disparo(ancho, alto)
            misil = Misil(origen[0], origen[1], vel_x, vel_y)
            self.misiles.append(misil)
            proyectil_info = {
                "tipo": "misil",
                "x": origen[0],
                "y": origen[1],
                "vel_x": vel_x,
                "vel_y": vel_y,
                "jugador": self.robot.nombre
            }

        if proyectil_info:
            if self.is_host:
                self.server.broadcast({"proyectil": proyectil_info})
            else:
                self.client.sock.send(pickle.dumps({"proyectil": proyectil_info}))

    # ---------------------
    # ARMAS Y DAÑOS
    # ---------------------
    def actualizar_y_dibujar_granadas(self):
        for granada in self.granadas[:]:
            granada.update(self.tiles, self.robot)
            for robot_estatico in self.robots_estaticos:
                granada.rebote_con_robot(robot_estatico)
                if granada.explotado and granada.estado == "explode":
                    if robot_estatico not in granada.danados and granada.get_hitbox().colliderect(robot_estatico.get_rect()):
                        dano = 70
                        robot_estatico.take_damage(dano)
                        puntos = dano * (2 if robot_estatico.health <= 0 else 1)
                        self.puntajes[self.robot] += puntos
                        granada.danados.add(robot_estatico)

                        if self.is_host:
                            info = {
                                "daño": {
                                    "jugador": robot_estatico.nombre,
                                    "cantidad": dano,
                                    "killer": self.robot.nombre
                                }
                            }
                            self.server.broadcast(info)

            if not granada.explotado:
                granada.rebote_con_tiles(self.tiles)
                granada.rebote_con_robot(self.robot)
            elif granada.explotado and granada.estado == "explode" and not granada.ya_hizo_dano:
                if granada.get_hitbox().colliderect(self.robot.get_rect()):
                    dano = 70
                    self.robot.take_damage(dano)
                    granada.ya_hizo_dano = True
                    if self.is_host:
                        info = {
                            "daño": {
                                "jugador": self.robot.nombre,
                                "cantidad": dano,
                                "killer": self.robot.nombre
                            }
                        }
                        self.server.broadcast(info)

            if granada.estado == "done":
                self.granadas.remove(granada)

        for granada in self.granadas:
            granada.draw(self.pantalla)

    def actualizar_y_dibujar_misiles(self):
        for misil in self.misiles[:]:
            misil.update(self.tiles, self.robot)
            for robot_estatico in self.robots_estaticos:
                misil.colisiona_con_robot(robot_estatico)
                if misil.explotado and misil.estado == "explode":
                    if robot_estatico not in misil.danados and misil.get_hitbox().colliderect(robot_estatico.get_rect()):
                        dano = 50
                        robot_estatico.take_damage(dano)
                        puntos = dano * (2 if robot_estatico.health <= 0 else 1)
                        self.puntajes[self.robot] += puntos
                        misil.danados.add(robot_estatico)

                        if self.is_host:
                            info = {
                                "daño": {
                                    "jugador": robot_estatico.nombre,
                                    "cantidad": dano,
                                    "killer": self.robot.nombre
                                }
                            }
                            self.server.broadcast(info)

            if not misil.explotado:
                misil.colisiona_con_tiles(self.tiles)
                misil.colisiona_con_robot(self.robot)
            elif misil.explotado and misil.estado == "explode" and not misil.ya_hizo_dano:
                if misil.get_hitbox().colliderect(self.robot.get_rect()):
                    dano = 50
                    self.robot.take_damage(dano)
                    misil.ya_hizo_dano = True
                    if self.is_host:
                        info = {
                            "daño": {
                                "jugador": self.robot.nombre,
                                "cantidad": dano,
                                "killer": self.robot.nombre
                            }
                        }
                        self.server.broadcast(info)

            if misil.estado == "done":
                self.misiles.remove(misil)

        for misil in self.misiles:
            misil.draw(self.pantalla)
