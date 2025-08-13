import pygame
from settings import ANCHO, ALTO, ALTURA_SUELO
from levels.map_loader import load_static_map, load_static_map_laterales
from ui.hud import HUDArmas, HUDPuntajes
from systems.aim_indicator import AimIndicator
from utils.paths import resource_path  # Importar para rutas seguras

class BaseGame:
    def __init__(self, nombre_jugador=None, personaje=None):
        pygame.init()
        self.nombre_jugador = nombre_jugador
        self.personaje = personaje

        self.pantalla = pygame.display.set_mode((ANCHO, ALTO))
        pygame.display.set_caption("Blastron Clone")
        self.reloj = pygame.time.Clock()

        # Mapas
        self.tiles = load_static_map()
        self.tiles_laterales = load_static_map_laterales()

        # Armas
        self.granadas = []
        self.misiles = []

        # Estados
        self.mouse_click_sostenido = False

        # Fondo
        self.fondo = pygame.image.load(resource_path("assets/maps/fondo.png")).convert()
        self.fondo = pygame.transform.smoothscale(self.fondo, (ANCHO, ALTO))

        # Fuente de mensajes de muerte
        self.fuente_muerte = pygame.font.SysFont("Verdana", 48, bold=True)

        # HUD
        self.hud_armas = HUDArmas(['granada', 'misil'], posicion=(10, 10))
        self.font = pygame.font.SysFont('Arial', 20)
        self.puntajes = {}

    def run(self):
        """Bucle principal del juego. Debe ser implementado o extendido por subclases."""
        raise NotImplementedError("Debes implementar este método en la subclase.")

    def draw_scene(self):
        """Dibuja el fondo, tiles y laterales"""
        self.pantalla.blit(self.fondo, (0, 0))
        for tile in self.tiles:
            tile.draw(self.pantalla)
        for tile in self.tiles_laterales:
            tile.draw(self.pantalla)
