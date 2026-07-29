# core/game_modes/solo_game/campaign.py
"""Reglas de desbloqueo; la UI nunca modifica el JSON de progreso directamente."""
from .level_repository import LevelRepository


class CampaignProgress:
    def __init__(self, repository: LevelRepository | None = None):
        self.repository = repository or LevelRepository()
        self.levels = self.repository.load_levels()
        self._by_id = {level.id: level for level in self.levels}
        self.progress = self.repository.load_progress()

    def refresh(self) -> None:
        """Recarga el progreso desde disco sin recrear todo el objeto.
        Pensado para pantallas de menú que viven varios frames: si el
        jugador completó un nivel y volvió, esto hace que el próximo
        nivel se vea desbloqueado sin tener que reabrir la pantalla."""
        self.progress = self.repository.load_progress()

    def is_unlocked(self, level_id: int) -> bool:
        level_id = int(level_id)
        if level_id not in self._by_id:
            return False
        previous = [item.id for item in self.levels if item.id < level_id]
        return not previous or max(previous) in self.progress["completed_levels"]

    def get_level(self, level_id: int):
        if not self.is_unlocked(level_id):
            raise PermissionError(f"El nivel {level_id} todavía está bloqueado")
        return self._by_id[int(level_id)]

    def complete_level(self, level_id: int, estrellas: int) -> None:
        level_id, estrellas = int(level_id), max(0, min(3, int(estrellas)))
        if level_id not in self._by_id:
            raise ValueError(f"Nivel inexistente: {level_id}")
        if level_id not in self.progress["completed_levels"]:
            self.progress["completed_levels"].append(level_id)
            self.progress["completed_levels"].sort()
        key = str(level_id)
        self.progress["stars"][key] = max(estrellas, self.progress["stars"].get(key, 0))
        unlocked = [level.id for level in self.levels if self.is_unlocked(level.id)]
        self.progress["highest_unlocked"] = max(unlocked, default=1)
        self.repository.save_progress(self.progress)

    def stars_for(self, level_id: int) -> int:
        return self.progress["stars"].get(str(level_id), 0)

    def next_level_id(self, level_id: int | None = None):
        current = int(level_id) if level_id is not None else max(self.progress["completed_levels"], default=0)
        for level in self.levels:
            if level.id > current and self.is_unlocked(level.id):
                return level.id
        return None