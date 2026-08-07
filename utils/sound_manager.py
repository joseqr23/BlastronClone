# utils/sound_manager.py
"""
Punto único para reproducir efectos de sonido y música de fondo.

Uso:
    from utils.sound_manager import sound_manager
    sound_manager.salto()
    sound_manager.dano()
    sound_manager.disparo("granada")   # o "misil"
    sound_manager.explosion()
    sound_manager.iniciar_musica()

Cada sonido se carga de forma PEREZOSA (la primera vez que se reproduce,
no al importar el módulo). Esto evita cualquier problema de orden de
inicialización con pygame.init()/pygame.mixer — para cuando el juego
realmente reproduce un sonido, pygame ya está inicializado.

Estructura de archivos esperada en assets/sfx/:
    assets/sfx/musica.mp3
    assets/sfx/salto/salto1.mp3, salto2.mp3, salto3.mp3
    assets/sfx/dano/dano1.mp3, dano2.mp3, dano3.mp3
    assets/sfx/disparo_granada.mp3
    assets/sfx/disparo_misil.mp3
    assets/sfx/explosion.mp3

Si algún archivo no existe, se imprime un aviso en consola y el juego
sigue funcionando sin ese sonido (no revienta).
"""
import random
import pygame
from utils.paths import resource_path


class SoundManager:
    def __init__(self):
        self.habilitado = True
        self._cache = {}

    def _cargar(self, ruta):
        if ruta in self._cache:
            return self._cache[ruta]
        sonido = None
        try:
            sonido = pygame.mixer.Sound(resource_path(ruta))
        except Exception as e:
            print(f"[Sound] No se pudo cargar '{ruta}': {e}")
        self._cache[ruta] = sonido
        return sonido

    def _reproducir(self, ruta, volumen=1.0):
        if not self.habilitado:
            return
        sonido = self._cargar(ruta)
        if sonido:
            sonido.set_volume(volumen)
            sonido.play()

    # --- Efectos con variantes aleatorias ---
    def salto(self):
        ruta = random.choice([
            "assets/sfx/salto/salto1.mp3",
            "assets/sfx/salto/salto2.mp3",
            "assets/sfx/salto/salto3.mp3",
        ])
        self._reproducir(ruta, 0.1)

    def dano(self):
        ruta = random.choice([
            "assets/sfx/dano/dano1.mp3",
            "assets/sfx/dano/dano2.mp3",
            "assets/sfx/dano/dano3.mp3",
        ])
        self._reproducir(ruta, 0.1)

    def muerte(self):
        ruta = random.choice([
            "assets/sfx/death/death1.mp3",
            "assets/sfx/death/death2.mp3",
            "assets/sfx/death/death3.mp3",
        ])
        self._reproducir(ruta, 0.2)

    # --- Efectos por arma (una carpeta por arma, dos sonidos cada una) ---
    def disparo(self, arma):
        """arma: 'granada', 'misil', o el nombre de cualquier arma futura —
        busca assets/sfx/weapons/<arma>/disparo.mp3."""
        self._reproducir(f"assets/sfx/weapons/{arma}/disparo.mp3", 0.1)

    def explosion(self, arma="granada"):
        """arma: 'granada', 'misil', o el nombre de cualquier arma futura —
        busca assets/sfx/weapons/<arma>/explosion.mp3."""
        self._reproducir(f"assets/sfx/weapons/{arma}/explosion.mp3", 0.1)

    # Efectos para modo basket
    def puntos_anotados(self):
        """Será instanciado cada que alguien anota puntos."""
        self._reproducir(f"assets/sfx/basket/puntos_anotados.mp3", 0.1)

    def rebote(self, ruta=None):
        """Sonido de rebote contra algo. 'ruta' permite pasar un
        archivo específico (ej. el rebote.mp3 propio de un mapa, ver
        Proyectil._reproducir_rebote); si no se pasa, usa un genérico."""
        ruta = random.choice([
            "assets/sfx/basket/rebote_basket_1.mp3",
            "assets/sfx/basket/rebote_basket_2.mp3",
            "assets/sfx/basket/rebote_basket_3.mp3",
        ])
        self._reproducir(ruta, 0.5)

    # --- Música de fondo ---
    def iniciar_musica(self, ruta="assets/sfx/musica.mp3", volumen=0.1):
        if not self.habilitado:
            return
        try:
            pygame.mixer.music.load(resource_path(ruta))
            pygame.mixer.music.set_volume(volumen)
            pygame.mixer.music.play(loops=-1)  # loop infinito
        except Exception as e:
            print(f"[Sound] No se pudo cargar música '{ruta}': {e}")

    def detener_musica(self):
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass

    # Mutea música
    def alternar_mute(self):
        """Alterna silencio general: pausa/reanuda la música de fondo Y
        evita que se reproduzcan nuevos efectos mientras esté muteado
        (los que ya sonaron, terminan solos)."""
        self.habilitado = not self.habilitado
        try:
            if not self.habilitado:
                pygame.mixer.music.pause()
            else:
                pygame.mixer.music.unpause()
        except Exception:
            pass
        return self.habilitado


# Instancia única compartida por todo el juego.
sound_manager = SoundManager()