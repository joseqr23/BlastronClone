# main.py
import sys
import pygame
from utils.paths import resource_path
from ui.menu import Menu

# --- Parches para recursos ---
_original_image_load = pygame.image.load
_original_sound = pygame.mixer.Sound
_original_font = pygame.font.Font

def load_image_with_meipass(path, *args, **kwargs):
    return _original_image_load(resource_path(path), *args, **kwargs)

def load_sound_with_meipass(path, *args, **kwargs):
    return _original_sound(resource_path(path), *args, **kwargs)

def load_font_with_meipass(path, size):
    return _original_font(resource_path(path), size)

pygame.image.load = load_image_with_meipass
pygame.mixer.Sound = load_sound_with_meipass
pygame.font.Font = load_font_with_meipass

# --- Inicio del programa ---
if __name__ == "__main__":
    pygame.init()

    pantalla = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("Menú Principal")

    menu = Menu(pantalla)
    seleccion = menu.run()

    modo_map = {
        "Modo Solo": "solo",
        "Modo Multijugador": "multiplayer",
        "Modo Libre": "free"
    }
    modo = modo_map[seleccion["modo"]]
    nombre_jugador = seleccion["nombre"]
    personaje = seleccion["personaje"]

    if modo == "solo":
        from core.game_modes.solo_game import SoloGame as Game
    elif modo == "multiplayer":
        from core.game_modes.multi_game import MultiplayerGame as Game
    elif modo == "free":
        from core.game_modes.free_game import FreeGame as Game
    else:
        print("Modo no válido, saliendo...")
        pygame.quit()
        sys.exit()

    juego = Game(nombre_jugador, personaje)
    juego.run()
