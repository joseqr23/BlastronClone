# core/game_modes/multi_game.py
import pygame
import socket
import threading
import pickle
import time

from settings import ANCHO, ALTO, ALTURA_SUELO
from entities.players.robot import Robot
from core.game_modes.base_game import BaseGame
from systems.collision import check_collisions, check_collisions_laterales_esquinas
from systems.aim_indicator import AimIndicator
from systems.weapon_manager import WeaponManager
from systems.hud_manager import HUDManager
from ui.hud import HUDPuntajes, HUDArmas
from systems.event_handler import EventHandler
from ui.chat import Chat


class MultiplayerGame(BaseGame):
    """MultiplayerGame con armas, HUD, mira y sincronización de robots remotos."""

    def __init__(self, nombre_jugador, personaje, host=True, server_ip="127.0.0.1", port=5000):
        super().__init__(nombre_jugador=nombre_jugador, personaje=personaje)

        # --- Robot local ---
        self.robot = Robot(
            x=ANCHO // 2 - 30,
            y=ALTO - 90 - ALTURA_SUELO,
            nombre_jugador=nombre_jugador,
            nombre_robot=personaje
        )

        # --- Robots remotos ---
        self.robots_remotos = {}
        self.robots_estaticos = []  # necesario para WeaponManager y HUD

        # --- Proyectiles ---
        self.granadas = []
        self.misiles = []

        # --- HUD, armas y chat ---
        self.aim = AimIndicator(self.robot.get_centro())
        self.weapon_manager = WeaponManager(self)
        self.puntajes[self.robot] = 0
        self.hud_puntajes = HUDPuntajes(self)
        self.hud_armas = HUDArmas(['granada', 'misil'])  # corregido
        self.hud_manager = HUDManager(self)
        self.chat = Chat(nombre_jugador)
        self.event_handler = EventHandler(self)
        self.mouse_click_sostenido = False
        self.font = pygame.font.SysFont("Arial", 16)

        # --- Networking ---
        self.host = host
        self.server_ip = server_ip
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(False)

        if self.host:
            self.sock.bind(("0.0.0.0", self.port))
            print(f"[Multiplayer] Servidor iniciado en 0.0.0.0:{self.port}")
            self.known_clients = set()

            # Detectar IPs locales para evitar reenviarnos a nosotros mismos
            self.server_sockname = self.sock.getsockname()  # e.g. ('0.0.0.0', 5000)
            self.local_ips = {"127.0.0.1", "::1"}
            try:
                import socket as _s
                resolved = _s.gethostbyname(_s.gethostname())
                self.local_ips.add(resolved)
            except Exception:
                pass
        else:
            self.sock.bind(("0.0.0.0", 0))
            print(f"[Multiplayer] Cliente listo (enviando a {self.server_ip}:{self.port})")

        # Hilo de escucha
        self._listening = True
        threading.Thread(target=self.listen, daemon=True).start()

    def listen(self):
        """Recibe mensajes de red y actualiza estado."""
        while self._listening:
            try:
                data, addr = self.sock.recvfrom(8192)
                msg = pickle.loads(data)

                if self.host:
                    # Registrar cliente nuevo SOLO si no es nuestra propia IP/puerto
                    is_self_addr = (addr[0] in getattr(self, "local_ips", {"127.0.0.1", "::1"}) and addr[1] == self.port)
                    if addr not in self.known_clients and not is_self_addr:
                        self.known_clients.add(addr)
                        print(f"[Host] Cliente conectado: {addr}")

                    # Reenviar a todos menos al emisor y excepto a direcciones locales del host
                    for client in list(self.known_clients):
                        client_is_self = (client[0] in getattr(self, "local_ips", {"127.0.0.1", "::1"}) and client[1] == self.port)
                        if client != addr and not client_is_self:
                            try:
                                self.sock.sendto(data, client)
                            except Exception:
                                # si falla con ese cliente, lo eliminamos
                                try:
                                    self.known_clients.remove(client)
                                except KeyError:
                                    pass

                tipo = msg.get("tipo")
                jugador = msg.get("jugador")

                if tipo == "update" and jugador != self.nombre_jugador:
                    if jugador not in self.robots_remotos:
                        self.robots_remotos[jugador] = Robot(
                            x=msg["x"], y=msg["y"],
                            nombre_jugador=jugador,
                            nombre_robot=msg.get("personaje", "default"),
                            es_remoto=True
                        )
                    else:
                        r = self.robots_remotos[jugador]
                        r.x = msg["x"]
                        r.y = msg["y"]
                        r.frame_index = msg.get("frame", 0)
                        r.current_animation = msg.get("estado", "idle")
                        r.facing_right = (msg.get("direccion", 1) == 1)

                    # 🔥 sincronizar vida si viene en el mensaje
                    if "health" in msg:
                        self.robots_remotos[jugador].health = msg["health"]


                elif tipo == "disparo":
                    self.weapon_manager.recibir_disparo_remoto(msg)

                elif tipo == "damage":
                    # debug: imprimir origen del paquete UDP + contenido
                    print(f"[DEBUG listen] paquete DAMAGE recibido en {self.nombre_jugador} desde {addr} -> {msg}")
                    jugador = msg["jugador"]
                    cantidad = msg["cantidad"]
                    quien_disparo = msg.get("quien", None)

                    if jugador == self.nombre_jugador:
                        # Solo aplico al local
                        if quien_disparo != self.nombre_jugador:
                            self.robot.take_damage(cantidad)

                    elif jugador in self.robots_remotos and jugador != self.nombre_jugador:
                        # Solo remotos que no son yo
                        self.robots_remotos[jugador].health -= cantidad
                        if self.robots_remotos[jugador].health < 0:
                            self.robots_remotos[jugador].health = 0


            except BlockingIOError:
                time.sleep(0.01)
            except Exception:
                time.sleep(0.05)

    def enviar_estado(self):
        """Envía posición, animación y vida del jugador local."""
        data = {
            "tipo": "update",
            "jugador": self.nombre_jugador,
            "personaje": self.personaje,
            "x": float(self.robot.x),
            "y": float(self.robot.y),
            "frame": self.robot.frame_index,
            "estado": self.robot.current_animation,
            "direccion": 1 if self.robot.facing_right else -1,
            "health": self.robot.health,   # 🔥 nueva clave
        }
        try:
            self.sock.sendto(pickle.dumps(data), (self.server_ip, self.port))
        except Exception:
            pass

    def enviar_disparo(self, proyectil):
        """Envía disparo del jugador local al host."""
        data = {
            "tipo": "disparo",
            "jugador": self.nombre_jugador,
            "owner": self.nombre_jugador,     # dueño del proyectil (explícito)
            "arma": proyectil.tipo,
            "x": proyectil.x,
            "y": proyectil.y,
            "dir_x": proyectil.dir_x,
            "dir_y": proyectil.dir_y,
        }
        try:
            self.sock.sendto(pickle.dumps(data), (self.server_ip, self.port))
        except Exception:
            pass

    def run(self):
        """Loop principal: input, robots, armas, HUD y render."""
        while True:
            if not self.event_handler.handle_events():
                self._listening = False
                self.sock.close()
                return

            # --- Input y actualización local ---
            keys = pygame.key.get_pressed()
            self.robot.update(keys)
            if keys[pygame.K_DELETE]:
                self.robot.take_damage(50)

            # --- Colisiones ---
            check_collisions(self.robot, self.tiles)
            check_collisions_laterales_esquinas(self.robot, self.tiles_laterales)

            # --- Enviar estado local ---
            self.enviar_estado()

            # --- Actualizar armas ---
            self.weapon_manager.update()

            # --- Render ---
            self.draw_scene()

            # Dibujar robots
            self.robot.draw(self.pantalla)
            for r in self.robots_remotos.values():
                r.draw(self.pantalla)

            # Dibujar proyectiles
            self.weapon_manager.draw(self.pantalla)

            # Indicador de mira
            if self.robot.arma_equipada not in [None, "nada"]:
                mouse_pos = pygame.mouse.get_pos()
                self.aim.origen = self.robot.get_centro()
                self.aim.update(mouse_pos)
                self.aim.draw(self.pantalla)

            # Actualizar robots estáticos para WeaponManager
            self.robots_estaticos = list(self.robots_remotos.values())

            # HUD y chat
            self.hud_manager.draw(self.pantalla)
            self.chat.draw(self.pantalla)

            # Mensajes de muerte
            self.robot.draw_death_message(self.pantalla, self.fuente_muerte)
            for r in self.robots_remotos.values():
                r.draw_death_message(self.pantalla, self.fuente_muerte)

            pygame.display.flip()
            self.reloj.tick(60)


    def enviar_dano(self, jugador_objetivo, cantidad):
        data = {
            "tipo": "damage",
            "jugador": jugador_objetivo,
            "cantidad": cantidad,
            "quien": self.nombre_jugador
        }
        try:
            print(f"[DEBUG] enviando paquete DAMAGE desde {self.nombre_jugador} para {jugador_objetivo} amt={cantidad}")
            self.sock.sendto(pickle.dumps(data), (self.server_ip, self.port))
        except Exception:
            pass