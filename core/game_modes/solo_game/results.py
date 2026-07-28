# core/game_modes/solo_game/results.py
from dataclasses import dataclass

@dataclass(frozen=True)
class LevelResult:
    level_id: int
    victory: bool
    stars: int
    reason: str
    next_level_id: int | None = None
