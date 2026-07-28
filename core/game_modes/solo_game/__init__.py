# core/game_modes/solo_game/__init__.py
from .campaign import CampaignProgress
from .level_config import LevelConfig, BossConfig

__all__ = ["SoloGame", "CampaignProgress", "LevelConfig", "BossConfig"]


def __getattr__(name):
    # Consultar progreso/configuración no debe inicializar pygame.
    if name == "SoloGame":
        from .game import SoloGame
        return SoloGame
    raise AttributeError(name)
