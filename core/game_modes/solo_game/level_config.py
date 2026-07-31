# core/game_modes/solo_game/level_config.py
"""Configuración inmutable de un nivel de campaña."""
from dataclasses import dataclass, field

# Pool de robots usado como fallback cuando un nivel define "bots" como un
# número simple (esquema viejo) en vez de una lista explícita. Vive acá
# (y no en bot_manager.py) para que level_config no dependa de nada del
# motor del juego — solo de dataclasses.
DEFAULT_ROBOTS = ("alfonso", "cartman", "cholo", "correnetali", "eren", "estaly", "netali", "rosadito")


@dataclass(frozen=True)
class BotConfig:
    """Un bot individual dentro de un nivel: qué skin usa, cómo se llama
    en el HUD/turnos, cuánta vida tiene y con qué arma empieza."""
    robot_id: str
    nombre: str | None = None       # None -> se genera "Bot N" al spawnear
    vida_maxima: int | None = None  # None -> usa modo.vida_maxima del modo de partida
    arma: str = "misil"
    velocidad: float = 2.5
    salto: float = 15,
    distancia_acercamiento: float | None = None  # None = automático según el arma
    distancia_ataque: float | None = None        # None = automático según el arma
    mensaje: str | None = None  # frase de presentación, opcional

@dataclass(frozen=True)
class BossConfig:
    robot_id: str
    nombre: str = "JEFE"
    vida_maxima: int = 800
    damage_multiplier: float = 1.35
    fases: tuple[float, ...] = (0.70, 0.35)
    armas: tuple[str, ...] = ("misil", "supermisil")
    ancho: int = 60
    alto: int = 90
    velocidad: float = 2.5
    salto: float = 15
    distancia_acercamiento: float | None = None
    distancia_ataque: float | None = None
    mensaje: str | None = None
@dataclass(frozen=True)
class LevelConfig:
    id: int
    mapa: str
    modo: str = "lms"
    dificultad: int = 1
    duracion_min: int = 3
    nombre: str | None = None  # nombre visible del nivel — independiente del id y del mapa
    bots: tuple[BotConfig, ...] = ()
    boss: BossConfig | None = None
    armas_jugador: tuple[str, ...] = ()          # () = todas las armas disponibles
    municion_jugador: dict = field(default_factory=dict)  # override opcional de municion por arma
    vida_jugador: int | None = None  # None = usa modo.vida_maxima (comportamiento de siempre)
    velocidad_jugador: float | None = None  # None = usa el default de Robot (2.5)
    salto_jugador: float | None = None       # None = usa el default de Robot (15)

    @classmethod
    def from_dict(cls, data: dict) -> "LevelConfig":
        bots = tuple(cls._parse_bots(data))

        boss_data = data.get("boss")
        if boss_data is True:  # compatibilidad con el esquema inicial
            boss_data = {"robot_id": data.get("boss_id", "correnetali")}
        boss = BossConfig(
            robot_id=boss_data.get("robot_id", "correnetali"),
            nombre=boss_data.get("nombre", "JEFE"),
            vida_maxima=int(boss_data.get("vida_maxima", 800)),
            damage_multiplier=float(boss_data.get("damage_multiplier", 1.35)),
            fases=tuple(boss_data.get("fases", (0.70, 0.35))),
            armas=tuple(boss_data.get("armas", ("misil", "supermisil"))),
            ancho=int(boss_data.get("ancho", 60)),
            alto=int(boss_data.get("alto", 90)),
            velocidad=float(boss_data.get("velocidad", 2.5)),
            salto=float(boss_data.get("salto", 15)),
            distancia_acercamiento=boss_data.get("distancia_acercamiento"),
            distancia_ataque=boss_data.get("distancia_ataque"),
            mensaje=boss_data.get("mensaje"),
        ) if isinstance(boss_data, dict) else None

        return cls(
            id=int(data["id"]), mapa=str(data.get("mapa", "parque")),
            modo=str(data.get("modo", "lms")),
            dificultad=max(1, int(data.get("dificultad", 1))),
            duracion_min=max(1, int(data.get("duracion_min", 3))),
            nombre=data.get("nombre"),  # si falta, la UI cae a mapa.capitalize()
            bots=bots, boss=boss,
            armas_jugador=tuple(data.get("armas_jugador", ())),
            municion_jugador=dict(data.get("municion_jugador", {})),
            vida_jugador=data.get("vida_jugador"),
            velocidad_jugador=data.get("velocidad") if "velocidad" in data else data.get("velocidad_jugador"),
            salto_jugador=data.get("salto") if "salto" in data else data.get("salto_jugador"),
        )

    @staticmethod
    def _parse_bots(data: dict) -> list[BotConfig]:
        bots_data = data.get("bots", [])

        if isinstance(bots_data, int):
            # Esquema viejo: "bots": 2, "armas_bots": ["granada", "misil"]
            armas = data.get("armas_bots", ("misil",)) or ("misil",)
            return [
                BotConfig(
                    robot_id=DEFAULT_ROBOTS[i % len(DEFAULT_ROBOTS)],
                    arma=armas[i % len(armas)],
                )
                for i in range(max(0, bots_data))
            ]

        # Esquema nuevo: lista explícita de bots.
        return [
            BotConfig(
                robot_id=b["robot_id"],
                nombre=b.get("nombre"),
                vida_maxima=b.get("vida_maxima"),
                arma=b.get("arma", "misil"),
                velocidad=float(b.get("velocidad", 2.5)),
                salto=float(b.get("salto", 15)),
                distancia_acercamiento=b.get("distancia_acercamiento"),
                distancia_ataque=b.get("distancia_ataque"),
                mensaje=b.get("mensaje"),
            )
            for b in bots_data
        ]