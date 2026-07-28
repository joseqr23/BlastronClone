# core/game_modes/multi_game/message_handler.py

import queue

from entities.players.robot import Robot
from utils.sound_manager import sound_manager


class MessageHandler:
    """Aplica mensajes en el hilo principal. Nunca desde NetworkManager."""
    LOBBY_TYPES = {"hello", "ready", "lobby_state", "match_start"}

    def __init__(self, game):
        self.game = game

    def process_pending(self):
        network = self.game.network
        while True:
            try:
                message, source_socket = network.incoming.get_nowait()
            except queue.Empty:
                return
            message_type = message.get("tipo")
            if self.game.host and message_type not in {"damage", "disparo", "hello", "ready"}:
                self.game.enviar(message, excluir_socket=source_socket)
            self.handle(message)

    def handle(self, message):
        game = self.game
        message_type = message.get("tipo")

        if message_type == "hello":
            if game.host:
                game.lobby_controller.register_client(
                    message.get("jugador"),
                    message.get("personaje", "robot"),
                )
            return

        if message_type == "ready":
            if game.host:
                game.lobby_controller.set_ready(
                    message.get("jugador"),
                    message.get("listo", False),
                )
            return

        if message_type == "lobby_state":
            if not game.host:
                game.lobby_controller.apply_remote_state(message)
            return

        if message_type == "match_start":
            if not game.host:
                game.lobby_controller.apply_remote_state(message)
                game.partida_iniciada = True
                game.ultimo_tick = game.now()
            return

        if message_type == "mapa_init":
            # Compatibilidad con mensajes de clientes/hosts de la versión anterior.
            if not game.host:
                from .lobby_state import LobbyConfig

                game.apply_lobby_config(LobbyConfig(
                    mapa_id=message.get("mapa_id", game.mapa_id),
                    duracion_min=message.get(
                        "duracion_min",
                        game.tiempo_total // 60,
                    ),
                    modo_partida=message.get(
                        "modo_partida",
                        game.modo_partida,
                    ),
                ))
            return
        
        if message_type == "update":
            self._apply_player_update(message); return
        if message_type == "disparo":
            if game.host: game.weapon_manager.crear_proyectil_host(message)
            return
        if message_type == "proy_sync":
            if not game.host: game.replication.apply_projectile_sync(message.get("items", []))
            return
        if message_type == "damage":
            player = message["jugador"]
            target = game.robot if player == game.nombre_jugador else game.robots_remotos.get(player)
            if target: target.take_damage(message["cantidad"])
            return
        if message_type == "empuje":
            if message.get("jugador") == game.nombre_jugador:
                game.robot.aplicar_empuje(message.get("vel_x", 0), message.get("vel_y", 0))
            return
        if message_type == "score":
            attacker, points = message["atacante"], message["puntos"]
            game.puntajes[attacker] = game.puntajes.get(attacker, 0) + points
            if message.get("victima_dead"):
                game.chat.agregar_mensaje(f"{message['victima']} fue detonado por {attacker}!")
            return
        if message_type == "muerte":
            victim_name = message["victima"]
            victim = game.robot if victim_name == game.nombre_jugador else game.robots_remotos.get(victim_name)
            if victim: game.modo.registrar_muerte(victim, message["atacante"])
            return
        if message_type == "chat":
            self._apply_chat(message); return
        if message_type == "timer":
            game.tiempo_restante = message["restante"]
            game.game_over = game.tiempo_restante <= 0
            return
        if message_type == "turnos_init":
            game.turn_manager.iniciar(message["jugadores"]); return
        if message_type == "mapa_init":
            if not game.host: game.apply_match_configuration(message)
            return
        if message_type == "turno_sync":
            self._apply_turn_sync(message); return
        if message_type == "turno_fin":
            self._apply_turn_end(message); return
        if message_type == "iniciar_partida":  # compatibilidad con clientes de la versión anterior
            game.partida_iniciada = True
            game.ultimo_tick = game.now()

    def _apply_player_update(self, message):
        game, player = self.game, message.get("jugador")
        if player == game.nombre_jugador:
            return
        sequence = message.get("seq", 0)
        if sequence <= game.last_sequences.get(player, -1):
            return
        game.last_sequences[player] = sequence
        remote = game.robots_remotos.get(player)
        if remote is None:
            remote = Robot(x=message["x"], y=message["y"], nombre_jugador=player,
                           nombre_robot=message.get("personaje", "robot"), es_remoto=True,
                           vida_maxima=game.vida_maxima, puede_reaparecer=game.modo.permite_reaparecer)
            remote.target_x, remote.target_y = remote.x, remote.y
            game.robots_remotos[player] = remote
            game.puntajes.setdefault(player, 0)
        previous_animation = remote.current_animation
        remote.target_x, remote.target_y = message["x"], message["y"]
        remote.frame_index = message.get("frame", 0)
        remote.current_animation = message.get("estado", "idle")
        remote.facing_right = message.get("direccion", 1) == 1
        remote.is_dead = remote.current_animation == "death"
        remote.arma_equipada = message.get("arma", remote.arma_equipada)
        remote.sin_municion = message.get("sin_municion", getattr(remote, "sin_municion", False))
        remote.aim_dx, remote.aim_dy = message.get("aim_dx", 0), message.get("aim_dy", 0)
        if remote.current_animation == "jump" and previous_animation != "jump": sound_manager.salto()
        if "health" in message: remote.health = message["health"]

    def _apply_chat(self, message):
        game, player = self.game, message.get("jugador")
        if player == game.nombre_jugador: return
        text = message["mensaje"]
        game.chat.agregar_mensaje(text)
        robot = game.robots_remotos.get(player)
        if robot: robot.mostrar_mensaje(text.split(": ", 1)[-1])

    def _apply_turn_sync(self, message):
        turns = self.game.turn_manager
        player, phase = message["jugador"], message.get("fase", "turno")
        if player in turns.jugadores: turns.turno_actual = turns.jugadores.index(player)
        turns.fase, turns.en_cooldown = phase, phase == "cooldown"
        if phase == "cooldown": turns.cooldown_restante_sync, turns.turno_inicio = message["tiempo"], None
        elif phase == "post_disparo": turns.post_disparo_restante_sync, turns.disparo_hecho = message["tiempo"], True
        else: turns.turno_restante_sync, turns.cooldown_inicio, turns.disparo_hecho = message["tiempo"], None, False

    def _apply_turn_end(self, message):
        game, player = self.game, message.get("jugador")
        if game.host: game.turn_manager.forzar_fin_turno()
        elif player == game.turn_manager.jugador_actual(): game.turn_manager.iniciar_cooldown()
        target = game.robot if player == game.nombre_jugador else game.robots_remotos.get(player)
        if target:
            target.vel_x = target.vel_y = 0
            target.current_animation = "idle"
