# utils/mapa_loader.py
"""
Descubrimiento dinámico de mapas — mismo patrón que assets/weapons/.
Estructura esperada:
    assets/maps/<mapa_id>/fondo.png
    assets/maps/<mapa_id>/config.json
Para agregar un mapa nuevo no hace falta tocar ningún .py:
    1. Crea la carpeta assets/maps/<mapa_id>/
    2. Pon fondo.png (el fondo, como ya tienes assets/maps/fondo.png)
    3. Genera config.json con utils/map_editor.py, con esta forma:
       {
         "nombre": "Parque",
         "plataformas": [[x, y, ancho, alto], ...],
         "laterales": [[x, y, ancho, alto], ...]
       }
El menú detecta automáticamente todos los mapas en assets/maps/ y los
muestra con fondo.png como miniatura.
"""
import os
import json

_CACHE = None

def cargar_mapas(forzar_recarga=False):
    global _CACHE
    if _CACHE is not None and not forzar_recarga:
        return _CACHE
    base = "assets/maps"
    mapas = {}
    if not os.path.isdir(base):
        print(f"[Mapas] No existe la carpeta '{base}'")
        _CACHE = mapas
        return mapas
    for nombre in sorted(os.listdir(base)):
        carpeta = os.path.join(base, nombre)
        config_path = os.path.join(carpeta, "config.json")
        fondo_path = os.path.join(carpeta, "fondo.png")
        if not os.path.isdir(carpeta) or not os.path.isfile(config_path) or not os.path.isfile(fondo_path):
            continue
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception as e:
            print(f"[Mapas] No se pudo leer '{config_path}': {e}")
            continue
        config.setdefault("id", nombre)
        config.setdefault("nombre", nombre.title())
        config["_fondo_path"] = fondo_path
        mapas[nombre] = config
    _CACHE = mapas
    return mapas

def config_mapa(mapa_id):
    return cargar_mapas().get(mapa_id)

def listar_mapas():
    """[(id, nombre, fondo_path), ...] ordenado — para poblar el
    selector del menú."""
    return [
        (mid, cfg.get("nombre", mid), cfg["_fondo_path"])
        for mid, cfg in cargar_mapas().items()
    ]