# core/game_modes/multi_game.py
import pygame
import socket
import threading
import pickle
import time

from settings import ANCHO, ALTO, ALTURA_SUELO
from entities.players.robot import Robot
from entities.players.robot_estatico import RobotEstatico
from entities.weapons.granada import Granada
from entities.weapons.misil import Misil
from systems.collision import check_collisions, check_collisions_laterales_esquinas
from systems.aim_indicator import AimIndicator
from core.game_modes.base_game import BaseGame
from ui.hud import HUDPuntajes

class MultiplayerGame(BaseGame):
    """
    MultiplayerGame (modo UDP simple):
    - Si host=True actúa como servidor: recibe mensajes de clientes y los reenvía a todos.
    - Si host=False actúa como cliente: envía su estado al servidor y recibe estados de los demás.
    - Mensajes: {'tipo': 'update'|'shoot', ...}
    Nota: Esta es una versión simple para pruebas en LAN/localhost.
    """

    def __init__(self, nombre_jugador, personaje, host=False, server_ip="192.168.1.236", port=5000):
        super().__init__(nombre_jugador=nombre_jugador, personaje=personaje)

        # Estado de juego muy similar a FreeGame
        self.robot = Robot(
            x=ANCHO // 2 - 30,
            y=ALTO - 90 - ALTURA_SUELO,
            nombre_jugador=nombre_jugador,
            nombre_robot=personaje
        )
        self.robots_estaticos = []
        self.aim = AimIndicator(self.robot.get_centro())
        self.puntajes[self.robot] = 0
        self.hud_puntajes = HUDPuntajes(self)

        # Proyectiles
        self.granadas = []
        self.misiles = []

        # Robots remotos: nombre_jugador -> Robot
        self.robots_remotos = {}

        # Networking
        self.host = host
        self.server_ip = server_ip
        self.port = port

        # Socket UDP no bloqueante
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(False)

        # Si soy host, me uno al puerto público; si soy cliente me enlazo a puerto aleatorio local
        if self.host:
            try:
                # bind en todas las interfaces para recibir de clientes
                self.sock.bind(("0.0.0.0", self.port))
                print(f"[Multiplayer] Servidor iniciado en 0.0.0.0:{self.port}")
            except OSError as e:
                print("[Multiplayer] Error bind servidor:", e)
                raise
            # mantenemos una lista de clientes (addr) para reenviar mensajes
            self.known_clients = set()
        else:
            try:
                # bind en puerto aleatorio local para que recvfrom funcione en Windows
                self.sock.bind(("0.0.0.0", 0))
            except OSError as e:
                print("[Multiplayer] Error bind cliente:", e)
                raise
            print(f"[Multiplayer] Cliente listo (enviando a {self.server_ip}:{self.port})")

        # Hilo para escuchar mensajes entrantes
        self._listening = True
        self.thread = threading.Thread(target=self.listen, daemon=True)
        self.thread.start()

    def listen(self):
        """Hilo que recibe mensajes UDP y los procesa."""
        while self._listening:
            try:
                data, addr = self.sock.recvfrom(8192)
                try:
                    msg = pickle.loads(data)
                except Exception:
                    # mensaje corrupto; ignora
                    continue

                tipo = msg.get("tipo")
                if self.host:
                    # si soy host, registro al cliente y reenvío el mensaje a todos (excepto origen)
                    if addr not in self.known_clients:
                        self.known_clients.add(addr)
                        print(f"[Multiplayer - host] Cliente conectado: {addr}")
                    # reenviar a todos los clientes (incluido el que envió?) -> NO reenviamos al emisor
                    for client in list(self.known_clients):
                        if client != addr:
                            try:
                                self.sock.sendto(data, client)
                            except Exception:
                                # ignora errores individuales de envio
                                pass

                # Procesar mensaje localmente (tanto host como cliente deben actualizar estado)
                if tipo == "update":
                    jugador = msg.get("jugador")
                    x = msg.get("x", 0)
                    y = msg.get("y", 0)
                    personaje = msg.get("personaje", "default")
                    if jugador and jugador != self.nombre_jugador:
                        if jugador not in self.robots_remotos:
                            # crear robot remoto
                            self.robots_remotos[jugador] = Robot(x=x, y=y, nombre_jugador=jugador, nombre_robot=personaje)
                            # opcional: inicializar puntaje
                            self.puntajes[self.robots_remotos[jugador]] = 0
                        else:
                            self.robots_remotos[jugador].x = x
                            self.robots_remotos[jugador].y = y
                elif tipo == "shoot":
                    # Reproducir proyectil remoto (granada/misil)
                    jugador = msg.get("jugador")
                    if jugador == self.nombre_jugador:
                        # si el host reenvía también puede llegar el propio mensaje; lo ignoramos
                        continue
                    arma = msg.get("arma")
                    ox = msg.get("origen_x")
                    oy = msg.get("origen_y")
                    vx = msg.get("vel_x")
                    vy = msg.get("vel_y")
                    if arma == "granada":
                        g = Granada(ox, oy, vx, vy)
                        self.granadas.append(g)
                    elif arma == "misil":
                        m = Misil(ox, oy, vx, vy)
                        self.misiles.append(m)

            except BlockingIOError:
                # No hay datos ahora
                time.sleep(0.005)
            except OSError as e:
                # Errores de socket (ej. cerrados) — loguear y continuar o romper según convenga
                # Evitamos parar el hilo por completo
                # Si es recurrente, podrías romper el loop
                # print("[Multiplayer] OSError en listen:", e)
                time.sleep(0.05)
            except Exception as e:
                # Captura general para evitar que el hilo muera por excepción inesperada
                # print("[Multiplayer] Excepción en listen:", e)
                time.sleep(0.05)

    def enviar_estado(self):
        """Envia posición/estado básico al servidor (o lo pone en el socket local si soy host)."""
        data = {
            "tipo": "update",
            "jugador": self.nombre_jugador,
            "personaje": self.personaje,
            "x": float(self.robot.x),
            "y": float(self.robot.y)
        }
        payload = pickle.dumps(data)
        try:
            # Cliente -> servidor; Host también puede enviar a known_clients si quiere (no necesario)
            self.sock.sendto(payload, (self.server_ip, self.port))
        except Exception:
            # No bloqueante: ignorar fallos momentáneos
            pass

    def enviar_shoot(self, arma, origen, vel_x, vel_y):
        """Enviar disparo para que los remotos lo repliquen."""
        data = {
            "tipo": "shoot",
            "jugador": self.nombre_jugador,
            "arma": arma,
            "origen_x": float(origen[0]),
            "origen_y": float(origen[1]),
            "vel_x": float(vel_x),
            "vel_y": float(vel_y),
            "personaje": self.personaje
        }
        payload = pickle.dumps(data)
        try:
            self.sock.sendto(payload, (self.server_ip, self.port))
        except Exception:
            pass

    # Reutilizamos la lógica de disparo de FreeGame
    def disparar_arma(self):
        origen, vel_x, vel_y = self.aim.get_datos_disparo()
        if self.robot.arma_equipada == 'granada':
            ancho, alto = Granada.ANCHO, Granada.ALTO
            origen, vel_x, vel_y = self.aim.get_datos_disparo(ancho, alto)
            self.granadas.append(Granada(origen[0], origen[1], vel_x, vel_y))
            # avisar a remotos
            self.enviar_shoot("granada", origen, vel_x, vel_y)
        elif self.robot.arma_equipada == 'misil':
            ancho, alto = Misil.ANCHO, Misil.ALTO
            origen, vel_x, vel_y = self.aim.get_datos_disparo(ancho, alto)
            self.misiles.append(Misil(origen[0], origen[1], vel_x, vel_y))
            self.enviar_shoot("misil", origen, vel_x, vel_y)

    def actualizar_y_dibujar_granadas(self):
        # Copiado y adaptado de FreeGame
        for granada in self.granadas[:]:
            granada.update(self.tiles, self.robot)
            # daño a robots estáticos
            for robot_estatico in self.robots_estaticos:
                granada.rebote_con_robot(robot_estatico)
                if granada.explotado and granada.estado == "explode":
                    if robot_estatico not in granada.danados and granada.get_hitbox().colliderect(robot_estatico.get_rect()):
                        robot_estatico.take_damage(70)
                        puntos = 70
                        if robot_estatico.health <= 0:
                            puntos *= 2
                        self.puntajes[self.robot] += puntos
                        granada.danados.add(robot_estatico)
            # rebotes y daño al jugador local
            if not granada.explotado:
                granada.rebote_con_tiles(self.tiles)
                granada.rebote_con_robot(self.robot)
            elif granada.explotado and granada.estado == "explode" and not granada.ya_hizo_dano:
                if granada.get_hitbox().colliderect(self.robot.get_rect()):
                    self.robot.take_damage(70)
                    granada.ya_hizo_dano = True
            if granada.estado == "done":
                try:
                    self.granadas.remove(granada)
                except ValueError:
                    pass
        for granada in self.granadas:
            granada.draw(self.pantalla)

    def actualizar_y_dibujar_misiles(self):
        for misil in self.misiles[:]:
            misil.update(self.tiles, self.robot)
            for robot_estatico in self.robots_estaticos:
                misil.colisiona_con_robot(robot_estatico)
                if misil.explotado and misil.estado == "explode":
                    if robot_estatico not in misil.danados and misil.get_hitbox().colliderect(robot_estatico.get_rect()):
                        robot_estatico.take_damage(50)
                        puntos = 50
                        if robot_estatico.health <= 0:
                            puntos *= 2
                        self.puntajes[self.robot] += puntos
                        misil.danados.add(robot_estatico)
            if not misil.explotado:
                misil.colisiona_con_tiles(self.tiles)
                misil.colisiona_con_robot(self.robot)
            elif misil.explotado and misil.estado == "explode" and not misil.ya_hizo_dano:
                if misil.get_hitbox().colliderect(self.robot.get_rect()):
                    self.robot.take_damage(50)
                    misil.ya_hizo_dano = True
            if misil.estado == "done":
                try:
                    self.misiles.remove(misil)
                except ValueError:
                    pass
        for misil in self.misiles:
            misil.draw(self.pantalla)

    def run(self):
        """Loop principal: muy similar a FreeGame pero con envío/recepción de red."""
        while True:
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    # detener hilo de escucha y cerrar socket
                    self._listening = False
                    try:
                        self.sock.close()
                    except Exception:
                        pass
                    pygame.quit()
                    return

                # Pasar eventos al chat
                self.chat.handle_event(evento)

                # Manejo de HUD de armas (misma interfaz que FreeGame)
                arma_seleccionada = self.hud_armas.manejar_evento(evento)
                if arma_seleccionada is not None:
                    if arma_seleccionada == "spawn_robot":
                        nuevo_robot = RobotEstatico(400, 300)
                        self.robots_estaticos.append(nuevo_robot)
                    else:
                        self.robot.arma_equipada = arma_seleccionada

                # Click para disparar (igual que FreeGame)
                if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                    if not self.mouse_click_sostenido:
                        clic_sobre_hud = any(
                            rect.collidepoint(evento.pos) for _, rect in self.hud_armas.botones
                        )
                        if not clic_sobre_hud and self.robot.arma_equipada not in [None, 'nada']:
                            self.disparar_arma()
                            self.mouse_click_sostenido = True

                if evento.type == pygame.MOUSEBUTTONUP and evento.button == 1:
                    self.mouse_click_sostenido = False

            # Actualizaciones locales
            keys = pygame.key.get_pressed()
            self.robot.update(keys)
            if keys[pygame.K_DELETE]:
                self.robot.take_damage(50)

            # Actualizar robots estaticos (si hay)
            for robot_estatico in self.robots_estaticos:
                robot_estatico.update(self.tiles)
            self.robots_estaticos = [r for r in self.robots_estaticos if not r.debe_eliminarse()]

            # Colisiones físicas del jugador local
            check_collisions(self.robot, self.tiles)
            check_collisions_laterales_esquinas(self.robot, self.tiles_laterales)

            # Enviar estado de jugador (posición) al servidor / host
            self.enviar_estado()

            # Actualizar y dibujar escena
            self.draw_scene()

            # Dibujar personajes (local + remotos)
            self.robot.draw(self.pantalla)
            for r in list(self.robots_remotos.values()):
                r.draw(self.pantalla)

            # Armas en el mundo (local y proyectiles que llegaron de remotos)
            self.actualizar_y_dibujar_granadas()
            self.actualizar_y_dibujar_misiles()

            # Indicador de mira (solo se muestra si arma equipada)
            if self.robot.arma_equipada not in [None, 'nada']:
                mouse_pos = pygame.mouse.get_pos()
                self.aim.origen = self.robot.get_centro()
                self.aim.update(mouse_pos)
                self.aim.draw(self.pantalla)

            # HUDs
            # Aseguramos pasar font (fix al error anterior)
            self.hud_armas.draw(self.pantalla, self.font)
            self.hud_puntajes.draw(self.pantalla)

            # Mensajes de muerte
            self.robot.draw_death_message(self.pantalla, self.fuente_muerte)
            for robot_estatico in self.robots_estaticos:
                robot_estatico.draw_death_message(self.pantalla, self.fuente_muerte)

            # Chat
            self.chat.draw(self.pantalla)

            pygame.display.flip()
            self.reloj.tick(60)
