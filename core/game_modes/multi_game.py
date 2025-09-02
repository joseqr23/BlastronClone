# core/game_modes/multi_game.py
import pygame
import socket
import threading
import pickle
import time

from settings import ANCHO, ALTO, ALTURA_SUELO
from entities.players.robot import Robot
from core.game_modes.base_game import BaseGame

class MultiplayerGame(BaseGame):
    """
    MultiplayerGame simplificado:
    - Host: actúa como servidor, recibe updates de clientes y los reenvía.
    - Cliente: envía su posición y recibe la de los demás.
    - Solo sincroniza movimiento (sin daño, armas, puntajes).
    """

    def __init__(self, nombre_jugador, personaje, host=True, server_ip="127.0.0.1", port=5000):
        super().__init__(nombre_jugador=nombre_jugador, personaje=personaje)

        # Robot local
        self.robot = Robot(
            x=ANCHO // 2 - 30,
            y=ALTO - 90 - ALTURA_SUELO,
            nombre_jugador=nombre_jugador,
            nombre_robot=personaje
        )

        # Robots remotos
        self.robots_remotos = {}

        # Networking
        self.host = host
        self.server_ip = server_ip
        self.port = port

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(False)

        if self.host:
            self.sock.bind(("0.0.0.0", self.port))
            print(f"[Multiplayer] Servidor iniciado en 0.0.0.0:{self.port}")
            self.known_clients = set()
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
                data, addr = self.sock.recvfrom(4096)
                msg = pickle.loads(data)

                if self.host:
                    # Registrar cliente nuevo
                    if addr not in self.known_clients:
                        self.known_clients.add(addr)
                        print(f"[Host] Cliente conectado: {addr}")

                    # Reenviar a todos menos al emisor
                    for client in self.known_clients:
                        if client != addr:
                            self.sock.sendto(data, client)

                if msg.get("tipo") == "update":
                    jugador = msg["jugador"]
                    if jugador != self.nombre_jugador:
                        if jugador not in self.robots_remotos:
                            self.robots_remotos[jugador] = Robot(
                                x=msg["x"], y=msg["y"],
                                nombre_jugador=jugador,
                                nombre_robot=msg.get("personaje", "default")
                            )
                        else:
                            self.robots_remotos[jugador].x = msg["x"]
                            self.robots_remotos[jugador].y = msg["y"]

            except BlockingIOError:
                time.sleep(0.01)
            except Exception:
                time.sleep(0.05)

    def enviar_estado(self):
        """Envia la posición local al servidor/host."""
        data = {
            "tipo": "update",
            "jugador": self.nombre_jugador,
            "personaje": self.personaje,
            "x": float(self.robot.x),
            "y": float(self.robot.y),
        }
        try:
            self.sock.sendto(pickle.dumps(data), (self.server_ip, self.port))
        except Exception:
            pass

    def run(self):
        """Loop principal: solo mueve y sincroniza robots."""
        while True:
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    self._listening = False
                    self.sock.close()
                    pygame.quit()
                    return

            # Input
            keys = pygame.key.get_pressed()
            self.robot.update(keys)

            # Enviar posición al servidor
            self.enviar_estado()

            # Dibujar escena
            self.draw_scene()
            self.robot.draw(self.pantalla)
            for r in self.robots_remotos.values():
                r.draw(self.pantalla)

            pygame.display.flip()
            self.reloj.tick(60)
