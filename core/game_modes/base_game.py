import pygame
from settings import ANCHO, ALTO, ALTURA_SUELO
from levels.map_loader import load_static_map, load_static_map_laterales
from ui.hud import HUDArmas, HUDPuntajes
from ui.chat import Chat
from systems.aim_indicator import AimIndicator
from utils.paths import resource_path
from utils.sound_manager import sound_manager
from utils.weapon_loader import cargar_armas
from utils.mapa_loader import config_mapa

class BaseGame:
    def __init__(self, nombre_jugador=None, personaje=None, mapa_id="parque"):
        pygame.init()
        self.nombre_jugador = nombre_jugador
        self.personaje = personaje
        self.pantalla = pygame.display.set_mode((ANCHO, ALTO))
        pygame.display.set_caption("Blastron Clone")
        self.reloj = pygame.time.Clock()
        # Mapa — ver cargar_mapa() más abajo. En multijugador, el cliente
        # arranca con el mapa por defecto y lo reemplaza en cuanto el
        # host le confirma cuál está usando (ver multi_game.py).
        self.cargar_mapa(mapa_id)
        # Armas — catálogo dinámico (assets/weapons/<arma>/config.json) y
        # una única lista de proyectiles activos, sin importar de qué
        # arma sean (granada, misil, o lo que agregues después).
        self.proyectiles = []
        self.mouse_click_sostenido = False
        self.fuente_muerte = pygame.font.SysFont("Verdana", 48, bold=True)
        self.hud_armas = HUDArmas(list(cargar_armas().keys()))
        self.font = pygame.font.SysFont('Arial', 20)
        self.puntajes = {}
        self.chat = Chat(nombre_jugador=self.nombre_jugador)
        self.sound_manager = sound_manager
        self.sound_manager.iniciar_musica()

    def cargar_mapa(self, mapa_id):
        """Carga (o recarga) tiles/laterales/fondo según mapa_id. Se
        llama una vez en __init__, y en multijugador el cliente vuelve a
        llamarla cuando recibe "mapa_init" del host — así ambos terminan
        jugando el mismo mapa aunque el cliente no haya pasado por la
        pantalla de configuración de host."""
        self.mapa_id = mapa_id
        self.tiles = load_static_map(mapa_id)
        self.tiles_laterales = load_static_map_laterales(mapa_id)
        config_del_mapa = config_mapa(mapa_id) or {}
        ruta_fondo = config_del_mapa.get("_fondo_path", "assets/maps/fondo.png")
        self.fondo = pygame.image.load(resource_path(ruta_fondo)).convert()
        self.fondo = pygame.transform.smoothscale(self.fondo, (ANCHO, ALTO))

    def run(self):
        raise NotImplementedError("Debes implementar este método en la subclase.")

    def draw_scene(self):
        self.pantalla.blit(self.fondo, (0, 0))
        for tile in self.tiles:
            tile.draw(self.pantalla)
        for tile in self.tiles_laterales:
            tile.draw(self.pantalla)

    def handle_events(self, event):
        self.chat.handle_event(event)

    def draw_ui(self):
        self.hud_armas.draw(self.pantalla)
        self.chat.draw(self.pantalla)