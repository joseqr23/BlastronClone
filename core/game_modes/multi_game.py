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
from ui.hud import HUDPuntajesMultiplayer, HUDArmas, HUDTimer, HUDTurnos
from systems.event_handler import EventHandler
from ui.chat import Chat
from systems.turn_manager import TurnManager


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
        self.puntajes[self.nombre_jugador] = 0
        self.hud_puntajes = HUDPuntajesMultiplayer(self)
        self.hud_armas = HUDArmas(['granada', 'misil'])  # corregido
        self.hud_manager = HUDManager(self)
        self.chat = Chat(nombre_jugador, game=self)
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

        # Tiempo de juego
        self.tiempo_total = 3 * 60  # 3 minutos en segundos
        self.tiempo_restante = self.tiempo_total
        self.ultimo_tick = time.time()
        self.game_over = False
        self.timer_hud = HUDTimer(self, duracion=180, posicion=(ANCHO // 2, 30))

        # Turnos de jugador
        self.turn_manager = TurnManager(self)
        self.hud_turnos = HUDTurnos(self.turn_manager, posicion=(ANCHO // 2 - 80, 60))
        self.turnos_iniciados = False


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

                # Estado de jugadores
                if tipo == "update" and jugador != self.nombre_jugador:
                    if jugador not in self.robots_remotos:
                        self.robots_remotos[jugador] = Robot(
                            x=msg["x"], y=msg["y"],
                            nombre_jugador=jugador,
                            nombre_robot=msg.get("personaje", "default"),
                            es_remoto=True
                        )
                        # 🔥 Inicializar puntaje del nuevo jugador
                        if jugador not in self.puntajes:
                            self.puntajes[jugador] = 0

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

                elif tipo == "score":
                    atacante = msg["atacante"]
                    puntos = msg["puntos"]
                    victima = msg["victima"]
                    victima_dead = msg.get("victima_dead", False)

                    # Actualizar puntaje
                    self.puntajes[atacante] = self.puntajes.get(atacante, 0) + puntos

                    # Log o evento visible
                    print(f"[SCORE] {atacante} ganó {puntos} puntos por dañar a {victima}")

                    if victima_dead:
                        self.chat.add_message(f"💥 {victima} fue detonado por {atacante}!")

                    # --- CORRECCIÓN IMPORTANTE ---
                    # El host debe asegurarse de que también llegue al emisor (addr).
                    # Nota: al inicio de listen ya reenvías a todos los clientes excepto addr;
                    # por eso aquí basta con enviar sólo a addr para completar la distribución
                    # sin duplicar mensajes a los otros clientes.
                    if self.host:
                        try:
                            # enviar únicamente al emisor para que también reciba el evento
                            self.sock.sendto(pickle.dumps(msg), addr)
                            print(f"[HOST] reenviado SCORE a emisor {addr} para que vea su puntaje")
                        except Exception as e:
                            print(f"[HOST] fallo reenvío SCORE a {addr}: {e}")

                elif tipo == "chat":
                    mensaje = msg["mensaje"]
                    jugador = msg.get("jugador")

                    # Solo mostrar si no es un mensaje propio
                    if jugador != self.nombre_jugador:
                        self.chat.agregar_mensaje(mensaje)

                elif tipo == "timer":
                    self.tiempo_restante = msg["restante"]
                    if self.tiempo_restante <= 0:
                        self.game_over = True


                 # --- NUEVOS MENSAJES DE TURNOS ---
                elif tipo == "turnos_init":
                    self.turn_manager.iniciar(msg["jugadores"])

                elif tipo == "turno_sync":
                    jugador = msg["jugador"]
                    if jugador in self.turn_manager.jugadores:
                        self.turn_manager.turno_actual = self.turn_manager.jugadores.index(jugador)
                    self.turn_manager.en_cooldown = msg["cooldown"]

                    if self.turn_manager.en_cooldown:
                        self.turn_manager.cooldown_restante_sync = msg["tiempo"]
                        self.turn_manager.turno_inicio = None
                    else:
                        self.turn_manager.turno_restante_sync = msg["tiempo"]
                        self.turn_manager.cooldown_inicio = None


                elif tipo == "turno_fin":
                    jugador = msg.get("jugador")
                    print(f"[NET] Fin de turno de {jugador}")

                    # 🔥 Actualizar turn manager
                    if self.host:
                        # si soy host, fuerzo el fin del turno en mi lógica
                        self.turn_manager.forzar_fin_turno()
                    else:
                        # si soy cliente, simplemente pongo cooldown (el host ya mandó el sync)
                        if jugador == self.turn_manager.jugador_actual():
                            self.turn_manager.iniciar_cooldown()

                    # 🔥 Frenar totalmente al jugador que terminó su turno
                    target = None
                    # 🔥 Frenar al jugador que terminó su turno
                    if jugador == self.nombre_jugador:
                        target = self.robot
                    elif jugador in self.robots_remotos:
                        target = self.robots_remotos[jugador]

                    if target:
                        target.vel_x = 0
                        target.vel_y = 0
                        target.current_animation = "idle"

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

        # --- Forzar fin de turno al disparar ---
        if self.turn_manager.jugador_actual() == self.nombre_jugador:
            self.turn_manager.forzar_fin_turno()
            data = {"tipo": "turno_fin", "jugador": self.nombre_jugador}
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

            # --- Si el tiempo ya terminó ---
            if self.game_over:
                fin_text = self.font.render("¡Tiempo terminado! Fin de la partida", True, (255, 0, 0))
                rect = fin_text.get_rect(center=(ANCHO // 2, ALTO // 2))
                self.pantalla.blit(fin_text, rect)
                pygame.display.flip()
                pygame.time.delay(5000)
                return


            # --- Inicializar turnos en host ---
            if self.host and not self.turnos_iniciados and self.robots_remotos and len(self.robots_remotos) >= 1: # and len(self.robots_remotos) >= 1: PARA ASEGURARSE DE QUE ARRANQUE SOLO SI HAY MAS DE DOS JUGADORES
                jugadores = [self.nombre_jugador] + list(self.robots_remotos.keys())
                self.turn_manager.iniciar(jugadores)
                data = {"tipo": "turnos_init", "jugadores": jugadores}
                try:
                    self.sock.sendto(pickle.dumps(data), (self.server_ip, self.port))
                except Exception:
                    pass
                self.turnos_iniciados = True
                print(f"[HOST] Turnos iniciados con jugadores: {jugadores}")

            # --- Actualizar turnos ---
            if self.host and self.turnos_iniciados:
                self.turn_manager.actualizar()
                data = {
                    "tipo": "turno_sync",
                    "jugador": self.turn_manager.jugador_actual(),
                    "tiempo": self.turn_manager.tiempo_restante(),
                    "cooldown": self.turn_manager.en_cooldown,
                }
                try:
                    self.sock.sendto(pickle.dumps(data), (self.server_ip, self.port))
                except Exception:
                    pass

            # # --- Input y actualización local ---
            # keys = pygame.key.get_pressed()
            # self.robot.update(keys)
            # if keys[pygame.K_DELETE]:
            #     self.robot.take_damage(50)

            # --- Input y actualización local (solo si es tu turno y no cooldown) ---
            if self.turn_manager.jugador_actual() == self.nombre_jugador and not self.turn_manager.en_cooldown:
                keys = pygame.key.get_pressed()
                self.robot.update(keys)

                # ⚡ Ejemplo: tecla DELETE simula un disparo
                if keys[pygame.K_DELETE]:
                    self.robot.take_damage(50)

                    # 🔥 Fin del turno si soy el host (controla la lógica)
                    if self.host:
                        self.turn_manager.forzar_fin_turno()
                        data = {"tipo": "turno_fin"}
                        try:
                            self.sock.sendto(pickle.dumps(data), (self.server_ip, self.port))
                        except Exception:
                            pass
            else:
                # 🔥 Aplicar solo gravedad/colisiones sin movimiento
                self.robot.update([])  # o pasa un arreglo vacío en lugar de None
                self.robot.vel_x = 0  # 🔒 evita que quede con velocidad horizontal

            # --- Colisiones ---
            check_collisions(self.robot, self.tiles)
            check_collisions_laterales_esquinas(self.robot, self.tiles_laterales)

            # --- Enviar estado local ---
            self.enviar_estado()

            # --- Actualizar armas ---
            self.weapon_manager.update()

            # --- Si soy host, actualizar cronómetro y enviarlo ---
            if self.host and not self.game_over:
                ahora = time.time()
                delta = ahora - self.ultimo_tick
                if delta >= 1:  # cada segundo
                    self.tiempo_restante -= int(delta)
                    self.ultimo_tick = ahora

                    if self.tiempo_restante <= 0:
                        self.tiempo_restante = 0
                        self.game_over = True

                    # enviar a clientes
                    data = {"tipo": "timer", "restante": self.tiempo_restante}
                    try:
                        self.sock.sendto(pickle.dumps(data), (self.server_ip, self.port))
                    except Exception:
                        pass

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

            # HUD de cronometro
            self.timer_hud.draw(self.pantalla)

            # HUD de turnos
            self.hud_turnos.draw(self.pantalla)

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

    def enviar_chat(self, mensaje):
        data = {
            "tipo": "chat",
            "jugador": self.nombre_jugador,
            "mensaje": mensaje
        }
        try:
            self.sock.sendto(pickle.dumps(data), (self.server_ip, self.port))
        except Exception:
            pass
