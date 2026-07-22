import pygame
from settings import ANCHO, ALTO, ALTURA_SUELO
from levels.map_loader import load_static_map, load_static_map_laterales
from ui.hud import HUDArmas, HUDPuntajes
from ui.chat import Chat
from systems.aim_indicator import AimIndicator
from utils.paths import resource_path
from utils.sound_manager import sound_manager
from utils.weapon_loader import cargar_armas


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
        # Armas — catálogo dinámico (assets/weapons/<arma>/config.json) y
        # una única lista de proyectiles activos, sin importar de qué
        # arma sean (granada, misil, o lo que agregues después).
        self.proyectiles = []
        # Estados
        self.mouse_click_sostenido = False
        # Fondo
        self.fondo = pygame.image.load(resource_path("assets/maps/fondo.png")).convert()
        self.fondo = pygame.transform.smoothscale(self.fondo, (ANCHO, ALTO))
        # Fuente de mensajes de muerte
        self.fuente_muerte = pygame.font.SysFont("Verdana", 48, bold=True)
        # HUD — la lista de armas seleccionables se arma sola a partir de
        # lo que haya en assets/weapons/, no hace falta tocar código para
        # que aparezca un arma nueva en el HUD.
        self.hud_armas = HUDArmas(list(cargar_armas().keys()))
        self.font = pygame.font.SysFont('Arial', 20)
        self.puntajes = {}
        # Chat
        self.chat = Chat(nombre_jugador=self.nombre_jugador)
        # Sonido — música de fondo en loop durante toda la partida
        self.sound_manager = sound_manager
        self.sound_manager.iniciar_musica()

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

    def handle_events(self, event):
        """Maneja eventos generales y del chat"""
        self.chat.handle_event(event)

    def draw_ui(self):
        """Dibuja HUD y chat"""
        self.hud_armas.draw(self.pantalla)
        self.chat.draw(self.pantalla)
