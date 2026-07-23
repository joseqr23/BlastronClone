# ui/hud.py
import pygame
from entities.players.robot import Robot
from utils.weapon_loader import cargar_armas
from settings import ANCHO


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
    """
    Selector de armas en cuadrícula (grid) que se ajusta sola al ancho de
    pantalla — calcula cuántos botones caben por fila según ANCHO (de
    settings.py) y su propia posición de inicio, y cuando se llena una
    fila continúa hacia abajo. No hace falta tocar nada cuando agregas
    un arma nueva, sin importar cuántas termines teniendo: nunca se sale
    de la pantalla, solo crece hacia abajo.

    Incluye:
      - Botón de colapsar/expandir, siempre visible, a la DERECHA de la
        cuadrícula de armas (las armas quedan ancladas en `posicion`, el
        botón se calcula después según el ancho real de la cuadrícula).
      - Panel de fondo semitransparente para que se vea como un widget,
        no íconos sueltos flotando sobre el mapa.
      - Tooltip con el nombre legible del arma (campo "nombre" de su
        config.json) al pasar el mouse por encima.

    Íconos: busca assets/hud/<arma>.png primero; si no existe, usa el
    primer frame del sprite propio del arma como ícono automático.
    """

    def __init__(self, armas_disponibles, posicion=(600, 10), margen_derecho=20, max_por_fila=None):
        self.armas = ['nada'] + armas_disponibles + ['spawn_robot']
        self.pos = posicion
        self.seleccion = 'nada'
        self.colapsado = False

        self.ancho_boton = 60
        self.alto_boton = 60
        self.padding = 10
        self.ancho_toggle = 30
        self.margen_derecho = margen_derecho
        # Si se pasa un número fijo, se usa tal cual; si no, se calcula
        # solo según cuánto espacio quede hasta el borde de la pantalla.
        self.max_por_fila = max_por_fila

        self.botones = []
        self.rect_toggle = pygame.Rect(0, 0, 0, 0)
        self.rect_panel = pygame.Rect(0, 0, 0, 0)
        self.imagenes = {}
        self.nombres_legibles = {}
        self.font_toggle = pygame.font.SysFont("Arial", 20, bold=True)
        self.font_tooltip = pygame.font.SysFont("Arial", 14, bold=True)

        self.crear_botones()
        self.cargar_imagenes()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _calcular_por_fila(self):
        if self.max_por_fila is not None:
            return max(1, self.max_por_fila)
        # Reserva espacio para el toggle AL FINAL (a la derecha de la
        # cuadrícula), no al principio.
        disponible = max(
            self.ancho_boton,
            (ANCHO - self.margen_derecho) - self.pos[0] - self.ancho_toggle - self.padding
        )
        return max(1, int((disponible + self.padding) // (self.ancho_boton + self.padding)))

    def crear_botones(self):
        x, y = self.pos
        self.botones = []
        por_fila = self._calcular_por_fila()

        # Las armas se anclan en (x, y) tal cual — ya no se corren para
        # dejarle hueco al toggle antes de ellas.
        for i, arma in enumerate(self.armas):
            fila, col = divmod(i, por_fila)
            rect = pygame.Rect(
                x + col * (self.ancho_boton + self.padding),
                y + fila * (self.alto_boton + self.padding),
                self.ancho_boton, self.alto_boton,
            )
            self.botones.append((arma, rect))

        columnas = min(len(self.armas), por_fila) if self.armas else 1
        filas = (len(self.armas) - 1) // por_fila + 1 if self.armas else 1
        ancho_grid = columnas * (self.ancho_boton + self.padding) - self.padding
        alto_grid = filas * (self.alto_boton + self.padding) - self.padding

        # El toggle se ubica DESPUÉS de la cuadrícula, a su derecha.
        x_toggle = x + ancho_grid + self.padding
        self.rect_toggle = pygame.Rect(x_toggle, y, self.ancho_toggle, self.alto_boton)

        # Panel de fondo que envuelve toda la cuadrícula + el toggle.
        margen = 6
        self.rect_panel = pygame.Rect(
            x - margen,
            y - margen,
            ancho_grid + self.padding + self.ancho_toggle + margen * 2,
            max(self.alto_boton, alto_grid) + margen * 2,
        )

    # ------------------------------------------------------------------
    # Recursos
    # ------------------------------------------------------------------
    def cargar_imagenes(self):
        catalogo = cargar_armas()
        for arma in self.armas:
            imagen = None
            try:
                imagen = pygame.image.load(f"assets/hud/{arma}.png").convert_alpha()
                imagen = pygame.transform.smoothscale(imagen, (40, 40))
            except Exception:
                # Sin ícono propio en assets/hud/: usamos el primer frame
                # del sprite del arma (idle) como ícono automático.
                config = catalogo.get(arma)
                frames = config.get("_frames_img") if config else None
                if frames:
                    try:
                        imagen = pygame.transform.smoothscale(frames[0], (40, 40))
                    except Exception:
                        imagen = None
            self.imagenes[arma] = imagen

            config = catalogo.get(arma)
            if config and config.get("nombre"):
                self.nombres_legibles[arma] = config["nombre"]
            elif arma == 'nada':
                self.nombres_legibles[arma] = 'Ninguna'
            elif arma == 'spawn_robot':
                self.nombres_legibles[arma] = 'Invocar robot'
            else:
                self.nombres_legibles[arma] = arma.capitalize()

    # ------------------------------------------------------------------
    # Eventos
    # ------------------------------------------------------------------
    def punto_sobre_hud(self, pos):
        """Usado por event_handler.py para no disparar cuando el clic cae
        sobre el botón de colapsar o (si está expandido) sobre algún
        botón de arma."""
        if self.rect_toggle.collidepoint(pos):
            return True
        if self.colapsado:
            return False
        return any(rect.collidepoint(pos) for _, rect in self.botones)

    def manejar_evento(self, evento):
        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            pos = evento.pos
            if self.rect_toggle.collidepoint(pos):
                self.colapsado = not self.colapsado
                return None
            if self.colapsado:
                return None
            for arma, rect in self.botones:
                if rect.collidepoint(pos):
                    self.seleccion = arma
                    return arma
        return None

    # ------------------------------------------------------------------
    # Dibujo
    # ------------------------------------------------------------------
    def draw(self, pantalla, font):
        panel = self.rect_toggle.inflate(6, 6) if self.colapsado else self.rect_panel
        fondo = pygame.Surface((panel.width, panel.height), pygame.SRCALPHA)
        fondo.fill((20, 20, 20, 160))
        pantalla.blit(fondo, panel.topleft)
        pygame.draw.rect(pantalla, (200, 200, 200), panel, width=1)

        pygame.draw.rect(pantalla, (80, 80, 80), self.rect_toggle)
        # El toggle ahora está a la derecha de las armas: ">" significa
        # "las armas están a la izquierda, clic para ocultarlas"
        # (expandido) y "<" significa "clic para mostrarlas" (colapsado).
        flecha = "<" if self.colapsado else ">"
        texto_flecha = self.font_toggle.render(flecha, True, (255, 255, 255))
        pantalla.blit(texto_flecha, texto_flecha.get_rect(center=self.rect_toggle.center))

        if self.colapsado:
            return

        mouse_pos = pygame.mouse.get_pos()
        hover = None

        for arma, rect in self.botones:
            color = (0, 200, 0) if self.seleccion == arma else (150, 150, 150)
            pygame.draw.rect(pantalla, color, rect)
            imagen = self.imagenes.get(arma)
            if imagen:
                img_rect = imagen.get_rect(center=rect.center)
                pantalla.blit(imagen, img_rect)
            else:
                texto_mostrar = self.nombres_legibles.get(arma, arma.capitalize())
                text = font.render(texto_mostrar, True, (0, 0, 0))
                text_rect = text.get_rect(center=rect.center)
                pantalla.blit(text, text_rect)
            if rect.collidepoint(mouse_pos):
                hover = (arma, rect)

        if hover is not None:
            self._draw_tooltip(pantalla, *hover)

    def _draw_tooltip(self, pantalla, arma, rect):
        texto = self.nombres_legibles.get(arma, arma.capitalize())
        render = self.font_tooltip.render(texto, True, (255, 255, 255))
        padding = 4
        fondo_rect = render.get_rect()
        fondo_rect.inflate_ip(padding * 2, padding * 2)
        fondo_rect.midtop = (rect.centerx, rect.bottom + 4)
        # No dejar que el tooltip se salga de la pantalla por la derecha.
        if fondo_rect.right > ANCHO:
            fondo_rect.right = ANCHO - 2
        fondo = pygame.Surface(fondo_rect.size, pygame.SRCALPHA)
        fondo.fill((0, 0, 0, 210))
        pantalla.blit(fondo, fondo_rect.topleft)
        pantalla.blit(render, render.get_rect(center=fondo_rect.center))


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