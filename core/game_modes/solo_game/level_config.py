# core/game_modes/solo_game/level_config.py
"""Configuración inmutable de un nivel de campaña."""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class BossConfig:
    robot_id: str
    sprite_folder: str | None = None
    vida_maxima: int = 800
    damage_multiplier: float = 1.35
    fases: tuple[float, ...] = (0.70, 0.35)
    armas: tuple[str, ...] = ("misil", "supermisil")


@dataclass(frozen=True)
class LevelConfig:
    id: int
    mapa: str
    modo: str = "lms"
    bots: int = 1
    dificultad: int = 1
    duracion_min: int = 3
    boss: BossConfig | None = None
    armas_bots: tuple[str, ...] = ("granada", "misil")

    @classmethod
    def from_dict(cls, data: dict) -> "LevelConfig":
        boss_data = data.get("boss")
        if boss_data is True:  # compatibilidad con el esquema inicial
            boss_data = {"robot_id": data.get("boss_id", "correnetali")}
        boss = BossConfig(
            robot_id=boss_data.get("robot_id", "correnetali"),
            sprite_folder=boss_data.get("sprite_folder"),
            vida_maxima=int(boss_data.get("vida_maxima", 800)),
            damage_multiplier=float(boss_data.get("damage_multiplier", 1.35)),
            fases=tuple(boss_data.get("fases", (0.70, 0.35))),
            armas=tuple(boss_data.get("armas", ("misil", "supermisil"))),
        ) if isinstance(boss_data, dict) else None
        return cls(
            id=int(data["id"]), mapa=str(data.get("mapa", "parque")),
            modo=str(data.get("modo", "lms")), bots=max(0, int(data.get("bots", 1))),
            dificultad=max(1, int(data.get("dificultad", 1))),
            duracion_min=max(1, int(data.get("duracion_min", 3))), boss=boss,
            armas_bots=tuple(data.get("armas_bots", ("granada", "misil"))),
        )
