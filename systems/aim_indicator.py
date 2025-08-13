import pygame
import math

class AimIndicator:
    def __init__(self, origen, max_fuerza=120): # CAMBIAR LONGITUD DE FLECHA
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

    def get_fuerza(self):
        return math.hypot(*self.direccion)

    def get_angulo(self):
        return math.atan2(self.direccion[1], self.direccion[0])

    def get_punta(self):
        """Devuelve la punta de la flecha"""
        return (self.origen[0] + self.direccion[0], self.origen[1] + self.direccion[1])

    def get_datos_disparo(self, ancho_proyectil=0, alto_proyectil=0):
        """
        Devuelve:
        - posición inicial (ajustada para que el centro del proyectil coincida con el origen)
        - velocidad en X
        - velocidad en Y
        """
        angulo = self.get_angulo()
        velocidad = self.get_fuerza() / self.max_fuerza * 25

        vel_x = math.cos(angulo) * velocidad
        vel_y = math.sin(angulo) * velocidad

        # Ajuste para que el proyectil esté centrado visualmente
        origen_ajustado = (
            self.origen[0] - ancho_proyectil / 2,
            self.origen[1] - alto_proyectil / 2
        )

        return origen_ajustado, vel_x, vel_y
    def draw(self, pantalla):
        punta = self.get_punta()
        distancia = self.get_fuerza()

        # Color invertido: rojo = poca fuerza, verde = mucha fuerza
        porcentaje = distancia / self.max_fuerza
        color = (
            int(255 * (1 - porcentaje)),  # Rojo fuerte si fuerza baja
            int(255 * porcentaje),        # Verde fuerte si fuerza alta
            0
        )

        # Línea principal
        pygame.draw.line(pantalla, color, self.origen, punta, 6)

        # Punta de flecha
        angulo = self.get_angulo()
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
