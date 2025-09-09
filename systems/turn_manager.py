import time
import pickle

class TurnManager:
    def __init__(self, game, duracion_turno=10, cooldown=2):
        self.game = game
        self.duracion_turno = duracion_turno
        self.cooldown = cooldown
        self.jugadores = []
        self.turno_actual = 0
        self.en_cooldown = False
        self.turno_inicio = None
        self.cooldown_inicio = None

        # 🔥 sincronización desde host
        self.turno_restante_sync = None
        self.cooldown_restante_sync = None

    def iniciar(self, jugadores):
        self.jugadores = jugadores
        self.turno_actual = 0
        self.en_cooldown = False
        self.turno_inicio = time.time()
        self.cooldown_inicio = None
        self.turno_restante_sync = self.duracion_turno
        print(f"[TURNOS] Inicia el turno de {self.jugador_actual()}")

    def jugador_actual(self):
        if not self.jugadores:
            return None
        return self.jugadores[self.turno_actual]

    def tiempo_restante(self):
        # 🔥 Si soy cliente, muestro solo lo sincronizado
        if not self.game.host:
            if self.en_cooldown:
                return max(0, int(self.cooldown_restante_sync or 0))
            else:
                return max(0, int(self.turno_restante_sync or 0))

        # 🔥 Si soy host, valido primero que haya tiempo inicializado
        if self.en_cooldown:
            if not self.cooldown_inicio:
                return self.cooldown
            elapsed = time.time() - self.cooldown_inicio
            return max(0, self.cooldown - int(elapsed))
        else:
            if not self.turno_inicio:
                return self.duracion_turno
            elapsed = time.time() - self.turno_inicio
            return max(0, self.duracion_turno - int(elapsed))

    def actualizar(self):
        if not self.jugadores or not self.game.host:
            return  # 🔥 solo el host avanza turnos

        if self.en_cooldown:
            if time.time() - self.cooldown_inicio >= self.cooldown:
                self.siguiente_turno()
        else:
            if time.time() - self.turno_inicio >= self.duracion_turno:
                print(f"[TURNOS] {self.jugador_actual()} perdió el turno por tiempo")
                self.iniciar_cooldown()

    def iniciar_cooldown(self):
        self.en_cooldown = True
        self.cooldown_inicio = time.time()

    def forzar_fin_turno(self):
        if not self.game.host:
            return
        print(f"[TURNOS] {self.jugador_actual()} terminó su turno al disparar")
        self.iniciar_cooldown()

    def siguiente_turno(self):
        self.turno_actual = (self.turno_actual + 1) % len(self.jugadores)
        self.turno_inicio = time.time()
        self.en_cooldown = False
        print(f"[TURNOS] Ahora es el turno de {self.jugador_actual()}")

        # 🔥 Avisar a todos
        if self.game.host:
            data = {
                "tipo": "turno_sync",
                "jugador": self.jugador_actual(),
                "tiempo": self.duracion_turno,
                "cooldown": False
            }
            try:
                self.game.sock.sendto(pickle.dumps(data), (self.game.server_ip, self.game.port))
            except Exception as e:
                print(f"[ERROR TurnManager] no se pudo enviar turno_sync: {e}")
