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
    asignados = {}   # nombre_jugador -> color, para esta partida
    usados = set()   # colores ya entregados en esta partida

    @classmethod
    def get_color(cls, nombre_jugador: str):
        """Asigna a cada jugador el PRIMER color libre de la lista, y lo
        recuerda para que siempre devuelva el mismo color mientras dure
        la partida. Dos jugadores distintos nunca reciben el mismo color
        mientras queden colores libres. Si algún día hay más jugadores
        que colores predefinidos, cae al hash determinista de siempre
        como último recurso (puede repetirse, pero es un caso extremo)."""
        if not nombre_jugador:
            return cls.colores_disponibles[0]
        if nombre_jugador in cls.asignados:
            return cls.asignados[nombre_jugador]
        for color in cls.colores_disponibles:
            if color not in cls.usados:
                cls.asignados[nombre_jugador] = color
                cls.usados.add(color)
                return color
        # Ya no quedan colores libres — fallback determinista de siempre.
        h = int(hashlib.md5(nombre_jugador.encode("utf-8")).hexdigest(), 16)
        idx = h % len(cls.colores_disponibles)
        color = cls.colores_disponibles[idx]
        cls.asignados[nombre_jugador] = color
        return color

    @classmethod
    def liberar(cls, nombre_jugador: str):
        """Libera el color de un jugador (ej. al desconectarse), para
        que quede disponible para alguien más en la misma partida."""
        color = cls.asignados.pop(nombre_jugador, None)
        if color is not None:
            cls.usados.discard(color)

    @classmethod
    def reset(cls):
        """Limpia todas las asignaciones — llamar al INICIO de cada
        partida nueva, para no arrastrar colores de una partida
        anterior (ColorManager es compartido mientras el proceso siga
        corriendo, ej. si vuelves al menú y empiezas otra partida)."""
        cls.asignados = {}
        cls.usados = set()