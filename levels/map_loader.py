# levels/map_loader.py
from levels.tile import Tile
from utils.mapa_loader import config_mapa

COLOR_POR_DEFECTO = None
COLOR_POR_DEFECTO_LATERALES = (255, 0, 0)

def load_static_map(mapa_id="parque"):
    """Genera los tiles de plataformas del mapa indicado, leyendo su
    config.json (ver utils/mapa_loader.py). Si no se pasa mapa_id, usa
    "parque" por defecto — así el código existente que llama
    load_static_map() sin argumentos sigue funcionando igual mientras
    terminas de conectar la selección de mapa en cada modo de juego."""
    config = config_mapa(mapa_id) or {}
    return [Tile(x, y, w, h, color=COLOR_POR_DEFECTO) for x, y, w, h in config.get("plataformas", [])]

def load_static_map_laterales(mapa_id="parque"):
    config = config_mapa(mapa_id) or {}
    return [Tile(x, y, w, h, color=COLOR_POR_DEFECTO_LATERALES) for x, y, w, h in config.get("laterales", [])]