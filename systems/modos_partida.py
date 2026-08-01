# systems/modos_partida.py
"""
Reglas de cada modo de partida — quién gana, cuándo se acaba, y cómo se
arma el podio. Igual que con las armas (ver COMPORTAMIENTOS en
entities/weapons/proyectil.py): agregar un modo nuevo es agregar UNA
clase aquí y registrarla en MODOS, sin tocar multi_game.py.

Interfaz común de cada modo:
    vida_maxima          (int, atributo de clase) — con cuánta vida
                          arrancan los robots en este modo.
    registrar_muerte(victima, atacante) — se llama una vez por cada
                          robot que muere, tanto en el host como en cada
                          cliente (vía el mensaje de red "muerte").
    partida_terminada()  -> bool — condición de fin PROPIA del modo,
                          además del timer normal (que ya termina la
                          partida solo). False si no aplica.
    etiqueta_podio()     -> str — texto que acompaña el valor de cada
                          jugador en el podio.
    podio()              -> [(rango, [(jugador, valor), ...]), ...] ya
                          agrupado y ordenado, listo para dibujar.

    usa_turnos            (bool, atributo de clase) — si el modo usa
                          TurnManager (un jugador a la vez) o todos
                          pueden moverse/atacar siempre.
    municion_ilimitada    (bool, atributo de clase) — si WeaponManager
                          debe ignorar la munición configurada por arma.
"""
import random
import pygame
from utils.weapon_loader import cargar_armas

class ModoPuntos:
    id = "puntos"
    nombre = "Puntos"
    vida_maxima = 200
    permite_reaparecer = True
    usa_turnos = True
    municion_ilimitada = False
    
    def __init__(self, game):
        self.game = game

    def registrar_muerte(self, victima, atacante):
        pass  # el puntaje ya se otorga por daño, no por la muerte en sí

    def partida_terminada(self):
        return False  # solo termina por tiempo

    def etiqueta_podio(self):
        return "Puntaje"

    def podio(self):
        return _podio_por_valor_numerico(self.game.puntajes)

    def valores_actuales(self):
        return dict(self.game.puntajes)
    
    def etiqueta_actual(self):
        return "Puntaje"

    def actualizar(self):
        pass  # este modo no tiene lógica propia por frame (solo timer)
class ModoMuertes:
    id = "muertes"
    nombre = "Muertes"
    vida_maxima = 100  # mitad de lo normal — muertes más rápidas
    permite_reaparecer = True
    usa_turnos = True
    municion_ilimitada = False

    def __init__(self, game):
        self.game = game
        self.muertes = {}

    def registrar_muerte(self, victima, atacante):
        nombre_victima = victima.nombre_jugador
        if atacante and atacante != nombre_victima:
            self.muertes[atacante] = self.muertes.get(atacante, 0) + 1
        else:
            # Suicidio, o muerte sin atacante (ej. zona dañina del
            # mapa): penaliza restando 1 al propio conteo de la víctima.
            self.muertes[nombre_victima] = self.muertes.get(nombre_victima, 0) - 1

    def partida_terminada(self):
        return False

    def etiqueta_podio(self):
        return "Muertes"

    def podio(self):
        jugadores = [self.game.nombre_jugador] + list(self.game.robots_remotos.keys())
        valores = {j: self.muertes.get(j, 0) for j in jugadores}
        return _podio_por_valor_numerico(valores)

    def valores_actuales(self):
        jugadores = [self.game.nombre_jugador] + list(self.game.robots_remotos.keys())
        return {j: self.muertes.get(j, 0) for j in jugadores}
    
    def etiqueta_actual(self):
        return "Muertes"

    def actualizar(self):
        pass  # este modo no tiene lógica propia por frame (solo timer)

class ModoUltimoEnPie:
    id = "lms"
    nombre = "Último en pie"
    vida_maxima = 1000  # mucha vida — la partida dura, no se acaba de un golpe
    permite_reaparecer = False
    usa_turnos = True
    municion_ilimitada = False

    def __init__(self, game):
        self.game = game
        self.orden_eliminacion = []  # primer eliminado -> último eliminado

    def registrar_muerte(self, victima, atacante):
        nombre = victima.nombre_jugador
        if nombre not in self.orden_eliminacion:
            self.orden_eliminacion.append(nombre)

    def _jugadores_vivos(self):
        todos = [self.game.nombre_jugador] + list(self.game.robots_remotos.keys())
        return [j for j in todos if j not in self.orden_eliminacion]

    def partida_terminada(self):
        todos = [self.game.nombre_jugador] + list(self.game.robots_remotos.keys())
        return len(todos) > 1 and len(self._jugadores_vivos()) <= 1

    def etiqueta_podio(self):
        return "Resultado"

    def podio(self):
        vivos = self._jugadores_vivos()
        grupos = []
        if vivos:
            entradas = []
            for j in vivos:
                robot = self.game.robot if j == self.game.nombre_jugador else self.game.robots_remotos.get(j)
                vida = getattr(robot, "health", 0) if robot else 0
                entradas.append((j, f"Vida restante {vida}"))
            entradas.sort(key=lambda e: e[1], reverse=True)
            for jugador, vida in entradas:
                if grupos and grupos[-1][1][0][1] == vida:
                    grupos[-1][1].append((jugador, vida))
                else:
                    grupos.append((len(grupos) + 1, [(jugador, vida)]))
        # El último en morir queda más cerca de haber ganado, así que va
        # justo debajo de los que sobrevivieron; el primero en morir
        # queda al final del podio.
        for jugador in reversed(self.orden_eliminacion):
            grupos.append((len(grupos) + 1, [(jugador, "Eliminado")]))
        return grupos

    def valores_actuales(self):
        valores = {}
        robot_local = self.game.robot
        valores[self.game.nombre_jugador] = 0 if robot_local.nombre_jugador in self.orden_eliminacion else robot_local.health
        for nombre, r in self.game.robots_remotos.items():
            valores[nombre] = 0 if nombre in self.orden_eliminacion else r.health
        return valores
    
    def etiqueta_actual(self):
        return "Vida Restante"
    
    def actualizar(self):
        pass  # este modo no tiene lógica propia por frame (solo timer)

def _podio_por_valor_numerico(valores: dict):
    """Helper compartido por los modos que ordenan por un número simple
    (puntaje, muertes): agrupa a quienes tengan el mismo valor."""
    orden = sorted(valores.items(), key=lambda kv: kv[1], reverse=True)
    grupos = []
    for jugador, valor in orden:
        if grupos and grupos[-1][1][0][1] == valor:
            grupos[-1][1].append((jugador, valor))
        else:
            grupos.append((len(grupos) + 1, [(jugador, valor)]))
    return grupos

class ModoLibre(ModoUltimoEnPie):
    """Todos se mueven y atacan libremente, sin esperar turno — última
    vida, gana quien sobrevive. Hereda TODA la lógica de eliminación,
    podio y condición de fin de ModoUltimoEnPie (son la misma regla);
    solo cambia cómo se gana el derecho a disparar."""
    id = "libre"
    nombre = "Libre"
    vida_maxima = 1000
    permite_reaparecer = False
    usa_turnos = False
    municion_ilimitada = True
    cooldown_ataque_ms = 2000  # tiempo mínimo entre disparos de un mismo jugador/bot
    def actualizar(self):
        pass  # este modo no tiene lógica propia por frame (solo timer)

class ModoMejorDeTres:
    """Rondas con la MISMA arma para todos (rota por ronda, elegida al
    azar) — gana la partida quien llegue primero a VICTORIAS_PARA_GANAR
    rondas. Reutiliza "muerte" tal cual (ya llega replicada a todos los
    clientes vía el mensaje "muerte", igual que en cualquier otro modo)
    — lo nuevo es actualizar() (SOLO se llama desde el host) y el
    mensaje "ronda_sync" para que los clientes reciban el reseteo de
    arma/vida al empezar cada ronda.

    De qué armas se sortea cada ronda (ver _resolver_pool_armas):
      - Modo Solo: si el nivel define "armas_rondas" en su JSON, se usa
        EXACTAMENTE esa lista — permite curar la campaña (p. ej. evitar
        armas demasiado fuertes en niveles tempranos).
      - Multijugador, o Solo sin ese campo: se sortea entre TODAS las
        armas que el juego tenga cargadas (cargar_armas()), sin lista
        fija — si agregas un arma nueva al proyecto, ya entra sola al
        pool sin tocar este archivo."""
    id = "best_of_three"
    nombre = "Mejor de 3"
    vida_maxima = 300
    permite_reaparecer = False
    usa_turnos = False
    municion_ilimitada = True
    cooldown_ataque_ms = 1200  # tiempo mínimo entre disparos de un mismo jugador/bot
    arma_bloqueada = True  # el jugador no puede cambiar de arma a mano
    VICTORIAS_PARA_GANAR = 2
    ARMAS_RONDAS_FALLBACK = ("misil", "granada", "rifle", "escopeta", "katana", "supermisil")
    DURACION_PAUSA_MS = 2200         # "X gana la ronda" antes de la siguiente
    DURACION_ROUND_BANNER_MS = 1500  # "ROUND N" al empezar cada ronda


    def __init__(self, game):
        self.game = game
        self.victorias = {}
        self.eliminados_ronda = []
        self.ronda = 0
        self.arma_ronda = None
        self.terminado = False
        self.ganador = None
        self.rng = random.Random()
        self.armas_pool = self._resolver_pool_armas()
        self.pausa_hasta_ms = 0
        self.banner_texto = None
        self.banner_hasta_ms = 0

    def _resolver_pool_armas(self):
        nivel = getattr(self.game, "level", None)
        armas_nivel = getattr(nivel, "armas_rondas", None) if nivel else None
        if armas_nivel:
            return list(armas_nivel)
        try:
            armas = list(cargar_armas().keys())
        except Exception:
            armas = []
        return armas or list(self.ARMAS_RONDAS_FALLBACK)

    def _elegir_arma_ronda(self):
        """Sortea la próxima arma evitando repetir la de la ronda
        anterior de seguido (si el pool tiene más de una opción) — así
        se siente más variado que un random.choice puro, que a veces
        repite dos rondas seguidas por pura casualidad."""
        pool = self.armas_pool
        if not pool:
            return self.ARMAS_RONDAS_FALLBACK[0]
        if len(pool) == 1:
            return pool[0]
        opciones = [a for a in pool if a != self.arma_ronda] or pool
        return self.rng.choice(opciones)

    def _jugadores(self):
        return [self.game.nombre_jugador] + list(self.game.robots_remotos.keys())

    def _robot(self, nombre):
        return self.game.robot if nombre == self.game.nombre_jugador else self.game.robots_remotos.get(nombre)

    def registrar_muerte(self, victima, atacante):
        nombre = victima.nombre_jugador
        if nombre not in self.eliminados_ronda:
            self.eliminados_ronda.append(nombre)

    def _vivos_ronda(self):
        return [j for j in self._jugadores() if j not in self.eliminados_ronda]

    def _mostrar_banner(self, texto, duracion_ms):
        self.banner_texto = texto
        self.banner_hasta_ms = pygame.time.get_ticks() + duracion_ms

    def actualizar(self):
        """SOLO debe llamarse desde el host (o desde SoloGame, que
        siempre actúa como host). Decide cuándo termina una ronda y
        arranca la siguiente, o cierra la partida."""
        if self.terminado:
            return
        ahora = pygame.time.get_ticks()

        if self.pausa_hasta_ms:
            if ahora < self.pausa_hasta_ms:
                return
            self.pausa_hasta_ms = 0
            self._iniciar_ronda()
            return
        
        if self.arma_ronda is None:
            self._iniciar_ronda()
            return
        
        jugadores = self._jugadores()
        if len(jugadores) <= 1 or len(self._vivos_ronda()) > 1:
            return
        vivos = self._vivos_ronda()
        ganador_ronda = vivos[0] if vivos else None
        if ganador_ronda:
            self.victorias[ganador_ronda] = self.victorias.get(ganador_ronda, 0) + 1
            if self.victorias[ganador_ronda] >= self.VICTORIAS_PARA_GANAR:
                self.terminado = True
                self.ganador = ganador_ronda
                self._sincronizar_victorias_finales()
                return
            texto = f"¡{ganador_ronda} gana la ronda {self.ronda}!"
        else:
            texto = f"¡Ronda {self.ronda} empatada!"

        self._mostrar_banner(texto, self.DURACION_PAUSA_MS)
        self.pausa_hasta_ms = ahora + self.DURACION_PAUSA_MS
        self.game.enviar({"tipo": "ronda_mensaje", "mensaje": texto, "duracion_ms": self.DURACION_PAUSA_MS})

    def _iniciar_ronda(self):
        self.game.proyectiles.clear()
        if hasattr(self.game, "weapon_manager"):
            self.game.weapon_manager.disparos_pendientes.clear()
        self.eliminados_ronda = []
        self.arma_ronda = self._elegir_arma_ronda()
        self.ronda += 1
        npc_manager = getattr(self.game, "npc_manager", None)
        for nombre in self._jugadores():
            robot = self._robot(nombre)
            if robot is None:
                continue
            robot.reset()  # respawn aleatorio + vida llena, igual que al arrancar la partida
            robot.arma_equipada = self.arma_ronda
            controlador = npc_manager.controllers.get(robot) if npc_manager else None
            if controlador:
                controlador.on_round_start()
        texto_banner = f"ROUND {self.ronda}"
        self._mostrar_banner(texto_banner, self.DURACION_ROUND_BANNER_MS)
        self.game.enviar({
            "tipo": "ronda_sync",
            "arma": self.arma_ronda,
            "ronda": self.ronda,
            "victorias": dict(self.victorias),
            "banner": texto_banner,
            "banner_ms": self.DURACION_ROUND_BANNER_MS,
        })

    def _sincronizar_victorias_finales(self):
        """Cuando la partida termina justo en la ronda ganadora, no hay
        una próxima ronda que dispare _iniciar_ronda() (y con ella el
        "ronda_sync" de siempre) — sin esto, los clientes se quedan con
        el conteo de victorias de ANTES de la ronda decisiva, mostrando
        al ganador con un punto menos de lo real en el podio."""
        self.game.enviar({
            "tipo": "ronda_sync",
            "arma": self.arma_ronda,
            "ronda": self.ronda,
            "victorias": dict(self.victorias),
            "final": True,
        })

    def partida_terminada(self):
        return self.terminado

    def etiqueta_podio(self):
        return "Victorias"

    def podio(self):
        return _podio_por_valor_numerico({j: self.victorias.get(j, 0) for j in self._jugadores()})

    def valores_actuales(self):
        return {j: self.victorias.get(j, 0) for j in self._jugadores()}

    def etiqueta_actual(self):
        return f"Victorias — Ronda {self.ronda} ({self.arma_ronda or '?'})"

MODOS = {
    "puntos": ModoPuntos,
    "muertes": ModoMuertes,
    "lms": ModoUltimoEnPie,
    "libre": ModoLibre,
    "best_of_three": ModoMejorDeTres,
}


def crear_modo(modo_id, game):
    clase = MODOS.get(modo_id)
    if clase is None:
        print(f"[Modos] '{modo_id}' no reconocido, usando 'puntos' por defecto")
        clase = ModoPuntos
    return clase(game)