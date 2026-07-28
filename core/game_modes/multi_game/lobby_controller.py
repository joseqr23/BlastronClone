# core/game_modes/multi_game/lobby_controller.py

from .lobby_state import LobbyPlayer


class LobbyController:
    """Reglas de la sala. Solo el Host puede alterar LobbyConfig."""
    def __init__(self, game, state):
        self.game = game
        self.state = state
        self.socket_a_jugador = {}

    def add_local_host(self):
        self.state.jugadores[self.game.nombre_jugador] = LobbyPlayer(
            self.game.nombre_jugador, self.game.personaje, listo=True
        )

    def register_client(self, nombre, personaje):
        if not self.game.host or not nombre:
            return None

        nombre_base = nombre.strip()
        nombre_final = nombre_base
        numero = 2

        while nombre_final in self.state.jugadores:
            sufijo = f" ({numero})"
            # Respeta el máximo de 29 caracteres del input del menú.
            nombre_final = nombre_base[:29 - len(sufijo)] + sufijo
            numero += 1

        self.state.jugadores[nombre_final] = LobbyPlayer(
            nombre_final, personaje, listo=False
        )
        return nombre_final

    def bind_client_socket(self, sock, nombre):
        """Asocia un socket TCP al nombre definitivo asignado por el host."""
        if sock is not None and nombre:
            self.socket_a_jugador[sock] = nombre

    def remove_client_socket(self, sock):
        """Quita al cliente desconectado y devuelve su nombre, si se conocía."""
        nombre = self.socket_a_jugador.pop(sock, None)
        if nombre:
            self.state.jugadores.pop(nombre, None)
        return nombre

    def set_ready(self, nombre, listo):
        if not self.game.host or nombre not in self.state.jugadores:
            return
        self.state.jugadores[nombre].listo = bool(listo)
        self.broadcast_state()

    def update_config(self, *, mapa_id=None, duracion_min=None, modo_partida=None):
        if not self.game.host:
            return False
        config = self.state.config
        changed = False
        if mapa_id is not None and mapa_id != config.mapa_id:
            config.mapa_id, changed = mapa_id, True
        if duracion_min is not None and duracion_min != config.duracion_min:
            config.duracion_min, changed = int(duracion_min), True
        if modo_partida is not None and modo_partida != config.modo_partida:
            config.modo_partida, changed = modo_partida, True
        if changed:
            self.game.apply_lobby_config(config)
            self.broadcast_state()
        return changed

    def apply_remote_state(self, message):
        self.state.apply_snapshot(message)
        self.game.apply_lobby_config(self.state.config)

    def broadcast_state(self):
        if self.game.host:
            self.game.enviar({"tipo": "lobby_state", **self.state.snapshot()})

    def can_start(self):
        return self.state.can_start()

    def start_match(self):
        if not self.game.host or not self.can_start():
            return False
        self.game.partida_iniciada = True
        self.game.ultimo_tick = self.game.now()
        self.game.enviar({"tipo": "match_start", **self.state.snapshot()})
        return True
