# main.py
import sys
import pygame
from utils.paths import resource_path  # función para rutas correctas

# Guardar funciones originales de pygame
_original_image_load = pygame.image.load
_original_sound = pygame.mixer.Sound
_original_font = pygame.font.Font

# Parche para imágenes
def load_image_with_meipass(path, *args, **kwargs):
    return _original_image_load(resource_path(path), *args, **kwargs)

# Parche para sonidos
def load_sound_with_meipass(path, *args, **kwargs):
    return _original_sound(resource_path(path), *args, **kwargs)

# Parche para fuentes
def load_font_with_meipass(path, size):
    return _original_font(resource_path(path), size)

# Aplicar parches globales
pygame.image.load = load_image_with_meipass
pygame.mixer.Sound = load_sound_with_meipass
pygame.font.Font = load_font_with_meipass

# Ahora importamos el juego después de aplicar los parches
from core.game import Game

if __name__ == "__main__":
    juego = Game()
    juego.run()
