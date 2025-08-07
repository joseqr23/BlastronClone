from levels.tile import Tile

# Lista de plataformas: (x, y, ancho, alto)
PLATAFORMAS = [
    (100, 400, 100, 20),
    (200, 390, 100, 20),
    (300, 375, 100, 20),
    (400, 360, 100, 20),
    (500, 345, 100, 20),
    (0, 494 - 70, 1000, 70),  # suelo base  # Suelo base
    # Añade más plataformas aquí...
]

COLOR_POR_DEFECTO = (150, 150, 150)

def load_static_map():
    tiles = []
    for x, y, w, h in PLATAFORMAS:
        tiles.append(Tile(x, y, w, h, color= COLOR_POR_DEFECTO))
    return tiles