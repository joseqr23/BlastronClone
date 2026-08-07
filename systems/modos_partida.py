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
from entities.weapons.proyectil import Proyectil
from utils.sound_manager import sound_manager

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
        return _podio_por_valor_numerico(self.valores_actuales())

    def valores_actuales(self):
        jugadores = [self.game.nombre_jugador] + list(self.game.robots_remotos.keys())
        if self._modo_equipos:
            return {j: self.puntos_equipo.get(self.equipos.get(j), 0) for j in jugadores}
        return {j: self.puntos.get(j, 0) for j in jugadores}
    
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
            armas = list(((cargar_armas().keys())))
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


class ModoBasket:
    """Una sola canasta (game.tiles_canasta); el balón (arma
    "balon_basket") nace en game.punto_spawn_balon y no hace daño —
    tocarlo lo convierte en el arma equipada de quien lo toca. Solo corre
    en el lado autoritativo (host / SoloGame) — en un cliente remoto,
    portador/arma/puntos de OTROS jugadores llegan por red (ver
    basket_portador / basket_arma_forzada / basket_punto en
    message_handler.py), nunca se calculan localmente."""
    id = "basket"
    nombre = "Basket"
    vida_maxima = 50000
    permite_reaparecer = True
    usa_turnos = False
    municion_ilimitada = True
    cooldown_ataque_ms = 500  # cadencia del "palmazo" de los bots

    ARMA_BALON = "balon_basket"
    ARMA_POR_DEFECTO = "manazo"
    ARMAS_PERMITIDAS = ("manazo",) # solo se puede usar el balón, no otras armas
    FACTOR_VELOCIDAD_PORTADOR = 0.5 # Al tener el balon, el portador se mueve más rápido
    FACTOR_SALTO_PORTADOR = 5.0 # Al tener el balon, el portador salta más alto
    FACTOR_VELOCIDAD_BASE = 3   # extra de velocidad para TODOS los robots del modo, no solo el portador
    FACTOR_SALTO_BASE = 1       # extra de salto para TODOS los robots del modo, no solo el portador
    DRENAJE_VIDA_POR_SEGUNDO = 3
    DISTANCIA_TRIPLE = 300
    DISTANCIA_TIRO_BOTS = 220  # los bots retroceden hasta esta distancia del aro antes de intentar encestar
    MARGEN_RECOGIDA_MS = 300
    DURACION_BANNER_MS = 2000
    BLOQUEO_RECOGIDA_MS = 500  # tras soltar el balón, ese jugador no puede volver a agarrarlo de inmediato
    UMBRAL_BALON_ATASCADO_MS = 6000  # si nadie lo agarra/encesta en este tiempo, se reinicia
    COLOR_EQUIPO_A = (220, 60, 60)    # rojo
    COLOR_EQUIPO_B = (70, 130, 230)   # azul

    def __init__(self, game):
        self.game = game
        self.puntos = {}
        self.portador = None
        self.arma_antes_balon = {}
        self._ultimo_drenaje = None
        self._proyectiles_vistos = set()
        self._balon_en_juego = False
        self.banner_texto = None
        self.banner_hasta_ms = 0
        self._bloqueo_recogida = {}
        self._jugadores_inicializados = set()
        self.armas_permitidas = self._resolver_armas_permitidas()
        self.equipos = {}
        self.puntos_equipo = {"A": 0, "B": 0}
        self._modo_equipos = len(getattr(game, "tiles_canasta", {}) or {}) >= 2

    def registrar_muerte(self, victima, atacante):
        pass  # revive solo; _revisar_muerte_portador() suelta el balón si el portador muere

    def partida_terminada(self):
        return False

    def etiqueta_podio(self):
        return "Puntos"

    def podio(self):
        jugadores = [self.game.nombre_jugador] + list(self.game.robots_remotos.keys())
        return _podio_por_valor_numerico({j: self.puntos.get(j, 0) for j in jugadores})

    def valores_actuales(self):
        jugadores = [self.game.nombre_jugador] + list(self.game.robots_remotos.keys())
        return {j: self.puntos.get(j, 0) for j in jugadores}

    def etiqueta_actual(self):
        return "Puntos"

    @property
    def arma_bloqueada(self):
        return self.portador == self.game.nombre_jugador

    def puede_lanzar(self, jugador, arma):
        """Guardia anti-duplicado: solo el portador reconocido por el HOST
        puede generar un proyectil de balon_basket. Corta la carrera entre
        'agarrar' y 'lanzar' cuando ambos caen en el mismo frame (ver
        weapon_manager.crear_proyectil_host)."""
        if arma != self.ARMA_BALON:
            return True
        return jugador == self.portador

    def _mostrar_banner(self, texto, duracion_ms):
        self.banner_texto = texto
        self.banner_hasta_ms = pygame.time.get_ticks() + duracion_ms

    def _robots(self):
        return [self.game.robot, *self.game.robots_remotos.values()]

    def _robot_por_nombre(self, nombre):
        if nombre == self.game.nombre_jugador:
            return self.game.robot
        return self.game.robots_remotos.get(nombre)

    def _es_bot(self, robot):
        npc_manager = getattr(self.game, "npc_manager", None)
        return bool(npc_manager and robot in npc_manager.controllers)

    def _asignar_arma(self, nombre, arma):
        """Cambia el arma equipada de `nombre`. Si el dueño real de ese
        robot es OTRA máquina, avisa por red — si no, el próximo "update"
        que mande esa máquina pisaría el cambio de vuelta a lo que tenía
        antes (cada jugador es la fuente de verdad de su propio
        arma_equipada, salvo por este aviso puntual)."""
        robot = self._robot_por_nombre(nombre)
        if robot is not None:
            robot.arma_equipada = arma
        if nombre != self.game.nombre_jugador:
            self.game.enviar({"tipo": "basket_arma_forzada", "jugador": nombre, "arma": arma})

    def _fijar_portador(self, nombre):
        self.portador = nombre
        self.game.enviar({"tipo": "basket_portador", "jugador": nombre})

    def _spawnear_balon(self):
        punto = getattr(self.game, "punto_spawn_balon", None)
        if punto is None:
            return
        self._reemplazar_balon(punto[0], punto[1])

    def _reemplazar_balon(self, x, y, owner=None):
        """Único punto de creación del balón en todo el modo — destruye
        cualquier balón preexistente ANTES de crear uno nuevo. Con esto
        es imposible que dos código-paths (ej. un golpe y un encestaje
        casi simultáneos) terminen creando dos balones a la vez."""
        self.game.proyectiles = [p for p in self.game.proyectiles if p.tipo != self.ARMA_BALON]
        pid = self.game._next_proy_id()
        p = Proyectil(self.ARMA_BALON, x, y, 0, 0, owner=owner)
        p.proj_id = pid
        self.game.proyectiles.append(p)
        self._balon_en_juego = True
        return p

    def _soltar_balon(self, nombre):
        arma_previa = self.arma_antes_balon.pop(nombre, "nada")
        self._asignar_arma(nombre, arma_previa)
        if self.portador == nombre:
            self._fijar_portador(None)
        # Bloqueo propio, independiente de aturdido_hasta del robot (que
        # ni siquiera se activa si el arma que golpeó no define empuje):
        # este jugador no puede volver a agarrar el balón por un rato,
        # sin importar POR QUÉ lo soltó (golpe, encestada, muerte).
        self._bloqueo_recogida[nombre] = pygame.time.get_ticks() + self.BLOQUEO_RECOGIDA_MS
        robot = self._robot_por_nombre(nombre)
        if robot is not None:
            centro = robot.get_centro()
            self._reemplazar_balon(*centro) 

    def _resolver_armas_permitidas(self):
        if self.ARMAS_PERMITIDAS:
            return list(self.ARMAS_PERMITIDAS)
        try:
            return list(cargar_armas().keys())
        except Exception:
            return []

    @staticmethod
    def _equipo_rival(equipo):
        return "B" if equipo == "A" else "A"

    def color_para_jugador(self, nombre):
        """Color de equipo para el HUD — None si el mapa no está en modo
        por equipos, en cuyo caso el HUD sigue usando el color
        individual de cada robot como siempre."""
        if not self._modo_equipos:
            return None
        equipo = self.equipos.get(nombre)
        if equipo == "A":
            return self.COLOR_EQUIPO_A
        if equipo == "B":
            return self.COLOR_EQUIPO_B
        return None

    def _canasta_rival_de(self, nombre):
        """A qué canasta debe apuntar `nombre` para anotar a favor — None
        si el mapa no está en modo por equipos (una sola canasta, todos
        contra todos)."""
        if not self._modo_equipos:
            return None
        equipo = self.equipos.get(nombre)
        return self._equipo_rival(equipo) if equipo else None

    def _inicializar_jugadores_nuevos(self):
        """Se llama cada frame — barato (es un chequeo de membresía en un
        set) y garantiza que CUALQUIER jugador nuevo (bot, o un jugador
        remoto cuyo robot recién apareció) quede armado y con equipo
        asignado apenas exista, sin depender de que ya estén todos
        presentes en el primer frame (que en multijugador casi nunca es
        el caso — los clientes tardan un par de frames en mandar su
        primer "update")."""
        for robot in self._robots():
            nombre = robot.nombre_jugador
            if nombre in self._jugadores_inicializados:
                continue
            self._jugadores_inicializados.add(nombre)
            self._asignar_arma(nombre, self.ARMA_POR_DEFECTO)
            if self._modo_equipos:
                self._asignar_equipo(nombre, robot)

    def _asignar_equipo(self, nombre, robot):
        fijo = getattr(robot, "equipo_basket", None)
        if not fijo:
            # Alterna A/B balanceando por cantidad ya asignada — así se
            # reparte parejo aunque los jugadores se conecten en
            # momentos distintos, no por índice de orden fijo.
            cuenta_a = sum(1 for e in self.equipos.values() if e == "A")
            cuenta_b = sum(1 for e in self.equipos.values() if e == "B")
            fijo = "A" if cuenta_a <= cuenta_b else "B"
        self.equipos[nombre] = fijo
        robot.color_nombre = self.COLOR_EQUIPO_A if fijo == "A" else self.COLOR_EQUIPO_B
        punto = self._punto_spawn_equipo(fijo)
        if punto:
            robot.punto_reaparicion = punto
            robot.x, robot.y = punto
        self.game.enviar({"tipo": "basket_equipo_jugador", "jugador": nombre, "equipo": fijo})

    def _punto_spawn_equipo(self, equipo):
        spawns = getattr(self.game, "spawns_equipo_basket", None) or {}
        return spawns.get(equipo)

    def mismo_equipo(self, jugador_a, jugador_b):
        """Usado por WeaponManager para quitar el fuego amigo (ver
        _update_proyectiles). False si el modo no es por equipos, si
        alguno es None, o si son la misma persona."""
        if not self._modo_equipos or not jugador_a or not jugador_b or jugador_a == jugador_b:
            return False
        equipo_a = self.equipos.get(jugador_a)
        return equipo_a is not None and equipo_a == self.equipos.get(jugador_b)

    def _centro_canasta(self, equipo=None):
        canastas = getattr(self.game, "tiles_canasta", None) or {}
        tiles = canastas.get(equipo) or next(iter(canastas.values()), None)
        if not tiles:
            return None
        xs = [t.rect.centerx for t in tiles]
        ys = [t.rect.centery for t in tiles]
        return (sum(xs) / len(xs), sum(ys) / len(ys))

    def _distancia_a_canasta(self, equipo, x):
        centro = self._centro_canasta(equipo)
        return abs(x - centro[0]) if centro else 0

    def actualizar(self):
        self._purgar_balones_duplicados()
        self._inicializar_jugadores_nuevos()
        if not self._balon_en_juego and self.portador is None:
            self._spawnear_balon()
        self._detectar_lanzamientos()
        self._detectar_recogidas()
        self._detectar_encestes()
        self._revisar_muerte_portador()
        self._aplicar_efecto_portador()
        self._revisar_balon_atascado()

    def _purgar_balones_duplicados(self):
        """Red de seguridad: nunca debería hacer falta gracias a
        _reemplazar_balon(), pero si por cualquier vía llegaran a
        coexistir dos balones, se destruyen todos menos el más viejo."""
        balones = [p for p in self.game.proyectiles if p.tipo == self.ARMA_BALON]
        for extra in balones[1:]:
            try:
                self.game.proyectiles.remove(extra)
            except ValueError:
                pass

    def _detectar_lanzamientos(self):
        if self.portador is None:
            return
        for p in self.game.proyectiles:
            if p.tipo != self.ARMA_BALON or id(p) in self._proyectiles_vistos:
                continue
            self._proyectiles_vistos.add(id(p))
            if p.owner == self.portador:
                p.x_lanzamiento = p.x
                nombre = self.portador
                self._fijar_portador(None)
                self._asignar_arma(nombre, self.arma_antes_balon.pop(nombre, "nada"))

    def _detectar_recogidas(self):
        if self.portador is not None:
            return
        ahora = pygame.time.get_ticks()
        for p in self.game.proyectiles:
            if p.tipo != self.ARMA_BALON:
                continue
            hitbox = p.get_hitbox()
            for robot in self._robots():
                if robot.is_dead:
                    continue
                nombre = robot.nombre_jugador
                if p.owner == nombre and ahora < p.tiempo_creacion + self.MARGEN_RECOGIDA_MS:
                    continue
                if ahora < self._bloqueo_recogida.get(nombre, 0):
                    continue
                if hitbox.colliderect(robot.get_rect()):
                    self.arma_antes_balon[nombre] = robot.arma_equipada
                    self._asignar_arma(nombre, self.ARMA_BALON)
                    self._fijar_portador(nombre)
                    try:
                        self.game.proyectiles.remove(p)
                    except ValueError:
                        pass
                    self._proyectiles_vistos.discard(id(p))
                    return

    def _detectar_encestes(self):
        canastas = getattr(self.game, "tiles_canasta", None)
        if not canastas:
            return
        for p in self.game.proyectiles[:]:
            if p.tipo != self.ARMA_BALON:
                continue
            hitbox = p.get_hitbox()
            equipo_dueño, encestado = None, False
            for equipo, tiles in canastas.items():
                if any(t.rect.colliderect(hitbox) for t in tiles):
                    equipo_dueño, encestado = equipo, True
                    break
            if not encestado:
                continue

            anotador = p.owner or self.portador
            if anotador:
                x_origen = getattr(p, "x_lanzamiento", p.x)
                puntos = 3 if self._distancia_a_canasta(equipo_dueño, x_origen) >= self.DISTANCIA_TRIPLE else 2
                autogol = False
                if self._modo_equipos and equipo_dueño is not None:
                    equipo_anotador = self.equipos.get(anotador)
                    autogol = equipo_anotador == equipo_dueño
                    beneficiado = self._equipo_rival(equipo_anotador) if autogol else equipo_anotador
                    self.puntos_equipo[beneficiado] = self.puntos_equipo.get(beneficiado, 0) + puntos
                    texto = (f"¡{anotador} encesta en su propio aro! {puntos} puntos para el equipo rival"
                            if autogol else f"¡{anotador} anota {puntos} puntos para su equipo!")
                else:
                    self.puntos[anotador] = self.puntos.get(anotador, 0) + puntos
                    texto = f"¡{puntos} PUNTOS ANOTADOS POR {anotador}!"
                sound_manager.puntos_anotados()
                self._mostrar_banner(texto, self.DURACION_BANNER_MS)
                self.game.enviar({"tipo": "ronda_mensaje", "mensaje": texto, "duracion_ms": self.DURACION_BANNER_MS})
                self.game.enviar({"tipo": "basket_punto", "jugador": anotador, "puntos": puntos, "autogol": autogol})
                self.game.chat.agregar_mensaje(texto)
            try:
                self.game.proyectiles.remove(p)
            except ValueError:
                pass
            self._proyectiles_vistos.discard(id(p))
            self._balon_en_juego = False
            if self.portador:
                nombre = self.portador
                self._fijar_portador(None)
                self._asignar_arma(nombre, self.arma_antes_balon.pop(nombre, "nada"))

    def _revisar_muerte_portador(self):
        if not self.portador:
            return
        robot = self._robot_por_nombre(self.portador)
        if robot is not None and robot.is_dead:
            self._soltar_balon(self.portador)

    def notificar_golpe(self, robot):
        """Llamado por WeaponManager cada vez que un golpe con empuje
        conecta contra un robot (ver el hook en
        WeaponManager._aplicar_empuje)."""
        if robot.nombre_jugador == self.portador:
            self._soltar_balon(robot.nombre_jugador)


    def _velocidades_para(self, robot):
        es_portador = robot.nombre_jugador == self.portador
        base_speed = robot.velocidad_base + self.FACTOR_VELOCIDAD_BASE
        base_jump = robot.salto_base + self.FACTOR_SALTO_BASE
        speed = base_speed + self.FACTOR_VELOCIDAD_PORTADOR if es_portador else base_speed
        jump = base_jump + self.FACTOR_SALTO_PORTADOR if es_portador else base_jump
        return speed, jump

    def aplicar_efecto_local(self, robot):
        """A diferencia de actualizar() (host-autoritativo: spawns, puntos,
        detección de encestes), esto debe correr en CADA máquina sobre SU
        PROPIO robot — cada cliente mueve el suyo con su propio teclado, y
        self.portador ya llega sincronizado a todos vía 'basket_portador'."""
        robot.speed, robot.jump_power = self._velocidades_para(robot)

    def _aplicar_efecto_portador(self):
        ahora = pygame.time.get_ticks()
        if self._ultimo_drenaje is None:
            self._ultimo_drenaje = ahora
        for robot in self._robots():
            robot.speed, robot.jump_power = self._velocidades_para(robot)
        if ahora - self._ultimo_drenaje < 1000:
            return
        self._ultimo_drenaje = ahora
        if self.portador:
            robot = self._robot_por_nombre(self.portador)
            if robot is not None and not robot.is_dead:
                pass  # drenaje de vida desactivado, como ya tenías

    def _revisar_balon_atascado(self):
        """Watchdog: no intenta diagnosticar la física exacta del atasco
        (esquina del aro, tile raro, etc.) — simplemente garantiza que el
        balón nunca quede fuera de circulación por mucho tiempo."""
        if self.portador is not None:
            return
        ahora = pygame.time.get_ticks()
        for p in self.game.proyectiles:
            if p.tipo != self.ARMA_BALON:
                continue
            if ahora - p.tiempo_creacion >= self.UMBRAL_BALON_ATASCADO_MS:
                try:
                    self.game.proyectiles.remove(p)
                except ValueError:
                    pass
                self._proyectiles_vistos.discard(id(p))
                self._balon_en_juego = False
            return  # solo debería existir un balón — no hace falta seguir

MODOS = {
    "puntos": ModoPuntos,
    "muertes": ModoMuertes,
    "lms": ModoUltimoEnPie,
    "libre": ModoLibre,
    "best_of_three": ModoMejorDeTres,
    "basket": ModoBasket,
}


def crear_modo(modo_id, game):
    clase = MODOS.get(modo_id)
    if clase is None:
        print(f"[Modos] '{modo_id}' no reconocido, usando 'puntos' por defecto")
        clase = ModoPuntos
    return clase(game)