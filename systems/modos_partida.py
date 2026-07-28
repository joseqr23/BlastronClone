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
"""


class ModoPuntos:
    id = "puntos"
    nombre = "Puntos"
    vida_maxima = 200
    permite_reaparecer = True

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


class ModoMuertes:
    id = "muertes"
    nombre = "Muertes"
    vida_maxima = 100  # mitad de lo normal — muertes más rápidas
    permite_reaparecer = True

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

class ModoUltimoEnPie:
    id = "lms"
    nombre = "Último en pie"
    vida_maxima = 600  # mucha vida — la partida dura, no se acaba de un golpe
    permite_reaparecer = False

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


MODOS = {
    "puntos": ModoPuntos,
    "muertes": ModoMuertes,
    "lms": ModoUltimoEnPie,
}


def crear_modo(modo_id, game):
    clase = MODOS.get(modo_id)
    if clase is None:
        print(f"[Modos] '{modo_id}' no reconocido, usando 'puntos' por defecto")
        clase = ModoPuntos
    return clase(game)