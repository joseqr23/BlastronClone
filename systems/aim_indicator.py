# systems/aim_indicator.py
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

    def get_datos_disparo(self, ancho_proyectil=0, alto_proyectil=0,  distancia_spawn=0, velocidad_fija=None):
        """
        Devuelve:
        - posición inicial (ajustada para que el centro del proyectil coincida
          con el punto de aparición)
        - velocidad en X
        - velocidad en Y

        distancia_spawn: cuántos píxeles alejar el punto de aparición del
        centro del jugador, EN LA DIRECCIÓN APUNTADA, antes de calcular la
        posición. Por defecto 0 — mantiene el comportamiento de siempre
        (proyectil nace justo en el centro del jugador, como granada/misil,
        que se alejan solos gracias a su velocidad). Para armas que no
        vuelan (cuerpo a cuerpo), pasa un valor > 0 para que el arma
        aparezca a un costado del jugador según hacia dónde apunte, en vez
        de quedarse centrada en él.

        velocidad_fija: si se define (no None), la velocidad de salida
        del proyectil es CONSTANTE con ese valor, ignorando cuánto
        arrastraste el mouse (fuerza) — solo se usa el ÁNGULO de
        apuntado para la dirección. Pensado para armas tipo escopeta,
        que deben salir siempre a máxima velocidad sin importar el
        "estirón" del aim.
        """
        angulo = self.get_angulo()
        if velocidad_fija is not None:
            velocidad = velocidad_fija
        else:
            velocidad = self.get_fuerza() / self.max_fuerza * 25
        vel_x = math.cos(angulo) * velocidad
        vel_y = math.sin(angulo) * velocidad

        centro_x = self.origen[0] + math.cos(angulo) * distancia_spawn
        centro_y = self.origen[1] + math.sin(angulo) * distancia_spawn

        origen_ajustado = (
            centro_x - ancho_proyectil / 2,
            centro_y - alto_proyectil / 2
        )
        return origen_ajustado, vel_x, vel_y

    def draw(self, pantalla, estilo="apuntar"):
        if estilo == "golpe":
            self._draw_golpe(pantalla)
            return

        punta = self.get_punta()
        distancia = self.get_fuerza()

        porcentaje = distancia / self.max_fuerza
        color = (
            int(255 * (1 - porcentaje)),
            int(255 * porcentaje),
            0
        )

        pygame.draw.line(pantalla, color, self.origen, punta, 6)

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

    def _draw_golpe(self, pantalla, longitud=45, color=(255, 120, 0)):
        """Mira alternativa para cuerpo a cuerpo: línea corta y FIJA en
        la dirección de apuntado (no depende de cuánto arrastres el
        mouse, a diferencia de 'apuntar') — solo cosmético, no cambia
        nada de la física del golpe."""
        angulo = self.get_angulo()
        punta = (
            self.origen[0] + math.cos(angulo) * longitud,
            self.origen[1] + math.sin(angulo) * longitud,
        )
        pygame.draw.line(pantalla, color, self.origen, punta, 8)
        tamaño_punta = 10
        izquierda = (
            punta[0] - tamaño_punta * math.cos(angulo - math.pi / 6),
            punta[1] - tamaño_punta * math.sin(angulo - math.pi / 6)
        )
        derecha = (
            punta[0] - tamaño_punta * math.cos(angulo + math.pi / 6),
            punta[1] - tamaño_punta * math.sin(angulo + math.pi / 6)
        )
        pygame.draw.polygon(pantalla, color, [punta, izquierda, derecha])

    def draw_arma_sostenida(self, pantalla, imagen, mouse_pos, posicion_x=0, posicion_y=0):
        """Dibuja weapon.png (si el arma equipada tiene uno) rotado hacia
        el mouse y reflejado si apunta a la izquierda. posicion_x/y
        definen un punto de anclaje relativo al robot CUANDO EL ARMA
        APUNTA HORIZONTAL (ángulo 0) — posicion_x se espeja según hacia
        qué lado apunta, posicion_y no. Ese offset se rota junto con el
        ángulo real de apuntado, para que el punto de anclaje se
        mantenga "pegado" al arma en vez de quedarse fijo en una
        dirección mientras la imagen gira (lo que la hacía verse
        flotando al apuntar hacia arriba/abajo). Usa la dirección
        COMPLETA hacia el mouse (no la recortada por max_fuerza como la
        flecha). Si imagen es None, no dibuja nada."""
        if imagen is None:
            return
        dx = mouse_pos[0] - self.origen[0]
        dy = mouse_pos[1] - self.origen[1]
        angulo = math.degrees(math.atan2(-dy, dx))
        direccion = 1 if dx >= 0 else -1
        frame = imagen
        if dx < 0:
            frame = pygame.transform.flip(imagen, True, False)
            angulo += 180
        imagen_rotada = pygame.transform.rotozoom(frame, angulo, 1)

        angulo_rad = math.radians(angulo)
        ox = posicion_x * direccion
        oy = posicion_y
        offset_x = ox * math.cos(angulo_rad) + oy * math.sin(angulo_rad)
        offset_y = -ox * math.sin(angulo_rad) + oy * math.cos(angulo_rad)

        centro = (self.origen[0] + offset_x, self.origen[1] + offset_y)
        rect = imagen_rotada.get_rect(center=centro)
        pantalla.blit(imagen_rotada, rect.topleft)