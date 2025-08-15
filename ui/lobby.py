# ui/lobby.py
import pygame
from ui.text_input import TextInput
from core.network import Client

class Lobby:
    def __init__(self, host=True, nickname="Jugador", ip="localhost", port=5000):
        self.host = host
        self.nickname = nickname
        self.running = True
        self.jugadores = [nickname]
        self.client = None

        pygame.font.init()
        self.font = pygame.font.SysFont("Arial", 20)
        self.ancho, self.alto = 400, 400
        self.pantalla = pygame.display.set_mode((self.ancho, self.alto))

        self.input_nombre_sala = TextInput(text="Sala1")
        self.input_password = TextInput(text="")

        if not self.host:
            self.client = Client(ip, port, nickname)
            self.client.on_update_players = self.update_players
            self.client.on_start_game = self.start_game_callback

    def update_players(self, players):
        self.jugadores = players

    def start_game_callback(self, config):
        print("¡Comenzar partida!", config)
        self.running = False
        # Aquí se puede instanciar MultiGame con config

    def run(self):
        clock = pygame.time.Clock()
        while self.running:
            self.pantalla.fill((30, 30, 30))
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                self.input_nombre_sala.handle_event(event)
                self.input_password.handle_event(event)

            # Dibujar lista de jugadores
            y = 50
            for jugador in self.jugadores:
                text = self.font.render(jugador, True, (255, 255, 255))
                self.pantalla.blit(text, (50, y))
                y += 30

            # Dibujar inputs
            self.input_nombre_sala.draw(self.pantalla, (50, 10, 200, 30))
            self.input_password.draw(self.pantalla, (260, 10, 100, 30))

            # Botón iniciar partida
            if self.host:
                boton_color = (0, 200, 0) if len(self.jugadores) > 1 else (100, 100, 100)
                rect_boton = pygame.Rect(150, self.alto - 60, 100, 40)
                pygame.draw.rect(self.pantalla, boton_color, rect_boton)
                text = self.font.render("Empezar", True, (0, 0, 0))
                self.pantalla.blit(text, (160, self.alto - 50))

                # Detectar click en botón
                if pygame.mouse.get_pressed()[0]:
                    if rect_boton.collidepoint(pygame.mouse.get_pos()) and len(self.jugadores) > 1:
                        config = {
                            "nombre": self.input_nombre_sala.text,
                            "password": self.input_password.text,
                            "tipo": "puntos",
                            "tiempo_partida": 300,
                            "tiempo_turno": 15
                        }
                        if self.client:
                            self.client.send({"action": "start_game", "config": config})
                        self.start_game_callback(config)

            pygame.display.flip()
            clock.tick(60)
