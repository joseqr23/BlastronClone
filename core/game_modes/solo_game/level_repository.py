# core/game_modes/solo_game/level_repository.py
"""Acceso a contenido de campaña y al progreso local del jugador."""
import json
from pathlib import Path
from .level_config import LevelConfig


class LevelRepository:
    def __init__(self, levels_path: Path | None = None, progress_path: Path | None = None):
        package_dir = Path(__file__).resolve().parent
        self.levels_path = levels_path or package_dir / "data" / "levels.json"
        self.progress_path = progress_path or Path.home() / ".blastron_clone" / "solo_progress.json"

    def load_levels(self) -> list[LevelConfig]:
        try:
            raw = json.loads(self.levels_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"No se pudo cargar la campaña: {self.levels_path}") from exc
        levels = [LevelConfig.from_dict(item) for item in raw.get("levels", [])]
        if not levels:
            raise RuntimeError("levels.json no contiene niveles")
        return sorted(levels, key=lambda level: level.id)

    def load_progress(self) -> dict:
        default = {"completed_levels": [], "stars": {}, "highest_unlocked": 1}
        try:
            loaded = json.loads(self.progress_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return default
        completed = sorted({int(level) for level in loaded.get("completed_levels", [])})
        stars = {str(key): max(0, min(3, int(value))) for key, value in loaded.get("stars", {}).items()}
        return {"completed_levels": completed, "stars": stars,
                "highest_unlocked": max(1, int(loaded.get("highest_unlocked", 1)))}

    def save_progress(self, progress: dict) -> None:
        self.progress_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.progress_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(progress, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.progress_path)

    def load_mundos(self) -> list[str]:
        """Nombres de "mundo" por página del carrusel — opcional; si
        faltan, la UI cae a "Mundo N"."""
        try:
            raw = json.loads(self.levels_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        return [str(nombre) for nombre in raw.get("mundos", [])]