import pygame

class HUDArmas:
    def __init__(self, armas_disponibles, posicion=(10, 10)):
        self.armas = ['nada'] + armas_disponibles  # Insertamos "nada" al inicio
        self.pos = posicion
        self.seleccion = 'nada'  # Por defecto sin arma equipada
        self.botones = []
        self.imagenes = {}  # Aquí guardaremos las imágenes
        self.crear_botones()
        self.cargar_imagenes()

    def crear_botones(self):
        x, y = self.pos
        ancho = 60
        alto = 60
        padding = 10
        self.botones = []
        for i, arma in enumerate(self.armas):
            rect = pygame.Rect(x + i*(ancho + padding), y, ancho, alto)
            self.botones.append((arma, rect))

    def cargar_imagenes(self):
        for arma in self.armas:
            try:
                ruta_img = f"assets/hud/{arma}.png"
                imagen = pygame.image.load(ruta_img).convert_alpha()
                # Escalamos la imagen para que quepa bien en el botón (ej: 40x40 px)
                imagen = pygame.transform.smoothscale(imagen, (40, 40))
                self.imagenes[arma] = imagen
            except Exception as e:
                print(f"No se pudo cargar imagen para {arma}: {e}")
                self.imagenes[arma] = None

    def manejar_evento(self, evento):
        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            pos = evento.pos
            for arma, rect in self.botones:
                if rect.collidepoint(pos):
                    self.seleccion = arma
                    return arma
        return None

    def draw(self, pantalla, font):
        for arma, rect in self.botones:
            color = (0, 200, 0) if self.seleccion == arma else (150, 150, 150)
            pygame.draw.rect(pantalla, color, rect)

            imagen = self.imagenes.get(arma)
            if imagen:
                img_rect = imagen.get_rect(center=rect.center)
                pantalla.blit(imagen, img_rect)
            else:
                # Si no hay imagen, muestra texto de fallback
                texto_mostrar = arma.capitalize() if arma != 'nada' else 'Ninguna'
                text = font.render(texto_mostrar, True, (0, 0, 0))
                text_rect = text.get_rect(center=rect.center)
                pantalla.blit(text, text_rect)
