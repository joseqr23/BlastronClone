# core/game_modes/multi_game/lobby_state.py
from dataclasses import asdict, dataclass, field

@dataclass
class LobbyConfig:
    mapa_id: str = "parque"
    duracion_min: int = 3
    modo_partida: str = "puntos"


@dataclass
class LobbyPlayer:
    nombre: str
    personaje: str
    listo: bool = False
    conectado: bool = True


@dataclass
class LobbyState:
    host_id: str
    config: LobbyConfig
    jugadores: dict[str, LobbyPlayer] = field(default_factory=dict)

    def snapshot(self):
        return {
            "host_id": self.host_id,
            "config": asdict(self.config),
            "jugadores": [asdict(jugador) for jugador in self.jugadores.values()],
        }

    def apply_snapshot(self, snapshot):
        self.host_id = snapshot.get("host_id", self.host_id)
        config = snapshot.get("config", {})
        self.config = LobbyConfig(
            mapa_id=config.get("mapa_id", self.config.mapa_id),
            duracion_min=int(config.get("duracion_min", self.config.duracion_min)),
            modo_partida=config.get("modo_partida", self.config.modo_partida),
        )
        self.jugadores = {
            raw["nombre"]: LobbyPlayer(
                nombre=raw["nombre"], personaje=raw.get("personaje", "robot"),
                listo=bool(raw.get("listo", False)), conectado=bool(raw.get("conectado", True)),
            )
            for raw in snapshot.get("jugadores", []) if raw.get("nombre")
        }

    def can_start(self):
        return len(self.jugadores) >= 2 and all(
            jugador.listo for nombre, jugador in self.jugadores.items()
            if nombre != self.host_id
        )
