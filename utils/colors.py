# utils/colors.py
import hashlib

class ColorManager:
    colores_disponibles = [
        (0, 0, 255),     # Azul
        (0, 200, 0),     # Verde
        (200, 0, 0),     # Rojo
        (255, 140, 0),   # Naranja
        (128, 0, 128),   # Morado
        (255, 255, 0),   # Amarillo
        (0, 255, 255),   # Cyan
        (255, 0, 255),   # Fucsia
    ]
    asignados = {}   # (opcional, no usado por la función determinista)
    usados = set()

    @classmethod
    def get_color(cls, nombre_jugador: str):
        """
        Asigna un color de forma determinista a partir del nombre.
        Usa md5(nombre) % len(colores) para que el resultado sea igual
        en todos los procesos y ejecuciones.
        """
        if not nombre_jugador:
            return cls.colores_disponibles[0]
        # md5 para estabilidad entre procesos
        h = int(hashlib.md5(nombre_jugador.encode("utf-8")).hexdigest(), 16)
        idx = h % len(cls.colores_disponibles)
        return cls.colores_disponibles[idx]
