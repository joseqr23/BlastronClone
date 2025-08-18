# main.py
import sys
import traceback
import pygame
from utils.paths import resource_path
from ui.menu import Menu

# --- Intenta leer settings, usa defaults si no están ---
try:
    from settings import SCREEN_WIDTH, SCREEN_HEIGHT, CAPTION, FPS
except Exception:
    SCREEN_WIDTH, SCREEN_HEIGHT, CAPTION, FPS = 800, 600, "Menú Principal", 60

# Audio de baja latencia (opcional) antes de pygame.init()
pygame.mixer.pre_init(44100, -16, 2, 512)

# --- Parches para recursos (solo en ejecutable/empacado) ---
def _patch_resource_loaders():
    if hasattr(sys, "_MEIPASS") or getattr(sys, "frozen", False):
        _orig_img = pygame.image.load
        _orig_snd = pygame.mixer.Sound
        _orig_font = pygame.font.Font

        def load_image_with_meipass(path, *args, **kwargs):
            return _orig_img(resource_path(path), *args, **kwargs)

        def load_sound_with_meipass(path, *args, **kwargs):
            return _orig_snd(resource_path(path), *args, **kwargs)

        def load_font_with_meipass(path, size, *args, **kwargs):
            # Permite Font(None, size) para la fuente por defecto del sistema
            if path is None:
                return _orig_font(None, size, *args, **kwargs)
            return _orig_font(resource_path(path), size, *args, **kwargs)

        pygame.image.load = load_image_with_meipass
        pygame.mixer.Sound = load_sound_with_meipass
        pygame.font.Font = load_font_with_meipass

def main():
    pygame.init()
    try:
        pygame.mixer.init()
    except pygame.error:
        # Continúa sin audio si no hay dispositivo/permiso
        pass

    screen = pygame.display.set_mode(
        (SCREEN_WIDTH, SCREEN_HEIGHT),
        pygame.SCALED | pygame.RESIZABLE
    )
    pygame.display.set_caption(CAPTION)

    # --- Menú principal ---
    menu = Menu(screen)
    seleccion = menu.run()
    if not seleccion:
        pygame.quit()
        sys.exit()

    modo_map = {
        "Modo Solo": "solo",
        "Modo Multijugador": "multiplayer",
        "Modo Libre": "free"
    }

    modo = modo_map.get(seleccion.get("modo"))
    nombre_jugador = seleccion.get("nombre") or "Jugador"
    personaje = seleccion.get("personaje") or "robot"

    # --- Selección de Game según modo ---
    if modo == "solo":
        from core.game_modes.solo_game import SoloGame as Game
    elif modo == "multiplayer":
        # Asegúrate que en multi_game.py la clase se llame EXACTAMENTE MultiplayerGame
        from core.game_modes.multi_game import MultiplayerGame as Game
    elif modo == "free":
        from core.game_modes.free_game import FreeGame as Game
    else:
        # Modo inválido o cancelado
        pygame.quit()
        sys.exit()

    # Si tus Game esperan screen primero, usa esta línea:
    # juego = Game(screen, nombre_jugador, personaje)
    juego = Game(nombre_jugador, personaje)

    # --- Ejecuta el juego ---
    try:
        juego.run()
    finally:
        pygame.quit()

if __name__ == "__main__":
    _patch_resource_loaders()
    try:
        main()
    except Exception:
        # Loguea el traceback (útil en ejecutable)
        traceback.print_exc()
        pygame.quit()
        sys.exit(1)
