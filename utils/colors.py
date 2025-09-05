class ColorManager:
    colores_disponibles = [
        (0, 0, 255),     # Azul
        (0, 200, 0),     # Verde
        (200, 0, 0),     # Rojo
        (255, 140, 0),   # Naranja
        (128, 0, 128),   # Morado
        (255, 255, 0),   # Amarillo (extra)
        (0, 255, 255),   # Cyan (extra)
        (255, 0, 255),   # Fucsia (extra)
    ]
    asignados = {}   # nombre_jugador -> color
    usados = set()

    @classmethod
    def get_color(cls, nombre_jugador):
        # Si ya tenía color, lo devuelve
        if nombre_jugador in cls.asignados:
            return cls.asignados[nombre_jugador]

        # Buscar el primer color libre
        for c in cls.colores_disponibles:
            if c not in cls.usados:
                cls.usados.add(c)
                cls.asignados[nombre_jugador] = c
                return c

        # Si todos están ocupados → asignar con round-robin
        idx = len(cls.asignados) % len(cls.colores_disponibles)
        c = cls.colores_disponibles[idx]
        cls.asignados[nombre_jugador] = c
        return c
