# levels/map_loader.py
# from levels.tile import Tile

####################### PARA PLATAFORMAS #######################

# # Lista de plataformas: (x, y, ancho, alto)
# PLATAFORMAS = [
#     (0, 415, 325, 100), # Piso parque izquierda
#     (760, 415, 290, 100), # Piso parque derecha
#     (330, 410, 6, 100), # Puente final izquierda
#     (350, 415, 6, 100), # Puente
#     (370, 420, 6, 100), # Puente
#     (390, 425, 6, 100), # Puente
#     (410, 430, 6, 100), # Puente centro
#     (430, 430, 6, 100), # Puente centro
#     (450, 430, 6, 100), # Puente centro
#     (470, 430, 6, 100), # Puente centro
#     (490, 430, 6, 100), # Puente centro
#     (510, 430, 6, 100), # Puente centro
#     (530, 430, 6, 100), # Puente centro
#     (550, 430, 6, 100), # Puente centro
#     (570, 430, 6, 100), # Puente centro
#     (590, 430, 6, 100), # Puente centro
#     (610, 430, 6, 100), # Puente centro
#     (630, 430, 6, 100), # Puente centro
#     (650, 430, 6, 100), # Puente centro
#     (670, 430, 6, 100), # Puente centro
#     (690, 425, 6, 100), # Puente
#     (710, 420, 6, 100), # Puente
#     (730, 415, 6, 100), # Puente
#     (750, 410, 6, 100), # Puente final derecha
#     #(992, -15, 6, 432), # Linea vertical derecha
#     #(-18, -12, 27, 423), # Linea vertical izquierda   
#     (609, 206, 129, 33), # Trozo tierra 1 derecha
#     (708, 311, 86, 33), # Trozo tierra 2 derecha
#     (100, 336, 55, 18), # Piedra
#     (107, 294, 62, 18), # Arbol 1 izquierda
#     (205, 204, 60, 18), # Arbol 2 izquierda
#     (140, 235, 80, 18), # Arbol 3 izquierda
#     (236, 261, 71, 18), # Arbol 4 izquierda
#     (221, 352, 28, 18), # Arbol 5 izquierda tallo
# ]

# #COLOR_POR_DEFECTO = (150, 150, 150)
# COLOR_POR_DEFECTO = None

# def load_static_map():
#     tiles = []
#     for x, y, w, h in PLATAFORMAS:
#         tiles.append(Tile(x, y, w, h, color= COLOR_POR_DEFECTO))
#     return tiles


# ####################### PARA LATERALES #######################

# LATERALES = [
#     (1020, -15, 6, 432), # Linea vertical derecha
#     (-55, -12, 27, 423), # Linea vertical izquierda   
# ]
# COLOR_POR_DEFECTO_LATERALES = (255, 0, 0)
# #COLOR_POR_DEFECTO_LATERALES = None

# def load_static_map_laterales():
#     tiles_laterales = []
#     for x, y, w, h in LATERALES:
#         tiles_laterales.append(Tile(x, y, w, h, color= COLOR_POR_DEFECTO_LATERALES))
#     return tiles_laterales







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