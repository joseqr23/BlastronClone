# core/game_modes/solo_game/game.py
"""Partida local de campaña — mismo motor de turnos que multi_game, pero
SoloGame actúa como el único "host" posible: no hay red, los bots y el
jefe ocupan el rol de robots_remotos, y enviar() resuelve localmente lo
poco que WeaponManager/TurnManager esperaban delegar a otras máquinas."""
import math
import time

import pygame

from settings import ANCHO, ALTO, ALTURA_SUELO
from core.game_modes.base_game import BaseGame
from core.game_modes.multi_game.renderer import MultiplayerRenderer
from core.game_modes.multi_game.results import ResultsScreen
from entities.players.robot import Robot
from systems.aim_indicator import AimIndicator
from systems.collision import (check_collisions, check_collisions_laterales_esquinas,
                               check_colision_bloque_solido, check_zonas_dañinas)
from systems.event_handler import EventHandler
from systems.hud_manager import HUDManager
from systems.modos_partida import crear_modo
from systems.turn_manager import TurnManager
from systems.weapon_manager import WeaponManager
from ui.chat import Chat
from ui.hud import HUDArmas, HUDPuntajesMultiplayer, HUDTimer, HUDTurnos
from utils.colors import ColorManager
from utils.weapon_loader import cargar_armas, config_arma

from .campaign import CampaignProgress
from .results import LevelResult
from .rewards import calculate_stars
from .npc_manager import NpcManager

from .intro_screen import IntroScreen

class SoloGame(BaseGame):
    """Campaña contra bots/jefe, por turnos — arquitectónicamente es un
    MultiplayerGame de un solo proceso: mismo TurnManager, mismo
    WeaponManager, mismo modos_partida. Los bots viven en
    self.robots_remotos igual que jugadores remotos reales."""

    def __init__(self, nombre_jugador, personaje, level_id=1, campaign=None):
        self.campaign = campaign or CampaignProgress()
        self.level = self.campaign.get_level(level_id)
        super().__init__(nombre_jugador=nombre_jugador, personaje=personaje, mapa_id=self.level.mapa)
        ColorManager.reset()
        self.host = True  # compatibilidad con utilidades compartidas (TurnManager, WeaponManager, etc.)

        self.modo_partida = self.level.modo
        self.modo = crear_modo(self.modo_partida, self)
        self.vida_maxima = self.modo.vida_maxima

        armas_disponibles = list(self.level.armas_jugador) or list(cargar_armas().keys())

        vida_jugador = self.level.vida_jugador or self.vida_maxima
        self.robot = Robot(ANCHO // 2 - 30, ALTO - ALTURA_SUELO - 90, nombre_jugador, personaje,
                           vida_maxima=vida_jugador, puede_reaparecer=self.modo.permite_reaparecer,
                           velocidad=self.level.velocidad_jugador or 2.5,
                           salto=self.level.salto_jugador or 15)
        self.robot.es_jugador = True
        self.robot.arma_equipada = armas_disponibles[0]

        # ---- Bots y jefe: ocupan el mismo rol que un jugador remoto ----
        self.robots_remotos = {}
        self.robots_estaticos = []  # se refresca cada frame con robots_remotos.values()
        self.last_sequences = {}    # no aplica sin red, pero algunas utilidades compartidas lo esperan

        self.npc_manager = NpcManager(self, self.level.bots, self.level.dificultad, seed=self.level.id)
        self.robots_remotos.update(self.npc_manager.spawn_bots())
        if self.level.boss:
            self.robots_remotos.update(self.npc_manager.spawn_boss(self.level.boss))

        for nombre in self.robots_remotos:
            ColorManager.get_color(nombre)

        self.puntajes = {nombre_jugador: 0}
        for nombre in self.robots_remotos:
            self.puntajes[nombre] = 0

        self.aim = AimIndicator(self.robot.get_centro())
        self.aim_remoto = AimIndicator((0, 0))  # requerido por MultiplayerRenderer
        self.weapon_manager = WeaponManager(self)
        for arma, cantidad in self.level.municion_jugador.items():
            self.weapon_manager.municion_restante[arma] = cantidad
        self.hud_puntajes = HUDPuntajesMultiplayer(self)
        self.hud_armas = HUDArmas(armas_disponibles)
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

        self.tiempo_total = self.level.duracion_min * 60
        self.tiempo_restante = self.tiempo_total
        self.ultimo_tick = self.now()
        self.game_over = False
        self.game_over_at = None
        self.PODIUM_DELAY_S = 2.0
        self.timer_hud = HUDTimer(self, duracion=self.tiempo_total, posicion=(ANCHO // 2, 30))
        self.turn_manager = TurnManager(self)
        self.hud_turnos = HUDTurnos(self.turn_manager, posicion=(ANCHO // 2, 72))
        self.turnos_iniciados = False

        self.renderer = MultiplayerRenderer(self)
        self.results = ResultsScreen(self)
        self._proj_id = 0
        self.result = None

    def now(self):
        return time.time()

    def all_robots(self):
        return [self.robot, *self.robots_remotos.values()]

    def robot_by_name(self, name):
        if name == self.nombre_jugador:
            return self.robot
        return self.robots_remotos.get(name)

    # ---------- API que WeaponManager / TurnManager esperan de un "host" ----------
    def _next_proy_id(self):
        self._proj_id += 1
        return self._proj_id

    def enviar(self, message, excluir_socket=None):
        """No hay red: el único efecto que de verdad hace falta reenviar
        es el empuje sobre un bot/jefe (para el jugador local ya se
        aplica directo en WeaponManager._aplicar_empuje). El resto de
        tipos ("damage", "score", "muerte", "timer", "turno_sync") ya se
        aplicaron localmente antes de esta llamada — no hay nada más
        que hacer con ellos en un solo proceso."""
        if message.get("tipo") == "empuje":
            robot = self.robot_by_name(message.get("jugador"))
            if robot:
                robot.aplicar_empuje(message.get("vel_x", 0), message.get("vel_y", 0))

    def enviar_chat(self, mensaje):
        #self.chat.agregar_mensaje(f"{self.nombre_jugador}: {mensaje}")  >> No hace falta, ya lo hace Chat.handle_event() antes de llamar a enviar_chat()
        pass

    def enviar_evento_puntaje(self, atacante, puntos, victima):
        self.puntajes[atacante] = self.puntajes.get(atacante, 0) + puntos
        if victima.health <= 0:
            self.chat.agregar_mensaje(f"{victima.nombre_jugador} fue derrotado por {atacante}!")
        self.enviar({"tipo": "score", "atacante": atacante, "puntos": puntos,
                     "victima": victima.nombre_jugador, "victima_dead": victima.health <= 0})

    def enviar_evento_muerte(self, atacante, victima):
        self.modo.registrar_muerte(victima, atacante)
        self.enviar({"tipo": "muerte", "atacante": atacante, "victima": victima.nombre_jugador})

    # ---------- Ciclo público ----------
    def run(self):
        entradas = [(bot.robot_id, bot.nombre or bot.robot_id.capitalize(), bot.mensaje) for bot in self.level.bots]
        if self.level.boss:
            entradas.append((self.level.boss.robot_id, self.level.boss.nombre, self.level.boss.mensaje))
        resultado = IntroScreen(self, entradas).run()
        if resultado is None:
            return None
        pygame.event.clear()
        return self._run_match()

    def _run_match(self):
        while True:
            if not self.robot.is_dead and self.robot.arma_equipada not in (None, "nada"):
                self.robot.facing_right = self.mouse_logico()[0] >= self.robot.get_centro()[0]
            if not self.event_handler.handle_events():
                return None
            if self.volver_al_menu:
                return "menu"
            if self.game_over:
                if self.game_over_at is None:
                    self.game_over_at = self.now()
                if self.now() - self.game_over_at < self.PODIUM_DELAY_S:
                    self.renderer.draw_frame()
                    self.presentar(); self.reloj.tick(60)
                    continue
                self._finalizar_si_falta()
                return "menu" if self.results.show(self.modo.etiqueta_podio()) else None

            self._actualizar_turno_y_actores()
            self._actualizar_fisica()
            self.robots_estaticos = list(self.robots_remotos.values())
            for robot in [self.robot, *self.robots_estaticos]:
                check_zonas_dañinas(robot, self.tiles_dañinas, self.dano_zonas,
                                    aplicar_dano_callback=self.weapon_manager.aplicar_dano)
            self.weapon_manager.update()
            self.modo.actualizar()
            self._actualizar_reloj()
            self._chequear_fin_de_partida()
            self.renderer.draw_frame()
            self.presentar()
            self.reloj.tick(60)

    # ---------- Turnos: jugador humano + bots + jefe ----------
    def _actualizar_turno_y_actores(self):
        if not getattr(self.modo, "usa_turnos", True):
            self._actualizar_libre()
            return

        if not self.turnos_iniciados:
            jugadores = [self.nombre_jugador] + list(self.robots_remotos.keys())
            self.turn_manager.iniciar(jugadores)
            self.turnos_iniciados = True

        self.turn_manager.actualizar()
        actual = self.turn_manager.jugador_actual()
        en_cooldown = self.turn_manager.en_cooldown

        if actual == self.nombre_jugador and not en_cooldown:
            keys = pygame.key.get_pressed()
            self.robot.update(keys)
        else:
            self.robot.update([])
            if pygame.time.get_ticks() >= self.robot.aturdido_hasta:
                self.robot.vel_x = 0

        for nombre, robot in self.robots_remotos.items():
            if robot.is_dead:
                robot.update([])
                continue

            controlador = self.npc_manager.controllers.get(robot)
            if actual == nombre and not en_cooldown and controlador:
                aim = controlador.update(self.robot)
                robot.update(None)
                if aim:
                    robot.aim_dx, robot.aim_dy = aim
                    if self.turn_manager.puede_disparar() and controlador.should_fire(self.robot):
                        self._disparar_bot(nombre, robot, aim)
            else:
                if pygame.time.get_ticks() >= robot.aturdido_hasta:
                    robot.vel_x = 0
                robot.update([])

    def _actualizar_libre(self):
        """Modo libre: sin turnos — el jugador y TODOS los bots actúan
        cada frame. Los bots persiguen sin tregua (ver
        persigue_sin_tregua en BotController)."""
        keys = pygame.key.get_pressed()
        self.robot.update(keys)
        if keys[pygame.K_DELETE]:
            self.robot.take_damage(50)

        for nombre, robot in self.robots_remotos.items():
            if robot.is_dead:
                robot.update([])
                continue
            controlador = self.npc_manager.controllers.get(robot)
            if not controlador:
                robot.update([])
                continue
            aim = controlador.update(self.robot)
            robot.update(None)
            if aim:
                robot.aim_dx, robot.aim_dy = aim
                if controlador.should_fire(self.robot):
                    self._disparar_bot(nombre, robot, aim)

    def _disparar_bot(self, nombre, robot, direccion):
        """Camino de disparo para bots/jefe: no pasa por WeaponManager.disparar()
        (esa función asume mouse/jugador local) — arma el mismo mensaje que
        generaría un cliente remoto y lo entrega directo a crear_proyectil_host,
        que ya se encarga de la física, el sonido, la ráfaga escalonada
        (intervalo_disparos_ms) y de avisarle a TurnManager que se disparó.

        Munición ilimitada para bots (ver nota sobre
        WeaponManager.municion_restante compartido por arma, no por jugador)."""
        tm = self.turn_manager
        if getattr(self.modo, "usa_turnos", True):
            if tm.jugador_actual() != nombre or not tm.puede_disparar():
                return
        arma = robot.arma_equipada or "misil"
        config = config_arma(arma)
        if not config:
            return
        ancho, alto = config.get("ancho_proyectil", 40), config.get("alto_proyectil", 40)
        origen = robot.get_centro()
        disparos = self._generar_disparos_bot(config, direccion, origen, ancho, alto)
        if not disparos:
            return
        self.weapon_manager.crear_proyectil_host({
            "tipo": "disparo",
            "jugador": nombre,
            "arma": arma,
            "facing_right": robot.facing_right,
            "angulo_ataque": math.degrees(math.atan2(direccion[1], direccion[0])),
            "disparos": disparos,
        })

    def _generar_disparos_bot(self, config, direccion, origen, ancho, alto):
        """Igual que WeaponManager._generar_disparos, pero partiendo de un
        vector de dirección (el aim del bot) en vez del mouse — así un
        rifle con "cantidad": 10 también dispara 10 proyectiles en
        abanico cuando lo usa un bot, no solo cuando lo usa el jugador."""
        dx, dy = direccion
        largo = math.hypot(dx, dy)
        if not largo:
            return []
        velocidad = config.get("velocidad_proyectil", 20)
        vel_x, vel_y = dx / largo * velocidad, dy / largo * velocidad
        cantidad = max(1, config.get("cantidad", 1))
        base = {"x": origen[0] - ancho / 2, "y": origen[1] - alto / 2}
        if cantidad == 1:
            return [{**base, "dir_x": vel_x, "dir_y": vel_y}]

        spread_total = config.get("dispersion_grados", 18)
        resultados = []
        for i in range(cantidad):
            t = (i / (cantidad - 1)) - 0.5  # de -0.5 a 0.5
            offset_rad = math.radians(t * spread_total)
            rot_x = vel_x * math.cos(offset_rad) - vel_y * math.sin(offset_rad)
            rot_y = vel_x * math.sin(offset_rad) + vel_y * math.cos(offset_rad)
            resultados.append({**base, "dir_x": rot_x, "dir_y": rot_y})
        return resultados

    def _actualizar_fisica(self):
        """A diferencia de multi_game (donde los robots remotos solo
        interpolan posiciones que llegan por red), acá SÍ somos la única
        fuente de verdad para los bots — hay que resolver su colisión
        contra el mapa cada frame, no solo en su turno, o se hunden en
        el piso mientras esperan."""
        for robot in [self.robot, *self.robots_remotos.values()]:
            check_collisions(robot, self.tiles)
            check_collisions_laterales_esquinas(robot, self.tiles_laterales)
            check_colision_bloque_solido(robot, self.tiles_impenetrables)

    def _actualizar_reloj(self):
        if self.game_over:
            return
        ahora, delta = self.now(), self.now() - self.ultimo_tick
        if delta >= 1:
            self.tiempo_restante = max(0, self.tiempo_restante - int(delta))
            self.ultimo_tick = ahora
            if not self.tiempo_restante:
                self.game_over = True

    def _chequear_fin_de_partida(self):
        if not self.game_over and self.modo.partida_terminada():
            self.tiempo_restante = 0
            self.game_over = True

    # ---------- Resultado de nivel: gana solo si termina primero, solo ----------
    def _finalizar_si_falta(self):
        if self.result:
            return
        rango, jugadores_top = self.modo.podio()[0]
        gano = len(jugadores_top) == 1 and jugadores_top[0][0] == self.nombre_jugador
        elapsed_ratio = 1 - (self.tiempo_restante / self.tiempo_total)
        health_ratio = max(0, self.robot.health) / self.robot.vida_maxima
        stars = calculate_stars(gano, health_ratio, elapsed_ratio)
        if gano:
            self.campaign.complete_level(self.level.id, stars)
        self.result = LevelResult(
            self.level.id, gano, stars,
            "Nivel completado" if gano else "No quedaste en primer lugar",
            self.campaign.next_level_id(self.level.id) if gano else None,
        )