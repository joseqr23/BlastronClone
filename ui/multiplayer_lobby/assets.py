# ui/multiplayer_lobby/assets.py
import pygame

from utils.mapa_loader import listar_mapas
from utils.paths import resource_path


class LobbyAssets:
    def __init__(self):
        self.mapas = listar_mapas()
        self.portraits = {}
        self.map_thumbs = {}
        for mapa_id, _nombre, fondo_path in self.mapas:
            try:
                image = pygame.image.load(resource_path(fondo_path)).convert()
                self.map_thumbs[mapa_id] = pygame.transform.smoothscale(image, (88, 52))
            except Exception:
                self.map_thumbs[mapa_id] = None

    def portrait(self, personaje):
        if personaje not in self.portraits:
            try:
                image = pygame.image.load(resource_path(f"assets/robots/{personaje}/portrait.png")).convert_alpha()
                self.portraits[personaje] = pygame.transform.smoothscale(image, (64, 64))
            except Exception:
                self.portraits[personaje] = None
        return self.portraits[personaje]
