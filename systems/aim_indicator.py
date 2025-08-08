# systems/aim_indicator.py
import pygame
import math

class AimIndicator:
    def __init__(self, origen, max_fuerza=150):
        self.origen = origen
        self.max_fuerza = max_fuerza
        self.direccion = (0, 0)

    def update(self, mouse_pos):
        dx = mouse_pos[0] - self.origen[0]
        dy = mouse_pos[1] - self.origen[1]
        distancia = math.hypot(dx, dy)

        if distancia > self.max_fuerza:
            escala = self.max_fuerza / distancia
            dx *= escala
            dy *= escala

        self.direccion = (dx, dy)

    def draw(self, pantalla):
        punta = (self.origen[0] + self.direccion[0], self.origen[1] + self.direccion[1])
        distancia = math.hypot(*self.direccion)

        # Color de rojo (baja fuerza) a verde (alta fuerza)
        porcentaje = distancia / self.max_fuerza
        color = (
            int(255 * (1 - porcentaje)),  # Rojo más fuerte si fuerza es baja
            int(255 * porcentaje),        # Verde más fuerte si fuerza es alta
            0
        )

        # Línea principal
        pygame.draw.line(pantalla, color, self.origen, punta, 6)

        # Punta de flecha
        angulo = math.atan2(self.direccion[1], self.direccion[0])
        tamaño_punta = 12
        izquierda = (
            punta[0] - tamaño_punta * math.cos(angulo - math.pi / 6),
            punta[1] - tamaño_punta * math.sin(angulo - math.pi / 6)
        )
        derecha = (
            punta[0] - tamaño_punta * math.cos(angulo + math.pi / 6),
            punta[1] - tamaño_punta * math.sin(angulo + math.pi / 6)
        )
        pygame.draw.polygon(pantalla, color, [punta, izquierda, derecha])
