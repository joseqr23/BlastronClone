import time


class TurnManager:
    """
    Fases de un turno:
      "turno"        -> puede moverse y disparar (1 vez)
      "post_disparo" -> ya disparó: puede seguir moviéndose pero no disparar,
                         dura post_disparo_duracion segundos
      "cooldown"     -> turno terminado, esperando pasar al siguiente jugador
    """

    def __init__(self, game, duracion_turno=10, post_disparo_duracion=3, cooldown=0):
        self.game = game
        self.duracion_turno = duracion_turno
        self.post_disparo_duracion = post_disparo_duracion
        self.cooldown = cooldown

        self.jugadores = []
        self.turno_actual = 0

        self.fase = "turno"
        self.en_cooldown = False
        self.disparo_hecho = False

        self.turno_inicio = None
        self.post_disparo_inicio = None
        self.cooldown_inicio = None

        # Sincronización para clientes (no-host)
        self.turno_restante_sync = None
        self.post_disparo_restante_sync = None
        self.cooldown_restante_sync = None

    def iniciar(self, jugadores):
        self.jugadores = jugadores
        self.turno_actual = 0
        self.fase = "turno"
        self.en_cooldown = False
        self.disparo_hecho = False
        self.turno_inicio = time.time()
        self.post_disparo_inicio = None
        self.cooldown_inicio = None
        self.turno_restante_sync = self.duracion_turno
        print(f"[TURNOS] Inicia el turno de {self.jugador_actual()}")

    def jugador_actual(self):
        if not self.jugadores:
            return None
        return self.jugadores[self.turno_actual]

    def puede_disparar(self):
        """Solo se puede disparar en fase 'turno', sin haber disparado ya."""
        return self.fase == "turno" and not self.disparo_hecho and not self.en_cooldown

    def tiempo_restante(self):
        if not self.game.host:
            if self.fase == "cooldown":
                return max(0, int(self.cooldown_restante_sync or 0))
            elif self.fase == "post_disparo":
                return max(0, int(self.post_disparo_restante_sync or 0))
            else:
                return max(0, int(self.turno_restante_sync or 0))

        if self.fase == "cooldown":
            if not self.cooldown_inicio:
                return self.cooldown
            elapsed = time.time() - self.cooldown_inicio
            return max(0, self.cooldown - int(elapsed))
        elif self.fase == "post_disparo":
            if not self.post_disparo_inicio:
                return self.post_disparo_duracion
            elapsed = time.time() - self.post_disparo_inicio
            return max(0, self.post_disparo_duracion - int(elapsed))
        else:
            if not self.turno_inicio:
                return self.duracion_turno
            elapsed = time.time() - self.turno_inicio
            return max(0, self.duracion_turno - int(elapsed))

    def actualizar(self):
        """Solo el host avanza la máquina de estados de turnos."""
        if not self.jugadores or not self.game.host:
            return

        if self.fase == "cooldown":
            if time.time() - self.cooldown_inicio >= self.cooldown:
                self.siguiente_turno()

        elif self.fase == "post_disparo":
            if time.time() - self.post_disparo_inicio >= self.post_disparo_duracion:
                self.iniciar_cooldown()

        else:  # "turno"
            if time.time() - self.turno_inicio >= self.duracion_turno:
                print(f"[TURNOS] {self.jugador_actual()} perdió el turno por tiempo")
                self.iniciar_cooldown()

    def registrar_disparo(self):
        """Llamado por WeaponManager (solo host) cuando el jugador actual
        dispara con éxito: bloquea nuevos disparos mientras le deja 3s más
        para moverse antes de que termine el turno."""
        if not self.game.host:
            return
        self.disparo_hecho = True
        self.fase = "post_disparo"
        self.post_disparo_inicio = time.time()
        print(f"[TURNOS] {self.jugador_actual()} disparó — {self.post_disparo_duracion}s de movimiento restante")
        self.enviar_sync()

    def iniciar_cooldown(self):
        self.fase = "cooldown"
        self.en_cooldown = True
        self.cooldown_inicio = time.time()
        self.enviar_sync()

    def forzar_fin_turno(self):
        """Termina el turno de inmediato, saltándose post_disparo (usado por
        ejemplo cuando el jugador recibe daño o se corta la partida)."""
        if not self.game.host:
            return
        print(f"[TURNOS] {self.jugador_actual()} terminó su turno de forma forzada")
        self.iniciar_cooldown()

    def siguiente_turno(self):
        self.turno_actual = (self.turno_actual + 1) % len(self.jugadores)
        self.fase = "turno"
        self.en_cooldown = False
        self.disparo_hecho = False
        self.turno_inicio = time.time()
        self.post_disparo_inicio = None
        self.cooldown_inicio = None
        print(f"[TURNOS] Ahora es el turno de {self.jugador_actual()}")
        self.enviar_sync()

    def enviar_sync(self):
        """Publica el estado actual del turno a todos los clientes.
        Se llama cada frame desde multi_game.run() y también en cada
        transición de fase para que el cambio se sienta instantáneo."""
        if not self.game.host:
            return
        self.game.enviar({
            "tipo": "turno_sync",
            "jugador": self.jugador_actual(),
            "fase": self.fase,
            "tiempo": self.tiempo_restante(),
        })
