# # utils/paths.py
import os
import sys

# Carpeta raíz del proyecto o del .exe
if getattr(sys, "frozen", False):
    BASE_PATH = sys._MEIPASS
else:
    BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resource_path(*paths):
    """
    Une automáticamente cualquier ruta con la carpeta base.

    Ejemplo:
        resource_path("assets","hud","granada.png")
    """
    return os.path.join(BASE_PATH, *paths)


# Carpetas principales
ASSETS = resource_path("assets")

HUD = resource_path("assets", "hud")
MAPS = resource_path("assets", "maps")
ROBOTS = resource_path("assets", "robots")
WEAPONS = resource_path("assets", "weapons")
SFX = resource_path("assets", "sfx")
UI = resource_path("assets", "ui")