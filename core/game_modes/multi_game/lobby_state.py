from dataclasses import asdict, dataclass, field


@dataclass
class LobbyPlayer:
    nombre: str
    personaje: str
    listo: bool = False
    conectado: bool = True

    def to_message(self):
        return asdict(self)


@dataclass
class LobbyConfig:
    mapa_id: str
    duracion_min: int
    modo_partida: str

    def to_message(self):
        return asdict(self)


@dataclass
class LobbyState:
    host_id: str | None
    config: LobbyConfig
    jugadores: dict[str, LobbyPlayer] = field(default_factory=dict)

    def to_message(self, message_type="lobby_state"):
        return {
            "tipo": message_type,
            "host_id": self.host_id,
            "config": self.config.to_message(),
            "jugadores": [jugador.to_message() for jugador in self.jugadores.values()],
        }

    def load_message(self, message):
        self.host_id = message.get("host_id", self.host_id)
        config = message.get("config", {})
        self.config = LobbyConfig(
            mapa_id=config.get("mapa_id", self.config.mapa_id),
            duracion_min=int(config.get("duracion_min", self.config.duracion_min)),
            modo_partida=config.get("modo_partida", self.config.modo_partida),
        )
        self.jugadores = {
            item["nombre"]: LobbyPlayer(
                nombre=item["nombre"], personaje=item.get("personaje", "robot"),
                listo=bool(item.get("listo", False)), conectado=bool(item.get("conectado", True)),
            )
            for item in message.get("jugadores", []) if item.get("nombre")
        }