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

from .lobby_state import LobbyConfig, LobbyState
from .lobby_controller import LobbyController
from ui.multiplayer_lobby import MultiplayerLobbyScreen
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
        self.requiere_confirmacion_menu = True
        self.confirmando_salida = False
        self.rect_volver_menu = self.rect_mute = None
        self.rect_confirmar_salida = self.rect_cancelar_salida = None
        self.fuente_botones = pygame.font.SysFont("Arial", 10, bold=True)
        self.mouse_click_sostenido = False
        self.font = pygame.font.SysFont("Arial", 16)

        self.tiempo_total = duracion_min * 60
        self.tiempo_restante = self.tiempo_total
        self.ultimo_tick = self.now()
        self.game_over = False
        self.game_over_at = None
        self.PODIUM_DELAY_S = 2.0
        self.timer_hud = HUDTimer(self, duracion=self.tiempo_total, posicion=(ANCHO // 2, 30))
        self.turn_manager = TurnManager(self)
        self.hud_turnos = HUDTurnos(self.turn_manager, posicion=(ANCHO // 2, 72))
        self.turnos_iniciados = False
        self.partida_iniciada = False

        self.lobby_state = LobbyState(
            host_id=nombre_jugador if host else "",
            config=LobbyConfig(
                mapa_id=mapa_id,
                duracion_min=duracion_min,
                modo_partida=modo_partida,
            ),
        )
        self.lobby_controller = LobbyController(self, self.lobby_state)
        if self.host:
            self.lobby_controller.add_local_host()

        self.network = NetworkManager(host, server_ip, port)
        self.replication = Replication(self)
        self.messages = MessageHandler(self)
        self.lobby_screen = MultiplayerLobbyScreen(self)
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

    def remove_remote_player(self, nombre):
        """Elimina un jugador que abandonó, sin bloquear el ciclo de turnos."""
        if not nombre or nombre == self.nombre_jugador:
            return
        self.robots_remotos.pop(nombre, None)
        self.last_sequences.pop(nombre, None)
        self.puntajes.pop(nombre, None)
        self.lobby_state.jugadores.pop(nombre, None)
        self.robots_estaticos = list(self.robots_remotos.values())

        turnos = self.turn_manager
        if nombre not in turnos.jugadores:
            return
        indice = turnos.jugadores.index(nombre)
        del turnos.jugadores[indice]
        if not turnos.jugadores:
            turnos.turno_actual = 0
            return
        if indice < turnos.turno_actual:
            turnos.turno_actual -= 1
        elif indice == turnos.turno_actual:
            turnos.turno_actual %= len(turnos.jugadores)
            turnos.fase = "turno"
            turnos.en_cooldown = False
            turnos.disparo_hecho = False
            turnos.turno_inicio = self.now()
            turnos.post_disparo_inicio = None
            turnos.cooldown_inicio = None
        if self.host:
            turnos.enviar_sync()

    def finish_if_one_player_left(self):
        if self.partida_iniciada and len(self.robots_remotos) == 0:
            self.tiempo_restante = 0
            self.game_over = True

    # ---------- Sala de espera ----------
    @property
    def local_ready(self):
        jugador = self.lobby_state.jugadores.get(self.nombre_jugador)
        return bool(jugador and jugador.listo)

    def apply_lobby_config(self, config):
        """Aplica la configuración de la sala antes de iniciar la partida."""
        if config.mapa_id != self.mapa_id:
            self.cargar_mapa(config.mapa_id)

        if config.modo_partida != self.modo_partida:
            self.modo_partida = config.modo_partida
            self.modo = crear_modo(config.modo_partida, self)
            self.vida_maxima = self.modo.vida_maxima
            for robot in [self.robot, *self.robots_remotos.values()]:
                robot.vida_maxima = self.vida_maxima
                robot.health = self.vida_maxima
                robot.puede_reaparecer = self.modo.permite_reaparecer

        self.tiempo_total = config.duracion_min * 60
        self.tiempo_restante = self.tiempo_total
        self.timer_hud = HUDTimer(self, duracion=self.tiempo_total, posicion=(ANCHO // 2, 30))

    # ---------- Ciclo público ----------
    def run(self):
        try:
            lobby_result = self.lobby_screen.run()
            if lobby_result != "start": return lobby_result
            self._sincronizar_colores()
            return self._run_match()
        finally:
            self._cerrar_red()

    def _sincronizar_colores(self):
        """Reasigna colores en un orden IDÉNTICO en todas las máquinas —
        el orden ya sincronizado del lobby (lobby_state.jugadores), en
        vez del orden en que cada cliente fue descubriendo a los demás
        por red (que varía según latencia, y por eso el HUD mostraba
        colores distintos entre máquinas para el mismo jugador)."""
        ColorManager.reset()
        for jugador in self.lobby_state.jugadores.keys():
            ColorManager.get_color(jugador)
        # self.robot ya existe desde __init__ (con su color asignado
        # ANTES del reset de arriba, y en un cliente incluso con el
        # nombre viejo sin renombrar) — se refresca acá para que quede
        # con el color correcto del orden canónico.
        self.robot.color_nombre = ColorManager.get_color(self.nombre_jugador)

    def _run_match(self):
        while True:
            if not self.robot.is_dead and self.robot.arma_equipada not in (None, "nada"):
                self.robot.facing_right = pygame.mouse.get_pos()[0] >= self.robot.get_centro()[0]
            if not self.event_handler.handle_events(): return None
            self.messages.process_pending()
            if self.volver_al_menu:
                return "menu"
            if self.game_over:
                if self.game_over_at is None:
                    self.game_over_at = self.now()
                if self.now() - self.game_over_at < self.PODIUM_DELAY_S:
                    self.renderer.draw_frame()
                    pygame.display.flip(); self.reloj.tick(60)
                    continue
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
        if not getattr(self.modo, "usa_turnos", True):
            # Modo libre: nadie espera turno, todos se mueven/disparan
            # siempre — la cadencia de ataque la limita el cooldown de
            # WeaponManager, no TurnManager.
            keys = pygame.key.get_pressed()
            self.robot.update(keys)
            if keys[pygame.K_DELETE]:
                self.robot.take_damage(50)
            return

        if self.host and not self.turnos_iniciados:
            players = list(self.lobby_state.jugadores.keys())
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
        if self.host and not self.game_over:
            self.modo.actualizar()
        if not self.host or self.game_over: return
        now, delta = self.now(), self.now() - self.ultimo_tick
        if delta >= 1:
            self.tiempo_restante = max(0, self.tiempo_restante - int(delta)); self.ultimo_tick = now
            self.enviar({"tipo": "timer", "restante": self.tiempo_restante})
            if not self.tiempo_restante: self.game_over = True
        if not self.game_over and self.modo.partida_terminada():
            self.tiempo_restante = 0; self.game_over = True
            self.enviar({"tipo": "timer", "restante": 0})

