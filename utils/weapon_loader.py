# utils/weapon_loader.py
"""
Descubrimiento dinámico de armas — mismo patrón que usas para personajes
(una carpeta por arma, un archivo de datos que la define).

Estructura esperada:
    assets/weapons/<arma>/config.json
    assets/weapons/<arma>/sprite.png

Para agregar un arma nueva normalmente NO hace falta tocar ningún .py:
    1. Crea assets/weapons/<arma>/config.json (copia uno existente y
       cambia los valores).
    2. Pon assets/weapons/<arma>/sprite.png (spritesheet horizontal con
       la cantidad de frames que indiques en "frames"). Puede tener
       CUALQUIER resolución — cada frame se recorta con su tamaño real
       (ancho_total_de_la_imagen / frames) y luego se escala al tamaño
       lógico que definas en "ancho"/"alto" del JSON. Es decir: "ancho" y
       "alto" ya NO tienen que coincidir con los píxeles reales del PNG.
    3. Opcional: assets/sfx/weapons/<arma>/disparo.mp3 y explosion.mp3.

Campos de config.json:
    nombre                 (str)  solo informativo
    comportamiento         (str)  "rebote" | "impacto" | "mina" — ver
                                   entities/weapons/proyectil.py
    daño                   (int)
    ancho, alto             (int)  tamaño LÓGICO del proyectil (display +
                                   hitbox base). No necesita coincidir con
                                   el tamaño real del sprite — se escala
                                   automáticamente.
    gravedad                (float)
    friccion_aire            (float)
    friccion_rebote           (float) solo relevante si comportamiento="rebote"
    radio_proximidad           (int)  solo relevante si comportamiento="mina"
    tiempo_explosion_ms        (int)  cuánto tarda en detonar si no impacta antes
                                       (ignorado si comportamiento="mina")
    tiempo_post_explosion_ms    (int)  cuánto dura la animación de explosión
    margen_dueño_ms              (int)  tiempo tras el disparo en que el arma
                                        ignora a su propio dueño (para no
                                        autodetonarse al salir)
    hitbox_padding_x/_y            (int)  margen extra del área de daño
    sprite                          (str)  ruta al spritesheet
    frames                          (int)  cantidad de frames en el spritesheet
                                           (por convención: 0=idle, 1=warning,
                                           2=explode — igual que granada/misil)
"""
import os
import json
import pygame
from utils.loader import load_spritesheet

_CACHE = None


def _cargar_frames_escalados(sprite_path, frames, ancho_deseado, alto_deseado):
    """Recorta cada frame usando el tamaño REAL que tiene en el spritesheet
    (ancho_total_de_la_imagen / frames, alto_total_de_la_imagen), y luego
    lo escala al tamaño lógico pedido en el JSON. Así el arte puede tener
    cualquier resolución y el JSON controla el tamaño del arma en el juego
    sin romper el recorte del spritesheet."""
    hoja = pygame.image.load(sprite_path).convert_alpha()
    ancho_frame_real = hoja.get_width() // frames
    alto_frame_real = hoja.get_height()

    frames_recortados = load_spritesheet(sprite_path, frames, ancho_frame_real, alto_frame_real)

    if (ancho_frame_real, alto_frame_real) == (ancho_deseado, alto_deseado):
        return frames_recortados

    return [
        pygame.transform.smoothscale(frame, (ancho_deseado, alto_deseado))
        for frame in frames_recortados
    ]


def cargar_armas(forzar_recarga=False):
    """Devuelve {arma_id: config_dict} escaneando assets/weapons/. Se
    cachea tras la primera llamada — pasa forzar_recarga=True si agregas
    un arma nueva en caliente (raro, normalmente se llama una sola vez al
    iniciar el juego)."""
    global _CACHE
    if _CACHE is not None and not forzar_recarga:
        return _CACHE

    base = "assets/weapons"
    armas = {}
    if not os.path.isdir(base):
        print(f"[Armas] No existe la carpeta '{base}'")
        _CACHE = armas
        return armas

    for nombre in sorted(os.listdir(base)):
        carpeta = os.path.join(base, nombre)
        config_path = os.path.join(carpeta, "config.json")
        if not os.path.isdir(carpeta) or not os.path.isfile(config_path):
            continue
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception as e:
            print(f"[Armas] No se pudo leer '{config_path}': {e}")
            continue

        config.setdefault("id", nombre)
        sprite_path = config.get("sprite", os.path.join(carpeta, "sprite.png"))
        frames = config.get("frames", 3)
        ancho = config.get("ancho", 40)   # tamaño lógico deseado (display + hitbox)
        alto = config.get("alto", 40)
        try:
            config["_frames_img"] = _cargar_frames_escalados(sprite_path, frames, ancho, alto)
        except Exception as e:
            print(f"[Armas] No se pudo cargar el sprite de '{nombre}' ({sprite_path}): {e}")
            config["_frames_img"] = []

        armas[nombre] = config

    _CACHE = armas
    return armas


def config_arma(arma_id):
    return cargar_armas().get(arma_id)