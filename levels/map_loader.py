from levels.tile import Tile

# Lista de plataformas: (x, y, ancho, alto)
PLATAFORMAS = [
    (0, 408, 325, 18),
    (330, 406, 18, 12),
    (350, 416, 27, 7),
    (383, 423, 29, 8),
    (414, 428, 33, 6),
    (444, 431, 177, 8),
    (628, 432, 32, 7),
    (662, 428, 36, 8),
    (697, 421, 34, 11),
    (726, 412, 27, 10),
    (751, 417, 239, 9),
    (981, 416, 29, 11),
    (992, -15, 6, 432),
    (-18, -12, 27, 423),
    (86, 336, 75, 73),
    (221, 352, 48, 58),
    (236, 261, 71, 10),
    (117, 235, 117, 7),
    (195, 204, 90, 13),
    (609, 206, 129, 6),
    (708, 311, 86, 7),
    (93, 294, 62, 6),
    #(0, 494 - 70, 1000, 70),  # suelo base  # Suelo base

    # Añade más plataformas aquí...
]

COLOR_POR_DEFECTO = (150, 150, 150)
#COLOR_POR_DEFECTO = None

def load_static_map():
    tiles = []
    for x, y, w, h in PLATAFORMAS:
        tiles.append(Tile(x, y, w, h, color= COLOR_POR_DEFECTO))
    return tiles