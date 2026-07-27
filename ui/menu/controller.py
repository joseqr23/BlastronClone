import pygame

from ui.text_input import TextInput

from .assets import MenuAssets
from .state import MenuState
from .theme import MenuFonts, draw_vertical_gradient
from .widgets import Toast
from .screens.main import MainScreen
from .screens.host_config import HostConfigScreen
from .screens.free_config import FreeConfigScreen


class Menu:
    """Punto de entrada compatible con el antiguo ui/menu.py."""
    def __init__(self, pantalla):
        self.pantalla = pantalla
        self.ancho, self.alto = pantalla.get_size()
        self.fonts = MenuFonts.create()
        self.assets = MenuAssets()
        self.state = MenuState()
        primer_mapa = self.assets.mapas[0][0] if self.assets.mapas else None
        self.state.host.mapa_id = primer_mapa
        self.state.libre.mapa_id = primer_mapa
        self.toast = Toast()
        self.nombre_input = TextInput((0, 0, 260, 38), self.fonts.input, max_length=29)
        self.ip_input = TextInput((0, 0, 220, 34), self.fonts.input, max_length=15)
        self.ip_input.text = "192.168.1.236"
        self.screens = {
            "principal": MainScreen(self.state, self.assets, self.fonts, self.nombre_input, self.ip_input, self.toast),
            "host_config": HostConfigScreen(self.state, self.assets, self.fonts, self.toast),
            "free_config": FreeConfigScreen(self.state, self.assets, self.fonts, self.toast),
        }
        self.cursor_actual = None

    def _nombre_y_personaje(self):
        return {
            "nombre": self.nombre_input.get_text() or "Jugador",
            "personaje": self.assets.personajes[self.state.personaje_idx],
        }

    def _construir_cliente(self):
        return {"modo": "Modo Multijugador", **self._nombre_y_personaje(), "host": False, "server_ip": self.ip_input.get_text()}

    def _construir_host(self):
        return {
            "modo": "Modo Multijugador", **self._nombre_y_personaje(), "host": True,
            "server_ip": "127.0.0.1", "duracion_min": self.state.host.duracion_min,
            "modo_partida": self.state.host.modo_partida, "mapa": self.state.host.mapa_id or "parque",
        }

    def _construir_libre(self):
        return {"modo": "Modo Libre", **self._nombre_y_personaje(), "mapa": self.state.libre.mapa_id or "parque"}

    def _resolver_accion(self, action):
        if action == "abrir_host": self.state.pantalla = "host_config"
        elif action == "abrir_libre": self.state.pantalla = "free_config"
        elif action == "volver": self.state.pantalla = "principal"
        elif action == "conectar_cliente": return self._construir_cliente()
        elif action == "empezar_host": return self._construir_host()
        elif action == "empezar_libre": return self._construir_libre()
        return None

    def run(self):
        clock = pygame.time.Clock()
        pygame.key.set_repeat(400, 40)
        fondo = pygame.Surface((self.ancho, self.alto))
        draw_vertical_gradient(fondo)
        while True:
            self.pantalla.blit(fondo, (0, 0))
            mouse_pos = pygame.mouse.get_pos()
            pantalla_actual = self.screens[self.state.pantalla]
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    raise SystemExit
                action = pantalla_actual.handle_event(event, mouse_pos)
                resultado = self._resolver_accion(action)
                if resultado is not None:
                    return resultado
                pantalla_actual = self.screens[self.state.pantalla]
            self.nombre_input.update()
            self.ip_input.update()
            hover = self.screens[self.state.pantalla].draw(self.pantalla, mouse_pos)
            cursor = pygame.SYSTEM_CURSOR_HAND if hover else pygame.SYSTEM_CURSOR_ARROW
            if cursor != self.cursor_actual:
                pygame.mouse.set_cursor(cursor)
                self.cursor_actual = cursor
            pygame.display.flip()
            clock.tick(60)
