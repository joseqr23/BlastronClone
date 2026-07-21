# ui/hud.py
import pygame
from entities.players.robot import Robot


def _draw_crown(pantalla, x, y, size=14, color=(255, 215, 0)):
    """Dibuja una corona simple (sin depender de ninguna imagen) junto al
    primer lugar del marcador de puntajes."""
    base_y = y + size
    puntos = [
        (x, base_y),
        (x, y + size * 0.4),
        (x + size * 0.25, y + size * 0.7),
        (x + size * 0.5, y),
        (x + size * 0.75, y + size * 0.7),
        (x + size, y + size * 0.4),
        (x + size, base_y),
    ]
    pygame.draw.polygon(pantalla, color, puntos)
    pygame.draw.polygon(pantalla, (150, 110, 0), puntos, width=1)


class HUDArmas:
    def __init__(self, armas_disponibles, posicion=(700, 10)):
        self.armas = ['nada'] + armas_disponibles + ['spawn_robot']
        self.pos = posicion
        self.seleccion = 'nada'
        self.botones = []
        self.imagenes = {}
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
                texto_mostrar = arma.capitalize() if arma != 'nada' else 'Ninguna'
                text = font.render(texto_mostrar, True, (0, 0, 0))
                text_rect = text.get_rect(center=rect.center)
                pantalla.blit(text, text_rect)


class HUDPuntajes:
    """Marcador de puntajes para el modo libre. Ordenado de mayor a menor;
    el primer lugar siempre lleva una corona al lado del nombre."""

    def __init__(self, game, posicion=(10, 10)):
        self.game = game
        self.pos = posicion
        self.font = pygame.font.SysFont("Arial", 17, bold=True)
        self.font_title = pygame.font.SysFont("Arial", 20, bold=True)

    def _entradas(self):
        entradas = [(
            self.game.robot.nombre_jugador,
            self.game.puntajes.get(self.game.robot, 0),
            getattr(self.game.robot, "color_nombre", (0, 0, 0)),
        )]
        for robot in self.game.robots_estaticos:
            if not robot.is_dead:
                entradas.append((
                    robot.nombre_jugador,
                    self.game.puntajes.get(robot, 0),
                    getattr(robot, "color_nombre", (0, 0, 0)),
                ))
        entradas.sort(key=lambda e: e[1], reverse=True)
        return entradas

    def draw(self, pantalla):
        x, y = self.pos
        titulo = self.font_title.render("Puntuación", True, (0, 0, 0))
        pantalla.blit(titulo, (x, y))
        y += 25
        for i, (nombre, score, color) in enumerate(self._entradas()):
            text_x = x
            if i == 0:
                _draw_crown(pantalla, x, y - 2)
                text_x = x + 20
            texto = self.font.render(f"{nombre}: {score}", True, color)
            pantalla.blit(texto, (text_x, y))
            y += 20


class HUDPuntajesMultiplayer:
    """Marcador de puntajes para el modo multijugador. Ordenado de mayor a
    menor; el primer lugar siempre lleva una corona al lado del nombre."""

    def __init__(self, game, posicion=(10, 10)):
        self.game = game
        self.pos = posicion
        self.font = pygame.font.SysFont("Arial", 17, bold=True)
        self.font_title = pygame.font.SysFont("Arial", 20, bold=True)

    def _entradas(self):
        entradas = []
        for jugador, score in self.game.puntajes.items():
            if self.game.robot and self.game.robot.nombre_jugador == jugador:
                robot = self.game.robot
            else:
                robot = self.game.robots_remotos.get(jugador)
            color = getattr(robot, "color_nombre", (0, 0, 0)) if robot else (0, 0, 0)
            entradas.append((jugador, score, color))
        entradas.sort(key=lambda e: e[1], reverse=True)
        return entradas

    def draw(self, pantalla):
        x, y = self.pos
        titulo = self.font_title.render("Puntuación", True, (0, 0, 0))
        pantalla.blit(titulo, (x, y))
        y += 25
        for i, (jugador, score, color) in enumerate(self._entradas()):
            text_x = x
            if i == 0:
                _draw_crown(pantalla, x, y - 2)
                text_x = x + 20
            texto = self.font.render(f"{jugador}: {score}", True, color)
            pantalla.blit(texto, (text_x, y))
            y += 20


class HUDTimer:
    def __init__(self, game, duracion=180, posicion=(400, 10)):
        self.game = game
        self.duracion = duracion
        self.posicion = posicion
        self.font = pygame.font.SysFont("Arial", 26, bold=True)

    def draw(self, pantalla):
        restante = max(0, self.game.tiempo_restante)
        minutos = restante // 60
        segundos = restante % 60
        texto = f"{minutos:02}:{segundos:02}"
        if restante <= 10:
            color = (255, 0, 0)
        elif restante <= 30:
            color = (255, 165, 0)
        else:
            color = (0, 0, 0)
        render = self.font.render(texto, True, color)
        rect = render.get_rect(center=self.posicion)
        pantalla.blit(render, rect)


class HUDTurnos:
    """
    Colores según fase del turno:
      "turno"        -> amarillo   (puede moverse y disparar)
      "post_disparo" -> naranja    (ya disparó, solo puede moverse)
      "cooldown"     -> rojo tenue (turno terminado, esperando el cambio)
    """

    def __init__(self, turn_manager, posicion=(10, 60)):
        self.tm = turn_manager
        self.font = pygame.font.SysFont("Arial", 20, bold=True)
        self.pos = posicion

    def draw(self, pantalla):
        x, y = self.pos
        jugador = self.tm.jugador_actual()
        if not jugador:
            return
        tiempo = max(0, self.tm.tiempo_restante())
        fase = getattr(self.tm, "fase", "turno")
        if fase == "post_disparo":
            color = (255, 140, 0)
            sufijo = ""
        elif fase == "cooldown":
            color = (200, 100, 100)
            sufijo = ""
        else:
            color = (255, 200, 0)
            sufijo = ""
        texto = f"Turno de {jugador} ({tiempo}){sufijo}"
        render = self.font.render(texto, True, color)
        pantalla.blit(render, (x, y))
