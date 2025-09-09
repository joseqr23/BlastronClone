# ui/hud.py
import pygame
from entities.players.robot import Robot

class HUDArmas:
    def __init__(self, armas_disponibles, posicion=(700, 10)):
        self.armas = ['nada'] + armas_disponibles + ['spawn_robot']  # Insertamos "nada" al inicio / robot al final para spawnear al robot
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


class HUDPuntajes:
    def __init__(self, game, posicion=(10, 10)):
        """
        game: referencia a la instancia de Game
        posicion: esquina superior derecha donde se dibuja la tabla
        """
        self.game = game
        self.pos = posicion
        self.font = pygame.font.SysFont("Arial", 17, bold=True)
        self.font_title = pygame.font.SysFont("Arial", 20, bold=True)

    def draw(self, pantalla):
        x, y = self.pos
        
        # Título
        titulo = self.font_title.render("Puntuación", True, (0, 0, 0))
        pantalla.blit(titulo, (x, y))
        y += 25

        # Jugador principal (color del robot)
        jugador_color = getattr(self.game.robot, "color_nombre", (0, 0, 0))
        jugador_texto = self.font.render(
            f"{self.game.robot.nombre_jugador}: {self.game.puntajes.get(self.game.robot, 0)}",
            True,
            jugador_color
        )
        pantalla.blit(jugador_texto, (x, y))
        y += 20

        # Robots enemigos
        for robot in self.game.robots_estaticos:
            if not robot.is_dead:
                color_robot = getattr(robot, "color_nombre", (0, 0, 0))
                texto = self.font.render(
                    f"{robot.nombre_jugador}: {self.game.puntajes.get(robot, 0)}",
                    True,
                    color_robot
                )
                pantalla.blit(texto, (x, y))
                y += 20

class HUDPuntajesMultiplayer:
    def __init__(self, game, posicion=(10, 10)):
        self.game = game
        self.pos = posicion
        self.font = pygame.font.SysFont("Arial", 17, bold=True)
        self.font_title = pygame.font.SysFont("Arial", 20, bold=True)

    def draw(self, pantalla):
        x, y = self.pos

        # Título
        titulo = self.font_title.render("Puntuación", True, (0, 0, 0))
        pantalla.blit(titulo, (x, y))
        y += 25

        # Recorremos los puntajes
        for jugador, score in self.game.puntajes.items():
            # Buscar robot correspondiente (local o remoto)
            if self.game.robot and self.game.robot.nombre_jugador == jugador:
                robot = self.game.robot
            else:
                robot = self.game.robots_remotos.get(jugador)

            color = getattr(robot, "color_nombre", (0, 0, 0)) if robot else (0, 0, 0)
            texto = self.font.render(f"{jugador}: {score}", True, color)
            pantalla.blit(texto, (x, y))
            y += 20


class HUDTimer:
    def __init__(self, game, duracion=180, posicion=(400, 10)):
        """
        game: referencia a la instancia del juego (para leer self.tiempo_restante)
        duracion: segundos de la partida (default 3 min = 180)
        posicion: coordenadas donde se dibuja el cronómetro
        """
        self.game = game
        self.duracion = duracion
        self.posicion = posicion
        self.font = pygame.font.SysFont("Arial", 26, bold=True)

    def draw(self, pantalla):
        # tiempo restante sincronizado desde Game
        restante = max(0, self.game.tiempo_restante)
        minutos = restante // 60
        segundos = restante % 60
        texto = f"{minutos:02}:{segundos:02}"

        # 🔴 Cambiar color según urgencia
        if restante <= 10:
            color = (255, 0, 0)      # rojo
        elif restante <= 30:
            color = (255, 165, 0)    # naranja
        else:
            color = (0, 0, 0)  # blanco

        render = self.font.render(texto, True, color)
        rect = render.get_rect(center=self.posicion)
        pantalla.blit(render, rect)

class HUDTurnos:
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
        texto = f"Turno de {self.tm.jugador_actual()} ({tiempo})"
        #texto = f"Turno: {jugador} - {tiempo:02d}s"
        color = (255, 200, 0) if not self.tm.en_cooldown else (200, 100, 100)
        render = self.font.render(texto, True, color)
        pantalla.blit(render, (x, y))
