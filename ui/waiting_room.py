class WaitingRoom:
    def __init__(self, pantalla, font, rol, socket):
        self.pantalla = pantalla
        self.font = font
        self.rol = rol
        self.socket = socket
        self.jugadores = []

    def run(self):
        running = True
        while running:
            # Dibujar sala, lista de jugadores y botones
            # Actualizar lista de jugadores desde socket
            # Manejar click en "Empezar" si rol == Servidor
            pass
