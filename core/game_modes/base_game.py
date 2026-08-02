# core/game_modes/base_game.py

import pygame
import random
from settings import ANCHO, ALTO
from levels.map_loader import (
    load_static_map, load_static_map_laterales,
    load_static_map_impenetrables, load_static_map_dañinas, cargar_dano_zonas_dañinas,
)
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

        # self.pantalla: superficie LÓGICA de juego, tamaño FIJO
        # (ANCHO x ALTO) — todo el código de dibujo/colisión sigue
        # trabajando con estas coordenadas exactamente igual que
        # siempre; ningún JSON de mapa necesita cambiar.
        # self.ventana: la ventana REAL en pantalla — puede ser más
        # grande (hasta pantalla completa). presentar() escala
        # self.pantalla hacia self.ventana cada frame.
        self.pantalla = pygame.Surface((ANCHO, ALTO)).convert()

        # Reusa la ventana real que ya esté abierta (la que dejó el menú,
        # con el tamaño que haya elegido el jugador) en vez de resetear
        # siempre a (ANCHO, ALTO) — antes cada partida nueva arrancaba
        # con el tamaño de fábrica sin importar la ventana del menú.
        superficie_actual = pygame.display.get_surface()
        if superficie_actual is not None and (superficie_actual.get_flags() & pygame.FULLSCREEN):
            self.ventana = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            self.pantalla_completa = True
            self._tamano_ventana_anterior = (ANCHO, ALTO)
        else:
            ancho_ventana, alto_ventana = superficie_actual.get_size() if superficie_actual is not None else (ANCHO, ALTO)
            ancho_ventana, alto_ventana = max(ANCHO, ancho_ventana), max(ALTO, alto_ventana)
            self.ventana = pygame.display.set_mode((ancho_ventana, alto_ventana), pygame.RESIZABLE)
            self.pantalla_completa = False
            self._tamano_ventana_anterior = (ancho_ventana, alto_ventana)
        pygame.display.set_caption("Blastron Clone")
        self._rect_presentacion = pygame.Rect(0, 0, ANCHO, ALTO)

        self.reloj = pygame.time.Clock()
        self.sound_manager = sound_manager
        self.superficie_mundo = pygame.Surface((ANCHO, ALTO)).convert()
        # Mapa — ver cargar_mapa() más abajo (también arranca la música
        # de ese mapa). En multijugador, el cliente arranca con el mapa
        # por defecto y lo reemplaza en cuanto el host le confirma cuál
        # está usando (ver multi_game.py) — cargar_mapa() se vuelve a
        # llamar ahí también, así que la música cambia junto con el mapa.
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

    def cargar_mapa(self, mapa_id):
        """Carga (o recarga) tiles/laterales/fondo según mapa_id. Se
        llama una vez en __init__, y en multijugador el cliente vuelve a
        llamarla cuando recibe "mapa_init" del host — así ambos terminan
        jugando el mismo mapa aunque el cliente no haya pasado por la
        pantalla de configuración de host."""
        self.mapa_id = mapa_id
        self.tiles = load_static_map(mapa_id)
        self.tiles_laterales = load_static_map_laterales(mapa_id)
        self.tiles_impenetrables = load_static_map_impenetrables(mapa_id)
        self.tiles_dañinas = load_static_map_dañinas(mapa_id)
        self.dano_zonas = cargar_dano_zonas_dañinas(mapa_id)
        config_del_mapa = config_mapa(mapa_id) or {}
        ruta_fondo = config_del_mapa.get("_fondo_path", "assets/maps/fondo.png")
        # self.fondo = pygame.image.load(resource_path(ruta_fondo)).convert()
        self.fondo = pygame.image.load(ruta_fondo).convert()
        self.fondo = pygame.transform.smoothscale(self.fondo, (ANCHO, ALTO))

        # Música del mapa: si la carpeta trae su propia musica.mp3, se
        # usa esa; si no, cae a la genérica de siempre.
        ruta_musica = config_del_mapa.get("_musica_path", "assets/sfx/musica.mp3")
        self.sound_manager.iniciar_musica(ruta_musica)


    def run(self):
        raise NotImplementedError("Debes implementar este método en la subclase.")

    def draw_scene(self, superficie=None):
        superficie = superficie or self.pantalla
        superficie.blit(self.fondo, (0, 0))
        for tile in self.tiles:
            tile.draw(superficie)
        for tile in self.tiles_laterales:
            tile.draw(superficie)
        for tile in self.tiles_impenetrables:
            tile.draw(superficie)
        for tile in self.tiles_dañinas:
            tile.draw(superficie)

    def handle_events(self, event):
        self.chat.handle_event(event)

    def draw_ui(self):
        self.hud_armas.draw(self.pantalla, self.font)
        self.chat.draw(self.pantalla)

    def activar_shake(self, intensidad, duracion_ms):
        ahora = pygame.time.get_ticks()
        fin_actual = getattr(self, "_shake_inicio", 0) + getattr(self, "_shake_duracion", 0)
        if ahora + duracion_ms > fin_actual:
            self._shake_inicio = ahora
            self._shake_duracion = duracion_ms
            self._shake_intensidad = intensidad

    def _offset_shake(self):
        ahora = pygame.time.get_ticks()
        inicio = getattr(self, "_shake_inicio", 0)
        duracion = getattr(self, "_shake_duracion", 0)
        transcurrido = ahora - inicio
        if duracion <= 0 or transcurrido >= duracion:
            return (0, 0)
        progreso = 1 - (transcurrido / duracion)
        mag = self._shake_intensidad * progreso
        return (random.uniform(-mag, mag), random.uniform(-mag, mag))

    # ------------------------------------------------------------------
    # Ventana redimensionable + escalado (zoom) de la escena lógica
    # ------------------------------------------------------------------
    def redimensionar_ventana(self, ancho, alto):
        ancho = max(ANCHO, ancho)
        alto = max(ALTO, alto)
        self.ventana = pygame.display.set_mode((ancho, alto), pygame.RESIZABLE)
        self.pantalla_completa = False

    def alternar_pantalla_completa(self):
        if self.pantalla_completa:
            self.ventana = pygame.display.set_mode(self._tamano_ventana_anterior, pygame.RESIZABLE)
            self.pantalla_completa = False
        else:
            self._tamano_ventana_anterior = self.ventana.get_size()
            self.ventana = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            self.pantalla_completa = True

    def presentar(self):
        ventana_ancho, ventana_alto = self.ventana.get_size()
        escala = min(ventana_ancho / ANCHO, ventana_alto / ALTO)
        nuevo_ancho, nuevo_alto = max(1, int(ANCHO * escala)), max(1, int(ALTO * escala))
        offset_x = (ventana_ancho - nuevo_ancho) // 2
        offset_y = (ventana_alto - nuevo_alto) // 2
        self._rect_presentacion = pygame.Rect(offset_x, offset_y, nuevo_ancho, nuevo_alto)

        if (nuevo_ancho, nuevo_alto) == (ANCHO, ALTO):
            escalada = self.pantalla
        else:
            escalada = pygame.transform.smoothscale(self.pantalla, (nuevo_ancho, nuevo_alto))

        self.ventana.fill((0, 0, 0))
        self.ventana.blit(escalada, (offset_x, offset_y))
        pygame.display.flip()

    def convertir_coordenadas(self, pos):
        x, y = pos
        rect = self._rect_presentacion
        if rect.width == 0 or rect.height == 0:
            return (0, 0)
        return ((x - rect.x) * ANCHO / rect.width, (y - rect.y) * ALTO / rect.height)

    def mouse_logico(self):
        return self.convertir_coordenadas(pygame.mouse.get_pos())