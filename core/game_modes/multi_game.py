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
from utils.weapon_loader import cargar_armas, config_arma
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

from utils.colors import ColorManager
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

    def __init__(self, nombre_jugador, personaje, host=True, server_ip="127.0.0.1", port=5000, duracion_min=3, modo_partida="puntos", mapa_id="parque"):
        super().__init__(nombre_jugador=nombre_jugador, personaje=personaje, mapa_id=mapa_id)
        self.modo_partida = modo_partida  # solo "puntos" implementado por ahora
        ColorManager.reset()

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
        self.aim_remoto = AimIndicator((0, 0))  # instancia aparte, solo para dibujar armas de robots remotos — nunca se usa para disparar
        self.weapon_manager = WeaponManager(self)
        self.puntajes[self.nombre_jugador] = 0
        self.hud_puntajes = HUDPuntajesMultiplayer(self)
        self.hud_armas = HUDArmas(list(cargar_armas().keys()))
        self.hud_manager = HUDManager(self)
        self.chat = Chat(nombre_jugador, game=self, robot_local=self.robot)
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
            # Aviso inmediato del mapa en uso — así el cliente lo recarga
            # antes de que empiece a chocar contra tiles que no tiene.
            try:
                _send_framed(conn, {"tipo": "mapa_init", "mapa_id": self.mapa_id})
            except Exception:
                pass
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
        mouse_pos = pygame.mouse.get_pos()
        origen = self.robot.get_centro()
        municion_actual = self.weapon_manager.municion_actual(self.robot.arma_equipada)
        sin_municion = municion_actual is not None and municion_actual <= 0
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
            "arma": self.robot.arma_equipada,
            "sin_municion": sin_municion,
            "aim_dx": mouse_pos[0] - origen[0],
            "aim_dy": mouse_pos[1] - origen[1],
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
                "facing_right": getattr(p, "_facing_right", True),
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
                r.arma_equipada = msg.get("arma")
                r.sin_municion = msg.get("sin_municion", False)   # <-- nuevo
                r.aim_dx = msg.get("aim_dx", 0)
                r.aim_dy = msg.get("aim_dy", 0)
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
                r.arma_equipada = msg.get("arma", getattr(r, "arma_equipada", None))
                r.sin_municion = msg.get("sin_municion", getattr(r, "sin_municion", False))  # <-- nuevo
                r.aim_dx = msg.get("aim_dx", getattr(r, "aim_dx", 0))
                r.aim_dy = msg.get("aim_dy", getattr(r, "aim_dy", 0))
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

        elif tipo == "empuje":
            if msg.get("jugador") == self.nombre_jugador:
                self.robot.aplicar_empuje(msg.get("vel_x", 0), msg.get("vel_y", 0))

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
                mensaje = msg["mensaje"]
                self.chat.agregar_mensaje(mensaje)
                # El mensaje llega formateado como "Jugador: texto" (así lo
                # arma Chat.handle_event) — para la burbuja solo queremos el
                # texto, sin el prefijo del nombre.
                texto_burbuja = mensaje.split(": ", 1)[1] if ": " in mensaje else mensaje
                robot_remoto = self.robots_remotos.get(jugador)
                if robot_remoto is not None:
                    robot_remoto.mostrar_mensaje(texto_burbuja)

        elif tipo == "timer":
            self.tiempo_restante = msg["restante"]
            if self.tiempo_restante <= 0:
                self.game_over = True

        elif tipo == "turnos_init":
            self.turn_manager.iniciar(msg["jugadores"])

        elif tipo == "mapa_init":
            if not self.host:
                nuevo_mapa = msg.get("mapa_id", "parque")
                if nuevo_mapa != self.mapa_id:
                    self.cargar_mapa(nuevo_mapa)

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
                proxy = Proyectil(item["tipo"], item["x"], item["y"], 0, 0, owner=item.get("owner"),
                                facing_right=item.get("facing_right", True))
                proxy.proj_id = pid
                proxy.danados = set()
                proxy.ya_hizo_dano = True
                self.proyectiles.append(proxy)
                sound_manager.disparo(item["tipo"])
            explotado_antes = proxy.explotado
            proxy.x = item["x"]
            proxy.y = item["y"]
            proxy.vel_x = item.get("vel_x", proxy.vel_x)
            proxy.vel_y = item.get("vel_y", proxy.vel_y)
            proxy.estado = item.get("estado")
            proxy.explotado = item.get("explotado", False)
            proxy._facing_right = item.get("facing_right", proxy._facing_right)
            if proxy.explotado and not explotado_antes:
                sound_manager.explosion(item["tipo"])

        self.proyectiles = [p for p in self.proyectiles if getattr(p, "proj_id", None) in ids_recibidos]

    # ------------------------------------------------------------------
    # Loop principal
    # ------------------------------------------------------------------
    def run(self):
        while True:
            if not self.robot.is_dead and self.robot.arma_equipada not in [None, "nada"]:
                mouse_pos = pygame.mouse.get_pos()
                self.robot.facing_right = mouse_pos[0] >= self.robot.get_centro()[0]

            if not self.event_handler.handle_events():
                self._cerrar_red()
                return

            self._procesar_mensajes_pendientes()

            if self.game_over:
                etiqueta = {"puntos": "Puntaje", "muertes": "Muertes"}.get(self.modo_partida, "Puntaje")
                self.mostrar_pantalla_final(etiqueta=etiqueta)
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
                if pygame.time.get_ticks() >= self.robot.aturdido_hasta:
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
                config = config_arma(self.robot.arma_equipada)
                estilo_mira = config.get("estilo_mira", "apuntar") if config else "apuntar"
                self.aim.draw(self.pantalla, estilo=estilo_mira)
                municion = self.weapon_manager.municion_actual(self.robot.arma_equipada)
                sin_municion = municion is not None and municion <= 0
                if config and not sin_municion:
                    oculta_al_disparar = config.get("oculta_arma_al_disparar")
                    if oculta_al_disparar is None:
                        oculta_al_disparar = (config.get("comportamiento") == "cuerpo_a_cuerpo")
                    tiene_proyectil_activo = oculta_al_disparar and any(
                        getattr(p, "owner", None) == self.robot.nombre_jugador
                        and getattr(p, "tipo", None) == self.robot.arma_equipada
                        and getattr(p, "estado", None) != "done"
                        for p in self.proyectiles
                    )
                    if not tiene_proyectil_activo:
                        self.aim.draw_arma_sostenida(
                            self.pantalla, config.get("_weapon_img"), mouse_pos,
                            posicion_x=config.get("posicion_ancho_arma_sostenida", 0),
                            posicion_y=config.get("posicion_alto_arma_sostenida", 0),
                        )

            # --- Arma sostenida de robots remotos, sincronizada por red ---
            for jugador, r in self.robots_remotos.items():
                arma_remota = getattr(r, "arma_equipada", None)
                if arma_remota in (None, "nada"):
                    continue
                if getattr(r, "sin_municion", False):   # <-- nuevo
                    continue
                config_r = config_arma(arma_remota)
                if not config_r:
                    continue
                oculta_al_disparar_r = config_r.get("oculta_arma_al_disparar")
                if oculta_al_disparar_r is None:
                    oculta_al_disparar_r = (config_r.get("comportamiento") == "cuerpo_a_cuerpo")
                tiene_proyectil_activo = oculta_al_disparar_r and any(
                    getattr(p, "owner", None) == jugador
                    and getattr(p, "tipo", None) == arma_remota
                    and getattr(p, "estado", None) != "done"
                    for p in self.proyectiles
                )
                if tiene_proyectil_activo:
                    continue
                origen_r = r.get_centro()
                mouse_virtual = (
                    origen_r[0] + getattr(r, "aim_dx", 0),
                    origen_r[1] + getattr(r, "aim_dy", 0),
                )
                self.aim_remoto.origen = origen_r
                self.aim_remoto.draw_arma_sostenida(
                    self.pantalla, config_r.get("_weapon_img"), mouse_virtual,
                    posicion_x=config_r.get("posicion_ancho_arma_sostenida", 0),
                    posicion_y=config_r.get("posicion_alto_arma_sostenida", 0),
                )
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

    def _calcular_podio(self):
        """Agrupa jugadores por rango, respetando empates (mismo
        puntaje/métrica = mismo podio). Genérico: no le importa si el
        número es puntaje, muertes, o cualquier otra cosa que llenes en
        self.puntajes."""
        orden = sorted(self.puntajes.items(), key=lambda kv: kv[1], reverse=True)
        podio = []  # [(rango, [(jugador, valor), ...]), ...]
        for jugador, valor in orden:
            if podio and podio[-1][1][0][1] == valor:
                podio[-1][1].append((jugador, valor))
            else:
                rango = len(podio) + 1
                podio.append((rango, [(jugador, valor)]))
        return podio

    def _robot_de(self, jugador):
        if jugador == self.nombre_jugador:
            return self.robot
        return self.robots_remotos.get(jugador)

    def mostrar_pantalla_final(self, etiqueta="Puntaje"):
        podio = self._calcular_podio()
        fuente_rango = pygame.font.SysFont("Arial", 28, bold=True)
        fuente_nombre = pygame.font.SysFont("Arial", 18, bold=True)
        fuente_valor = pygame.font.SysFont("Arial", 16)
        fuente_titulo = pygame.font.SysFont("Arial", 36, bold=True)

        alturas_podio = {1: 160, 2: 110, 3: 70}
        altura_extra = 40  # decrece un poco más por cada rango >3

        base_y = ALTO - 60
        ancho_bloque = 110
        espacio = 20

        posiciones = []  # (cx, y_superior, alto_bloque, jugador, valor, rango)
        x_actual = 60
        for rango, jugadores in podio:
            alto_bloque = alturas_podio.get(rango, max(30, alturas_podio[3] - (rango - 3) * altura_extra))
            n = len(jugadores)
            for i, (jugador, valor) in enumerate(jugadores):
                cx = x_actual + i * (ancho_bloque + espacio) + ancho_bloque // 2
                posiciones.append((cx, base_y - alto_bloque, alto_bloque, jugador, valor, rango))
            ancho_grupo = ancho_bloque * n + espacio * (n - 1)
            x_actual += ancho_grupo + espacio * 2

        esperando = True
        reloj_local = pygame.time.Clock()
        while esperando:
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT or evento.type == pygame.KEYDOWN:
                    esperando = False

            self.pantalla.fill((30, 30, 40))
            titulo = fuente_titulo.render("¡Fin de la partida!", True, (255, 215, 0))
            self.pantalla.blit(titulo, titulo.get_rect(center=(ANCHO // 2, 50)))

            for cx, y_superior, alto_bloque, jugador, valor, rango in posiciones:
                color_bloque = (
                    (200, 170, 60) if rango == 1 else
                    (180, 180, 190) if rango == 2 else
                    (160, 110, 70) if rango == 3 else
                    (90, 90, 100)
                )
                pygame.draw.rect(self.pantalla, color_bloque, (cx - ancho_bloque // 2, y_superior, ancho_bloque, alto_bloque))

                robot = self._robot_de(jugador)
                sprite_top = y_superior
                if robot is not None:
                    idle_img = robot.animations["idle"][0]
                    if not robot.facing_right:
                        idle_img = pygame.transform.flip(idle_img, True, False)
                    img_rect = idle_img.get_rect(midbottom=(cx, y_superior))
                    self.pantalla.blit(idle_img, img_rect)
                    sprite_top = img_rect.top

                nombre_render = fuente_nombre.render(jugador, True, ColorManager.get_color(jugador))
                self.pantalla.blit(nombre_render, nombre_render.get_rect(center=(cx, sprite_top - 15)))

                # Rango / etiqueta / valor, siempre a la misma altura base
                # (relativa al piso, no al alto variable del bloque) para
                # que quede alineado sin importar el podio de cada uno.
                texto_rango = fuente_rango.render(f"{rango}°", True, (255, 255, 255))
                self.pantalla.blit(texto_rango, texto_rango.get_rect(center=(cx, base_y + 20)))

                etiqueta_render = fuente_valor.render(f"{etiqueta}:", True, (255, 255, 255))
                self.pantalla.blit(etiqueta_render, etiqueta_render.get_rect(center=(cx, base_y + 42)))

                valor_render = fuente_valor.render(str(valor), True, (255, 255, 255))
                self.pantalla.blit(valor_render, valor_render.get_rect(center=(cx, base_y + 64)))

            ayuda = fuente_valor.render("Presiona cualquier tecla para salir", True, (200, 200, 200))
            self.pantalla.blit(ayuda, ayuda.get_rect(center=(ANCHO // 2, ALTO - 20)))

            pygame.display.flip()
            reloj_local.tick(30)

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
