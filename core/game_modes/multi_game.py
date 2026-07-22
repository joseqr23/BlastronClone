# core/game_modes/multi_game.py
"""
MultiplayerGame — v4: proyectiles host-autoritativos y genéricos.

1. Los proyectiles YA NO se simulan de forma independiente en cada
   máquina. Solo el HOST corre física real (colisión, rebote/impacto,
   explosión, daño). Los clientes reciben snapshots ("proy_sync") con la
   posición/estado de cada proyectil activo y solo los dibujan.

2. Cada proyectil tiene un proj_id único asignado por el host.

3. self.robots_estaticos se actualiza ANTES de weapon_manager.update().

4. TurnManager maneja una fase intermedia "post_disparo": tras disparar,
   el jugador no puede volver a disparar pero puede seguir moviéndose
   unos segundos antes de que el turno termine.

5. Las armas ya no están hardcodeadas (Granada/Misil): son instancias de
   Proyectil configuradas por assets/weapons/<arma>/config.json, y viven
   todas juntas en self.proyectiles (una sola lista, sin importar el
   arma) — ver entities/weapons/proyectil.py y utils/weapon_loader.py.
"""

import pygame
import socket
import threading
import struct
import json
import time
import queue

from settings import ANCHO, ALTO, ALTURA_SUELO
from entities.players.robot import Robot
from entities.weapons.proyectil import Proyectil
from utils.weapon_loader import cargar_armas
from utils.sound_manager import sound_manager
from core.game_modes.base_game import BaseGame
from systems.collision import check_collisions, check_collisions_laterales_esquinas
from systems.aim_indicator import AimIndicator
from systems.weapon_manager import WeaponManager
from systems.hud_manager import HUDManager
from ui.hud import HUDPuntajesMultiplayer, HUDArmas, HUDTimer, HUDTurnos
from systems.event_handler import EventHandler
from ui.chat import Chat
from systems.turn_manager import TurnManager


# ----------------------------------------------------------------------
# Framing de mensajes sobre TCP
# ----------------------------------------------------------------------
def _send_framed(sock, msg: dict):
    data = json.dumps(msg).encode("utf-8")
    header = struct.pack("!I", len(data))
    sock.sendall(header + data)


def _extraer_mensajes(buffer: bytearray):
    mensajes = []
    while True:
        if len(buffer) < 4:
            break
        (length,) = struct.unpack("!I", buffer[:4])
        if len(buffer) < 4 + length:
            break
        payload = bytes(buffer[4:4 + length])
        buffer = buffer[4 + length:]
        try:
            mensajes.append(json.loads(payload.decode("utf-8")))
        except json.JSONDecodeError:
            pass
    return mensajes, buffer


class MultiplayerGame(BaseGame):
    """MultiplayerGame con red TCP confiable, host autoritativo para
    turnos/daño/score/proyectiles, y sincronización de robots remotos."""

    def __init__(self, nombre_jugador, personaje, host=True, server_ip="127.0.0.1", port=5000, duracion_min=3, modo_partida="puntos"):
        super().__init__(nombre_jugador=nombre_jugador, personaje=personaje)
        self.modo_partida = modo_partida  # solo "puntos" implementado por ahora

        # --- Robot local ---
        self.robot = Robot(
            x=ANCHO // 2 - 30,
            y=ALTO - 90 - ALTURA_SUELO,
            nombre_jugador=nombre_jugador,
            nombre_robot=personaje
        )

        # --- Robots remotos ---
        self.robots_remotos = {}
        self.robots_estaticos = []
        self._ultimo_seq_recibido = {}

        # Los proyectiles activos ya viven en self.proyectiles (una sola
        # lista para cualquier arma), inicializada en BaseGame.__init__.
        self._proy_id_counter = 0

        # --- HUD, armas y chat ---
        self.aim = AimIndicator(self.robot.get_centro())
        self.weapon_manager = WeaponManager(self)
        self.puntajes[self.nombre_jugador] = 0
        self.hud_puntajes = HUDPuntajesMultiplayer(self)
        self.hud_armas = HUDArmas(list(cargar_armas().keys()))
        self.hud_manager = HUDManager(self)
        self.chat = Chat(nombre_jugador, game=self)
        self.event_handler = EventHandler(self)
        self.mouse_click_sostenido = False
        self.font = pygame.font.SysFont("Arial", 16)

        # --- Networking (TCP) ---
        self.host = host
        self.server_ip = server_ip
        self.port = port
        self._seq_local = 0

        self._incoming = queue.Queue()
        self._listening = True
        self._client_sockets = []
        self._client_sockets_lock = threading.Lock()
        self._server_socket = None
        self._client_socket = None

        if self.host:
            self._iniciar_host()
        else:
            self._iniciar_cliente()

        # Tiempo de juego
        self.tiempo_total = duracion_min * 60
        self.tiempo_restante = self.tiempo_total
        self.ultimo_tick = time.time()
        self.game_over = False
        self.timer_hud = HUDTimer(self, duracion=self.tiempo_total, posicion=(ANCHO // 2, 30))

        # Turnos
        self.turn_manager = TurnManager(self)
        self.hud_turnos = HUDTurnos(self.turn_manager, posicion=(ANCHO // 2 - 80, 60))
        self.turnos_iniciados = False
        self.partida_iniciada = False

    # ------------------------------------------------------------------
    # Conexión
    # ------------------------------------------------------------------
    def _iniciar_host(self):
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind(("0.0.0.0", self.port))
        self._server_socket.listen(8)
        print(f"[Multiplayer] Servidor TCP escuchando en 0.0.0.0:{self.port}")
        threading.Thread(target=self._aceptar_clientes, daemon=True).start()

    def _iniciar_cliente(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.server_ip, self.port))
        self._client_socket = sock
        print(f"[Multiplayer] Conectado al host {self.server_ip}:{self.port}")
        threading.Thread(target=self._recibir_de_socket, args=(sock,), daemon=True).start()

    def _aceptar_clientes(self):
        while self._listening:
            try:
                conn, addr = self._server_socket.accept()
            except OSError:
                break
            print(f"[Host] Cliente conectado: {addr}")
            with self._client_sockets_lock:
                self._client_sockets.append(conn)
            threading.Thread(target=self._recibir_de_socket, args=(conn,), daemon=True).start()

    def _recibir_de_socket(self, sock):
        buffer = bytearray()
        while self._listening:
            try:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                buffer.extend(chunk)
                mensajes, buffer = _extraer_mensajes(buffer)
                for msg in mensajes:
                    self._incoming.put((msg, sock))
            except (ConnectionResetError, OSError):
                break
            except Exception as e:
                print(f"[Multiplayer] error de recepción: {e}")
                break
        with self._client_sockets_lock:
            if sock in self._client_sockets:
                self._client_sockets.remove(sock)

    # ------------------------------------------------------------------
    # Envío
    # ------------------------------------------------------------------
    def enviar(self, msg, excluir_socket=None):
        if self.host:
            with self._client_sockets_lock:
                sockets = list(self._client_sockets)
            for s in sockets:
                if s is excluir_socket:
                    continue
                try:
                    _send_framed(s, msg)
                except Exception:
                    pass
        else:
            if self._client_socket:
                try:
                    _send_framed(self._client_socket, msg)
                except Exception:
                    pass

    def enviar_estado(self):
        self._seq_local += 1
        self.enviar({
            "tipo": "update",
            "jugador": self.nombre_jugador,
            "personaje": self.personaje,
            "seq": self._seq_local,
            "x": float(self.robot.x),
            "y": float(self.robot.y),
            "frame": self.robot.frame_index,
            "estado": self.robot.current_animation,
            "direccion": 1 if self.robot.facing_right else -1,
            "health": self.robot.health,
        })

    def enviar_chat(self, mensaje):
        self.enviar({"tipo": "chat", "jugador": self.nombre_jugador, "mensaje": mensaje})

    def enviar_evento_puntaje(self, atacante, puntos, victima):
        """Solo debe llamarse desde el host (autoridad de daño)."""
        if not self.host:
            return
        self.puntajes[atacante] = self.puntajes.get(atacante, 0) + puntos
        if victima.health <= 0:
            self.chat.agregar_mensaje(f"{victima.nombre_jugador} fue detonado por {atacante}!")
        print(f"[SCORE] {atacante} ganó {puntos} puntos por dañar a {victima.nombre_jugador}")
        self.enviar({
            "tipo": "score",
            "atacante": atacante,
            "puntos": puntos,
            "victima": victima.nombre_jugador,
            "victima_dead": victima.health <= 0,
        })

    def _next_proy_id(self):
        self._proy_id_counter += 1
        return self._proy_id_counter

    def _sync_proyectiles(self):
        """Solo el host llama esto: transmite el estado real de cada
        proyectil activo (sin importar el arma) para que los clientes lo
        dibujen tal cual."""
        if not self.host:
            return
        items = []
        for p in self.proyectiles:
            items.append({
                "id": getattr(p, "proj_id", None),
                "tipo": p.tipo,
                "owner": getattr(p, "owner", None),
                "x": p.x, "y": p.y,
                "vel_x": p.vel_x, "vel_y": p.vel_y,
                "estado": getattr(p, "estado", None),
                "explotado": getattr(p, "explotado", False),
            })
        self.enviar({"tipo": "proy_sync", "items": items})

    # ------------------------------------------------------------------
    # Procesamiento de mensajes — SIEMPRE en el hilo principal
    # ------------------------------------------------------------------
    def _procesar_mensajes_pendientes(self):
        while True:
            try:
                msg, origen_sock = self._incoming.get_nowait()
            except queue.Empty:
                break
            if self.host and msg.get("tipo") not in ("damage", "disparo"):
                self.enviar(msg, excluir_socket=origen_sock)
            self._procesar_mensaje(msg)

    def _procesar_mensaje(self, msg):
        tipo = msg.get("tipo")

        if tipo == "update":
            jugador = msg.get("jugador")
            if jugador == self.nombre_jugador:
                return
            seq = msg.get("seq", 0)
            ultimo = self._ultimo_seq_recibido.get(jugador, -1)
            if seq <= ultimo:
                return
            self._ultimo_seq_recibido[jugador] = seq

            if jugador not in self.robots_remotos:
                r = Robot(
                    x=msg["x"], y=msg["y"],
                    nombre_jugador=jugador,
                    nombre_robot=msg.get("personaje", "default"),
                    es_remoto=True,
                )
                r.target_x, r.target_y = r.x, r.y
                r.is_dead = (msg.get("estado", "idle") == "death")
                self.robots_remotos[jugador] = r
                if jugador not in self.puntajes:
                    self.puntajes[jugador] = 0
            else:
                r = self.robots_remotos[jugador]
                anim_anterior = r.current_animation
                r.target_x = msg["x"]
                r.target_y = msg["y"]
                r.frame_index = msg.get("frame", 0)
                r.current_animation = msg.get("estado", "idle")
                r.facing_right = (msg.get("direccion", 1) == 1)
                r.is_dead = (r.current_animation == "death")
                if r.current_animation == "jump" and anim_anterior != "jump":
                    sound_manager.salto()
            if "health" in msg:
                self.robots_remotos[jugador].health = msg["health"]

        elif tipo == "disparo":
            if self.host:
                self.weapon_manager.crear_proyectil_host(msg)

        elif tipo == "proy_sync":
            if not self.host:
                self._aplicar_proy_sync(msg.get("items", []))

        elif tipo == "damage":
            jugador = msg["jugador"]
            cantidad = msg["cantidad"]
            if jugador == self.nombre_jugador:
                self.robot.take_damage(cantidad)
            elif jugador in self.robots_remotos:
                self.robots_remotos[jugador].take_damage(cantidad)

        elif tipo == "score":
            atacante = msg["atacante"]
            puntos = msg["puntos"]
            victima = msg["victima"]
            victima_dead = msg.get("victima_dead", False)
            self.puntajes[atacante] = self.puntajes.get(atacante, 0) + puntos
            if victima_dead:
                self.chat.agregar_mensaje(f"{victima} fue detonado por {atacante}!")

        elif tipo == "chat":
            jugador = msg.get("jugador")
            if jugador != self.nombre_jugador:
                self.chat.agregar_mensaje(msg["mensaje"])

        elif tipo == "timer":
            self.tiempo_restante = msg["restante"]
            if self.tiempo_restante <= 0:
                self.game_over = True

        elif tipo == "turnos_init":
            self.turn_manager.iniciar(msg["jugadores"])

        elif tipo == "turno_sync":
            jugador = msg["jugador"]
            if jugador in self.turn_manager.jugadores:
                self.turn_manager.turno_actual = self.turn_manager.jugadores.index(jugador)
            fase = msg.get("fase", "turno")
            self.turn_manager.fase = fase
            self.turn_manager.en_cooldown = (fase == "cooldown")
            if fase == "cooldown":
                self.turn_manager.cooldown_restante_sync = msg["tiempo"]
                self.turn_manager.turno_inicio = None
            elif fase == "post_disparo":
                self.turn_manager.post_disparo_restante_sync = msg["tiempo"]
                self.turn_manager.disparo_hecho = True
            else:
                self.turn_manager.turno_restante_sync = msg["tiempo"]
                self.turn_manager.cooldown_inicio = None
                self.turn_manager.disparo_hecho = False

        elif tipo == "turno_fin":
            jugador = msg.get("jugador")
            print(f"[NET] Fin de turno de {jugador}")
            if self.host:
                self.turn_manager.forzar_fin_turno()
            else:
                if jugador == self.turn_manager.jugador_actual():
                    self.turn_manager.iniciar_cooldown()
            target = None
            if jugador == self.nombre_jugador:
                target = self.robot
            elif jugador in self.robots_remotos:
                target = self.robots_remotos[jugador]
            if target:
                target.vel_x = 0
                target.vel_y = 0
                target.current_animation = "idle"

        elif tipo == "iniciar_partida":
            self.partida_iniciada = True
            self.ultimo_tick = time.time()
            print(f"[{self.nombre_jugador}] recibió señal de inicio de partida")

    def _aplicar_proy_sync(self, items):
        """Cliente: aplica el snapshot de proyectiles del host. No se
        calcula ninguna física ni colisión aquí, solo se refleja el
        estado. Funciona para cualquier arma, no solo granada/misil."""
        ids_recibidos = set()
        for item in items:
            pid = item.get("id")
            if pid is None:
                continue
            ids_recibidos.add(pid)
            proxy = next((p for p in self.proyectiles if getattr(p, "proj_id", None) == pid), None)
            if proxy is None:
                proxy = Proyectil(item["tipo"], item["x"], item["y"], 0, 0, owner=item.get("owner"))
                proxy.proj_id = pid
                proxy.danados = set()
                proxy.ya_hizo_dano = True  # el cliente nunca aplica daño, solo dibuja
                self.proyectiles.append(proxy)
                sound_manager.disparo(item["tipo"])  # proyectil recién aparecido: sonido de disparo
            explotado_antes = proxy.explotado
            proxy.x = item["x"]
            proxy.y = item["y"]
            proxy.vel_x = item.get("vel_x", proxy.vel_x)
            proxy.vel_y = item.get("vel_y", proxy.vel_y)
            proxy.estado = item.get("estado")
            proxy.explotado = item.get("explotado", False)
            if proxy.explotado and not explotado_antes:
                sound_manager.explosion(item["tipo"])

        self.proyectiles = [p for p in self.proyectiles if getattr(p, "proj_id", None) in ids_recibidos]

    # ------------------------------------------------------------------
    # Loop principal
    # ------------------------------------------------------------------
    def run(self):
        while True:
            if not self.event_handler.handle_events():
                self._cerrar_red()
                return

            self._procesar_mensajes_pendientes()

            if self.game_over:
                fin_text = self.font.render("¡Tiempo terminado! Fin de la partida", True, (255, 0, 0))
                rect = fin_text.get_rect(center=(ANCHO // 2, ALTO // 2))
                self.pantalla.blit(fin_text, rect)
                pygame.display.flip()
                pygame.time.delay(5000)
                self._cerrar_red()
                return

            if self.host and not self.partida_iniciada:
                keys = pygame.key.get_pressed()
                if keys[pygame.K_i]:
                    self.partida_iniciada = True
                    self.ultimo_tick = time.time()
                    self.enviar({"tipo": "iniciar_partida"})
                    print("[HOST] Partida iniciada!")

            if (self.host and self.partida_iniciada and not self.turnos_iniciados
                    and self.robots_remotos and len(self.robots_remotos) >= 1):
                jugadores = [self.nombre_jugador] + list(self.robots_remotos.keys())
                self.turn_manager.iniciar(jugadores)
                self.enviar({"tipo": "turnos_init", "jugadores": jugadores})
                self.turnos_iniciados = True
                print(f"[HOST] Turnos iniciados con jugadores: {jugadores}")

            if self.host and self.turnos_iniciados:
                self.turn_manager.actualizar()
                self.turn_manager.enviar_sync()

            if self.turn_manager.jugador_actual() == self.nombre_jugador and not self.turn_manager.en_cooldown:
                keys = pygame.key.get_pressed()
                self.robot.update(keys)
                if keys[pygame.K_DELETE]:
                    self.robot.take_damage(50)
                    if self.host:
                        self.turn_manager.forzar_fin_turno()
                        self.enviar({"tipo": "turno_fin", "jugador": self.nombre_jugador})
            else:
                self.robot.update([])
                self.robot.vel_x = 0

            # --- Colisiones del robot local contra el mapa ---
            check_collisions(self.robot, self.tiles)
            check_collisions_laterales_esquinas(self.robot, self.tiles_laterales)

            # --- Enviar estado local ---
            self.enviar_estado()

            # --- Robots remotos actualizados ANTES de usarlos para colisión ---
            self.robots_estaticos = list(self.robots_remotos.values())

            # --- Armas: física real solo en host; en cliente no hace nada ---
            self.weapon_manager.update()
            self._sync_proyectiles()

            # --- Suavizar movimiento de robots remotos ---
            self._interpolar_remotos()

            # --- Cronómetro ---
            if self.host and self.partida_iniciada and not self.game_over:
                ahora = time.time()
                delta = ahora - self.ultimo_tick
                if delta >= 1:
                    self.tiempo_restante -= int(delta)
                    self.ultimo_tick = ahora
                    if self.tiempo_restante <= 0:
                        self.tiempo_restante = 0
                        self.game_over = True
                    self.enviar({"tipo": "timer", "restante": self.tiempo_restante})

            # --- Render ---
            self.draw_scene()
            self.robot.draw(self.pantalla)
            for r in self.robots_remotos.values():
                r.draw(self.pantalla)
            self.weapon_manager.draw(self.pantalla)
            if self.robot.arma_equipada not in [None, "nada"]:
                mouse_pos = pygame.mouse.get_pos()
                self.aim.origen = self.robot.get_centro()
                self.aim.update(mouse_pos)
                self.aim.draw(self.pantalla)
            self.hud_manager.draw(self.pantalla)
            self.chat.draw(self.pantalla)
            self.timer_hud.draw(self.pantalla)
            self.hud_turnos.draw(self.pantalla)
            self.robot.draw_death_message(self.pantalla, self.fuente_muerte)
            for r in self.robots_remotos.values():
                r.draw_death_message(self.pantalla, self.fuente_muerte)

            pygame.display.flip()
            self.reloj.tick(60)

    def _interpolar_remotos(self, factor=0.35):
        for r in self.robots_remotos.values():
            tx = getattr(r, "target_x", r.x)
            ty = getattr(r, "target_y", r.y)
            r.x += (tx - r.x) * factor
            r.y += (ty - r.y) * factor

    def _cerrar_red(self):
        self._listening = False
        try:
            if self._server_socket:
                self._server_socket.close()
        except Exception:
            pass
        try:
            if self._client_socket:
                self._client_socket.close()
        except Exception:
            pass
        with self._client_sockets_lock:
            for s in self._client_sockets:
                try:
                    s.close()
                except Exception:
                    pass
