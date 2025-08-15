# core/ui/chat.py
import pygame

class Chat:
    COLORES_NOMBRES = [
        (0, 0, 255),     # Azul
        (0, 200, 0),     # Verde
        (200, 0, 0),     # Rojo
        (255, 140, 0),   # Naranja
        (128, 0, 128),   # Morado
    ]

    def __init__(self, nombre_jugador, posicion=(10, 410), ancho=300, alto=80):
        self.nombre_jugador = nombre_jugador
        self.posicion = posicion
        self.ancho = ancho
        self.alto = alto
        self.mensajes = []  # ahora guardamos todos los mensajes
        self.font = pygame.font.SysFont("Arial", 16)
        self.color_fondo = (0, 0, 0, 150)  # Negro semi-transparente
        self.color_texto = (255, 255, 255)
        self.color_nombre = self.COLORES_NOMBRES[hash(nombre_jugador) % len(self.COLORES_NOMBRES)]
        self.input_text = ""
        self.activo = False
        self.scroll_offset = 0  # para movernos en el historial

    def agregar_mensaje(self, texto):
        """Agrega un mensaje al historial."""
        self.mensajes.append(texto)
        self.scroll_offset = 0  # volver al final cuando hay mensaje nuevo

    def lineas_visibles(self):
        """Cantidad de líneas que caben en el chat."""
        return (self.alto - 25) // 18

    def draw(self, pantalla):
        """Dibuja el chat y la caja de entrada."""
        surface = pygame.Surface((self.ancho, self.alto), pygame.SRCALPHA)
        surface.fill(self.color_fondo)
        pantalla.blit(surface, self.posicion)

        # Calcular mensajes visibles según el scroll
        max_lineas = self.lineas_visibles()
        inicio = max(0, len(self.mensajes) - max_lineas - self.scroll_offset)
        fin = inicio + max_lineas
        mensajes_a_mostrar = self.mensajes[inicio:fin]

        y_offset = 5
        for mensaje in mensajes_a_mostrar:
            if ": " in mensaje:
                nombre, texto = mensaje.split(": ", 1)
                color_nombre = self.COLORES_NOMBRES[hash(nombre) % len(self.COLORES_NOMBRES)]
                render_nombre = self.font.render(nombre + ": ", True, color_nombre)
                pantalla.blit(render_nombre, (self.posicion[0] + 5, self.posicion[1] + y_offset))

                render_texto = self.font.render(texto, True, self.color_texto)
                pantalla.blit(render_texto, (self.posicion[0] + 5 + render_nombre.get_width(), self.posicion[1] + y_offset))
            else:
                render = self.font.render(mensaje, True, self.color_texto)
                pantalla.blit(render, (self.posicion[0] + 5, self.posicion[1] + y_offset))
            y_offset += 18

        if self.activo:
            input_render = self.font.render("Decir: " + self.input_text, True, self.color_texto)
            pantalla.blit(input_render, (self.posicion[0] + 5, self.posicion[1] + self.alto - 20))

    def handle_event(self, evento):
        """Maneja eventos de teclado y scroll."""
        if evento.type == pygame.KEYDOWN:
            if evento.key == pygame.K_RETURN:
                if self.activo:
                    if self.input_text.strip():
                        mensaje_formateado = f"{self.nombre_jugador}: {self.input_text.strip()}"
                        self.agregar_mensaje(mensaje_formateado)
                    self.input_text = ""
                    self.activo = False
                else:
                    self.activo = True

            elif self.activo:
                if evento.key == pygame.K_BACKSPACE:
                    self.input_text = self.input_text[:-1]
                else:
                    if evento.unicode.isprintable():
                        self.input_text += evento.unicode
            else:
                # Scroll con teclado
                if evento.key == pygame.K_PAGEUP:
                    self.scroll_offset = min(self.scroll_offset + 1, max(0, len(self.mensajes) - self.lineas_visibles()))
                elif evento.key == pygame.K_PAGEDOWN:
                    self.scroll_offset = max(self.scroll_offset - 1, 0)

        elif evento.type == pygame.MOUSEBUTTONDOWN and not self.activo:
            if evento.button == 4:  # Rueda hacia arriba
                self.scroll_offset = min(self.scroll_offset + 1, max(0, len(self.mensajes) - self.lineas_visibles()))
            elif evento.button == 5:  # Rueda hacia abajo
                self.scroll_offset = max(self.scroll_offset - 1, 0)
