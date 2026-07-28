# core/game_modes/multi_game/game.py

import time
import pygame

from settings import ANCHO, ALTO, ALTURA_SUELO
from core.game_modes.base_game import BaseGame
from entities.players.robot import Robot
from systems.aim_indicator import AimIndicator
from systems.collision import check_collisions, check_collisions_laterales_esquinas, check_colision_bloque_solido, check_zonas_dañinas
from systems.event_handler import EventHandler
from systems.hud_manager import HUDManager
from systems.modos_partida import crear_modo
from systems.turn_manager import TurnManager
from systems.weapon_manager import WeaponManager
from ui.chat import Chat
from ui.hud import HUDArmas, HUDPuntajesMultiplayer, HUDTimer, HUDTurnos
from utils.colors import ColorManager
from utils.weapon_loader import cargar_armas

from .lobby import LobbyScreen
from .message_handler import MessageHandler
from .network import NetworkManager
from .renderer import MultiplayerRenderer
from .replication import Replication
from .results import ResultsScreen


class MultiplayerGame(BaseGame):
    """Coordina sala de espera, partida y servicios de red multijugador."""
    def __init__(self, nombre_jugador, personaje, host=True, server_ip="127.0.0.1", port=5000,
                 duracion_min=3, modo_partida="puntos", mapa_id="parque"):
        super().__init__(nombre_jugador=nombre_jugador, personaje=personaje, mapa_id=mapa_id)
        self.host, self.server_ip, self.port = host, server_ip, port
        self.modo_partida = modo_partida
        self.modo = crear_modo(modo_partida, self)
        self.vida_maxima = self.modo.vida_maxima
        ColorManager.reset()

        self.robot = Robot(x=ANCHO // 2 - 30, y=ALTO - 90 - ALTURA_SUELO,
                           nombre_jugador=nombre_jugador, nombre_robot=personaje,
                           vida_maxima=self.vida_maxima, puede_reaparecer=self.modo.permite_reaparecer)
        self.robots_remotos, self.robots_estaticos, self.last_sequences = {}, [], {}
        self.aim, self.aim_remoto = AimIndicator(self.robot.get_centro()), AimIndicator((0, 0))
        self.weapon_manager = WeaponManager(self)
        self.puntajes[self.nombre_jugador] = 0
        self.hud_puntajes = HUDPuntajesMultiplayer(self)
        self.hud_armas = HUDArmas(list(cargar_armas().keys()))
        self.hud_manager = HUDManager(self)
        self.chat = Chat(nombre_jugador, game=self, robot_local=self.robot)
        self.event_handler = EventHandler(self)
        self.volver_al_menu = False
        self.rect_volver_menu = self.rect_mute = None
        self.fuente_botones = pygame.font.SysFont("Arial", 10, bold=True)
        self.mouse_click_sostenido = False
        self.font = pygame.font.SysFont("Arial", 16)

        self.tiempo_total = duracion_min * 60
        self.tiempo_restante = self.tiempo_total
        self.ultimo_tick = self.now()
        self.game_over = False
        self.timer_hud = HUDTimer(self, duracion=self.tiempo_total, posicion=(ANCHO // 2, 30))
        self.turn_manager = TurnManager(self)
        self.hud_turnos = HUDTurnos(self.turn_manager, posicion=(ANCHO // 2, 72))
        self.turnos_iniciados = False
        self.partida_iniciada = False

        self.host_name = nombre_jugador if host else None
        self.local_ready = host
        self.lobby_players = ({nombre_jugador: {"nombre": nombre_jugador, "personaje": personaje, "listo": True}} if host else {})
        # main.py lo usa si el Host vuelve a la configuración desde el lobby.
        self.menu_restore = {
            "nombre": nombre_jugador, "personaje": personaje, "duracion_min": duracion_min,
            "modo_partida": modo_partida, "mapa": mapa_id,
        }
        self.network = NetworkManager(host, server_ip, port)
        self.replication = Replication(self)
        self.messages = MessageHandler(self)
        self.lobby = LobbyScreen(self)
        self.renderer = MultiplayerRenderer(self)
        self.results = ResultsScreen(self)
        self._seq_local = 0
        self.network.start()

    def now(self):
        return time.time()

    # ---------- API usada por EventHandler, WeaponManager y lobby ----------
    def enviar(self, message, excluir_socket=None):
        self.network.send(message, exclude_socket=excluir_socket)

    def enviar_chat(self, mensaje):
        self.enviar({"tipo": "chat", "jugador": self.nombre_jugador, "mensaje": mensaje})

    def enviar_evento_puntaje(self, atacante, puntos, victima):
        if not self.host: return
        self.puntajes[atacante] = self.puntajes.get(atacante, 0) + puntos
        if victima.health <= 0:
            self.chat.agregar_mensaje(f"{victima.nombre_jugador} fue detonado por {atacante}!")
        self.enviar({"tipo": "score", "atacante": atacante, "puntos": puntos,
                     "victima": victima.nombre_jugador, "victima_dead": victima.health <= 0})

    def enviar_evento_muerte(self, atacante, victima):
        if not self.host: return
        self.modo.registrar_muerte(victima, atacante)
        self.enviar({"tipo": "muerte", "atacante": atacante, "victima": victima.nombre_jugador})

    def _next_proy_id(self): return self.replication.next_projectile_id()
    def _sync_proyectiles(self): self.replication.sync_projectiles()
    def enviar_estado(self): self.replication.send_local_state()
    def _interpolar_remotos(self, factor=0.35): self.replication.interpolate_remotes(factor)
    def _procesar_mensajes_pendientes(self): self.messages.process_pending()
    def _cerrar_red(self): self.network.close()

    # ---------- Sala de espera ----------
    def _configuration_message(self, message_type):
        return {"tipo": message_type, "host_name": self.host_name, "jugadores": list(self.lobby_players.values()),
                "mapa_id": self.mapa_id, "modo_partida": self.modo_partida,
                "duracion_min": self.tiempo_total // 60}

    def broadcast_lobby_state(self):
        if self.host: self.enviar(self._configuration_message("lobby_state"))

    def apply_lobby_state(self, message):
        self.host_name = message.get("host_name", self.host_name)
        players = message.get("jugadores", [])
        self.lobby_players = {player["nombre"]: player for player in players if player.get("nombre")}
        self.local_ready = self.lobby_players.get(self.nombre_jugador, {}).get("listo", False)
        self.apply_match_configuration(message)

    def apply_match_configuration(self, message):
        mapa_id = message.get("mapa_id", self.mapa_id)
        if mapa_id != self.mapa_id: self.cargar_mapa(mapa_id)
        mode_id = message.get("modo_partida", self.modo_partida)
        if mode_id != self.modo_partida:
            self.modo_partida = mode_id
            self.modo = crear_modo(mode_id, self)
            self.vida_maxima = self.modo.vida_maxima
            for robot in [self.robot, *self.robots_remotos.values()]:
                robot.vida_maxima, robot.health = self.vida_maxima, self.vida_maxima
                robot.puede_reaparecer = self.modo.permite_reaparecer
        minutes = int(message.get("duracion_min", self.tiempo_total // 60))
        self.tiempo_total, self.tiempo_restante = minutes * 60, minutes * 60

    def set_local_ready(self, ready):
        if self.host: return
        self.local_ready = ready
        self.enviar({"tipo": "ready", "jugador": self.nombre_jugador, "listo": ready})

    def can_start_match(self):
        return len(self.lobby_players) >= 2 and all(player.get("listo", False) for name, player in self.lobby_players.items() if name != self.nombre_jugador)

    def start_match_if_possible(self):
        if not self.host or not self.can_start_match(): return False
        self.partida_iniciada = True
        self.ultimo_tick = self.now()
        self.enviar(self._configuration_message("match_start"))
        print("[HOST] Partida iniciada desde la sala de espera")
        return True

    # ---------- Ciclo público ----------
    def run(self):
        try:
            lobby_result = self.lobby.run()
            if lobby_result != "start": return lobby_result
            return self._run_match()
        finally:
            self._cerrar_red()

    def _run_match(self):
        while True:
            if not self.robot.is_dead and self.robot.arma_equipada not in (None, "nada"):
                self.robot.facing_right = pygame.mouse.get_pos()[0] >= self.robot.get_centro()[0]
            if not self.event_handler.handle_events(): return None
            self.messages.process_pending()
            if self.game_over:
                return "menu" if self.results.show(self.modo.etiqueta_podio()) else None
            self._update_turns_and_player()
            check_collisions(self.robot, self.tiles)
            check_collisions_laterales_esquinas(self.robot, self.tiles_laterales)
            check_colision_bloque_solido(self.robot, self.tiles_impenetrables)
            self.replication.send_local_state()
            self.robots_estaticos = list(self.robots_remotos.values())
            if self.host:
                for robot in [self.robot, *self.robots_estaticos]:
                    check_zonas_dañinas(robot, self.tiles_dañinas, self.dano_zonas,
                                        aplicar_dano_callback=self.weapon_manager.aplicar_dano)
            self.weapon_manager.update(); self.replication.sync_projectiles(); self.replication.interpolate_remotes()
            self._update_clock()
            self.renderer.draw_frame()
            pygame.display.flip(); self.reloj.tick(60)

    def _update_turns_and_player(self):
        if self.host and not self.turnos_iniciados and self.robots_remotos:
            players = [self.nombre_jugador, *self.robots_remotos.keys()]
            self.turn_manager.iniciar(players)
            self.enviar({"tipo": "turnos_init", "jugadores": players})
            self.turnos_iniciados = True
        if self.host and self.turnos_iniciados:
            self.turn_manager.actualizar(); self.turn_manager.enviar_sync()
        if self.turn_manager.jugador_actual() == self.nombre_jugador and not self.turn_manager.en_cooldown:
            keys = pygame.key.get_pressed(); self.robot.update(keys)
            if keys[pygame.K_DELETE]:
                self.robot.take_damage(50)
                if self.host:
                    self.turn_manager.forzar_fin_turno()
                    self.enviar({"tipo": "turno_fin", "jugador": self.nombre_jugador})
        else:
            self.robot.update([])
            if pygame.time.get_ticks() >= self.robot.aturdido_hasta: self.robot.vel_x = 0

    def _update_clock(self):
        if not self.host or self.game_over: return
        now, delta = self.now(), self.now() - self.ultimo_tick
        if delta >= 1:
            self.tiempo_restante = max(0, self.tiempo_restante - int(delta)); self.ultimo_tick = now
            self.enviar({"tipo": "timer", "restante": self.tiempo_restante})
            if not self.tiempo_restante: self.game_over = True
        if not self.game_over and self.modo.partida_terminada():
            self.tiempo_restante = 0; self.game_over = True
            self.enviar({"tipo": "timer", "restante": 0})
