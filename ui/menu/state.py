# ui/menu/state.py

from dataclasses import dataclass, field

@dataclass
class HostConfig:
    duracion_min: int = 3
    modo_partida: str = "puntos"
    mapa_id: str | None = None


@dataclass
class FreeConfig:
    mapa_id: str | None = None


@dataclass
class MenuState:
    pantalla: str = "principal"  # principal | host_config | free_config | solo_config
    opcion_seleccionada: int = 1
    personaje_idx: int = 0
    nombre_jugador: str = ""
    editando_nombre: bool = True
    multijugador_opcion: str = "host"  # host | cliente
    host: HostConfig = field(default_factory=HostConfig)
    libre: FreeConfig = field(default_factory=FreeConfig)
