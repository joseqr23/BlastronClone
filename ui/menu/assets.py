# ui/menu/assets.py

import os
import pygame

from utils.paths import resource_path
from utils.mapa_loader import listar_mapas


class MenuAssets:
    ICONOS_MODO = {
        "Modo Solo": "solo_game.png",
        "Modo Multijugador": "multi_game.png",
        "Modo Libre": "free_game.png",
    }

    def __init__(self):
        self.iconos_modo = self._cargar_iconos()
        self.mapas = listar_mapas()
        self.mapa_thumbs = self._cargar_miniaturas()
        self.personajes, self.portraits = self._cargar_personajes()
        if not self.personajes:
            raise RuntimeError("No se encontró ningún robot con portrait.png en assets/robots.")

    def _cargar_iconos(self):
        resultado = {}
        for modo, archivo in self.ICONOS_MODO.items():
            try:
                imagen = pygame.image.load(resource_path(f"assets/ui/icons/{archivo}")).convert_alpha()
                resultado[modo] = pygame.transform.smoothscale(imagen, (28, 28))
            except Exception:
                resultado[modo] = None
        return resultado

    def _cargar_miniaturas(self):
        resultado = {}
        for mapa_id, _nombre, fondo_path in self.mapas:
            try:
                imagen = pygame.image.load(resource_path(fondo_path)).convert()
                resultado[mapa_id] = pygame.transform.smoothscale(imagen, (100, 62))
            except Exception:
                resultado[mapa_id] = None
        return resultado

    def _cargar_personajes(self):
        personajes, portraits = [], {}
        robots_path = resource_path("assets/robots")
        if not os.path.isdir(robots_path):
            return personajes, portraits
        for carpeta in sorted(os.listdir(robots_path)):
            portrait_path = os.path.join(robots_path, carpeta, "portrait.png")
            if os.path.isfile(portrait_path):
                personajes.append(carpeta)
                imagen = pygame.image.load(portrait_path).convert_alpha()
                portraits[carpeta] = pygame.transform.smoothscale(imagen, (64, 64))
        return personajes, portraits
