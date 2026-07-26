# levels/map_loader.py
from levels.tile import Tile
from utils.mapa_loader import config_mapa

COLOR_POR_DEFECTO_PLATAFORMAS = None #(0,255,0)
COLOR_POR_DEFECTO_LATERALES = None #(255, 0, 0)
COLOR_POR_DEFECTO_IMPENETRABLES= None #(255, 255, 0)
COLOR_POR_DEFECTO_DAÑINAS = None #(0, 0, 255)

# COLOR_POR_DEFECTO_PLATAFORMAS = (0,255,0)
# COLOR_POR_DEFECTO_LATERALES = (255, 0, 0)
# COLOR_POR_DEFECTO_IMPENETRABLES= (255, 255, 0)
# COLOR_POR_DEFECTO_DAÑINAS = (0, 0, 255)

def load_static_map(mapa_id="parque"):
    """Genera los tiles de plataformas del mapa indicado, leyendo su
    config.json (ver utils/mapa_loader.py). Si no se pasa mapa_id, usa
    "parque" por defecto — así el código existente que llama
    load_static_map() sin argumentos sigue funcionando igual mientras
    terminas de conectar la selección de mapa en cada modo de juego."""
    config = config_mapa(mapa_id) or {}
    return [Tile(x, y, w, h, color=COLOR_POR_DEFECTO_PLATAFORMAS) for x, y, w, h in config.get("plataformas", [])]

def load_static_map_laterales(mapa_id="parque"):
    config = config_mapa(mapa_id) or {}
    return [Tile(x, y, w, h, color=COLOR_POR_DEFECTO_LATERALES) for x, y, w, h in config.get("laterales", [])]


def load_static_map_impenetrables(mapa_id="parque"):
    """Igual que laterales para el robot (bloqueo lateral puro, sin
    "pisar por encima" — así se evita el bug de teletransporte), pero
    para las armas se tratan como una plataforma sólida más (ver más
    abajo cómo combinarlas al llamar a Proyectil.update)."""
    config = config_mapa(mapa_id) or {}
    return [Tile(x, y, w, h, color=COLOR_POR_DEFECTO_IMPENETRABLES) for x, y, w, h in config.get("plataformas_y_laterales_impenetrables", [])]

def load_static_map_dañinas(mapa_id="parque"):
    """Zonas que solo hacen daño por solapamiento — no bloquean nada, ni
    a robots ni a armas."""
    config = config_mapa(mapa_id) or {}
    return [Tile(x, y, w, h, color=COLOR_POR_DEFECTO_DAÑINAS) for x, y, w, h in config.get("plataformas_y_laterales_dañinas", [])]

def cargar_dano_zonas_dañinas(mapa_id="parque"):
    """Daño único global para TODAS las zonas dañinas del mapa (no por
    rectángulo individual). Si el mapa no define el campo, usa 20."""
    config = config_mapa(mapa_id) or {}
    return config.get("plataformas_y_laterales_dañinas_daño", 20)
