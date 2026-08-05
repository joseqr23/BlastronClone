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

    def draw(self, pantalla, estilo="apuntar", config=None):
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
        if config is not None:
            self._draw_trayectoria(pantalla, config)

    def _draw_golpe(self, pantalla, longitud=60, tamaño=15, grosor=4, color=(255, 255, 255)):
        """Mira alternativa para cuerpo a cuerpo: un recuadro tipo mira
        de cámara '[ ]' ubicado a una distancia fija en la dirección de
        apuntado, en vez de la flecha con gradiente de fuerza. Puramente
        cosmético — no cambia nada de la física del golpe."""
        angulo = self.get_angulo()
        cx = self.origen[0] + math.cos(angulo) * longitud
        cy = self.origen[1] + math.sin(angulo) * longitud

        mitad = tamaño / 2
        x0, y0 = cx - mitad, cy - mitad
        x1, y1 = cx + mitad, cy + mitad
        brazo = tamaño * 0.35

        # Esquina superior izquierda
        pygame.draw.line(pantalla, color, (x0, y0), (x0 + brazo, y0), grosor)
        pygame.draw.line(pantalla, color, (x0, y0), (x0, y0 + brazo), grosor)
        # Esquina superior derecha
        pygame.draw.line(pantalla, color, (x1, y0), (x1 - brazo, y0), grosor)
        pygame.draw.line(pantalla, color, (x1, y0), (x1, y0 + brazo), grosor)
        # Esquina inferior izquierda
        pygame.draw.line(pantalla, color, (x0, y1), (x0 + brazo, y1), grosor)
        pygame.draw.line(pantalla, color, (x0, y1), (x0, y1 - brazo), grosor)
        # Esquina inferior derecha
        pygame.draw.line(pantalla, color, (x1, y1), (x1 - brazo, y1), grosor)
        pygame.draw.line(pantalla, color, (x1, y1), (x1, y1 - brazo), grosor)

    def _draw_trayectoria(self, pantalla, config, cantidad_puntos=7, intervalo_frames=2, radio=5, color=(255, 255, 255)):
        """Puntos que muestran el arco real por el que va a caer el
        proyectil — misma integración que Proyectil.update() (gravedad,
        posición, fricción de aire, en ese orden). No contempla colisión
        con tiles/robots: es el arco de vuelo libre, se corta solo si sale
        de la pantalla por abajo."""
        ancho = config.get("ancho_proyectil", 40)
        alto = config.get("alto_proyectil", 40)
        origen, vel_x, vel_y = self.get_datos_disparo(ancho, alto, velocidad_fija=config.get("velocidad_proyectil"))
        x, y = origen[0] + ancho / 2, origen[1] + alto / 2
        gravedad = config.get("gravedad", 0.5)
        friccion_aire = config.get("friccion_aire", 0.99)
        limite_y = pantalla.get_height()

        for i in range(cantidad_puntos):
            for _ in range(intervalo_frames):
                vel_y += gravedad
                x += vel_x
                y += vel_y
                vel_x *= friccion_aire
            if y > limite_y:
                break
            pygame.draw.circle(pantalla, color, (int(x), int(y)), max(2, radio - i // 2))

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