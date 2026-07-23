# systems/weapon_manager.py
"""
WeaponManager multijugador — genérico y dirigido por datos.

Las armas ya NO están hardcodeadas por clase (Granada/Misil): se definen
en assets/weapons/<arma>/config.json y se cargan dinámicamente mediante
utils/weapon_loader.py. Agregar un arma nueva normalmente solo requiere:

  1. assets/weapons/<arma>/config.json
  2. assets/weapons/<arma>/sprite.png
  3. (opcional) assets/sfx/weapons/<arma>/disparo.mp3 y explosion.mp3

Sin tocar ningún .py — salvo que la nueva arma necesite una física de
colisión genuinamente distinta a "rebote"/"impacto"/"mina"/"cuerpo_a_cuerpo",
en cuyo caso se agrega UN handler más en entities/weapons/proyectil.py
(ver COMPORTAMIENTOS ahí).

IMPORTANTE: este archivo NO decide a quién le hace daño una explosión —
esa decisión (colisión, exclusión de dueño, etc.) vive ÚNICAMENTE en
Proyectil.robots_afectados(). Aquí solo se itera esa lista y se aplica el
daño/puntaje. Si agregas una nueva regla de "quién puede recibir daño",
va en proyectil.py, no aquí.

Host: dueño real de la física de proyectiles (colisión, rebote,
explosión, daño). Cliente: no simula nada, solo dibuja lo que el host
le manda por 'proy_sync' (ver multi_game.py).
"""
from entities.weapons.proyectil import Proyectil
from utils.weapon_loader import config_arma
from utils.sound_manager import sound_manager


class WeaponManager:
    def __init__(self, game):
        self.game = game

    # ------------------------------------------------------------------
    # Disparo
    # ------------------------------------------------------------------
    def disparar(self):
        tm = self.game.turn_manager
        if tm.jugador_actual() != self.game.nombre_jugador or not tm.puede_disparar():
            print(f"[DEBUG] {self.game.nombre_jugador} intentó disparar fuera de turno o ya disparó.")
            return
        arma = self.game.robot.arma_equipada
        config = config_arma(arma)
        if not config:
            return
        ancho = config.get("ancho_proyectil", 40)
        alto = config.get("alto_proyectil", 40)
        origen, vel_x, vel_y = self.game.aim.get_datos_disparo(ancho, alto)
        msg = {
            "tipo": "disparo",
            "jugador": self.game.nombre_jugador,
            "arma": arma,
            "x": origen[0],
            "y": origen[1],
            "dir_x": vel_x,
            "dir_y": vel_y,
        }
        # Bloqueo local inmediato: evita que un doble-click dispare dos
        # veces mientras se espera la confirmación por red.
        tm.disparo_hecho = True
        if self.game.host:
            self.crear_proyectil_host(msg)
        else:
            self.game.enviar(msg)

    def crear_proyectil_host(self, msg):
        """Solo el host llama esto (directo al disparar localmente, o al
        recibir un 'disparo' de un cliente). Crea el proyectil canónico
        y arranca la fase post_disparo del turno."""
        game = self.game
        if not game.host:
            return
        jugador = msg["jugador"]
        arma = msg["arma"]
        if not config_arma(arma):
            print(f"[WeaponManager] Arma desconocida: '{arma}'")
            return
        x, y, dx, dy = msg["x"], msg["y"], msg["dir_x"], msg["dir_y"]
        pid = game._next_proy_id()
        p = Proyectil(arma, x, y, dx, dy, owner=jugador)
        p.proj_id = pid
        game.proyectiles.append(p)
        sound_manager.disparo(arma)
        game.turn_manager.registrar_disparo()

    # ------------------------------------------------------------------
    # Update / draw
    # ------------------------------------------------------------------
    def update(self):
        if self.game.host:
            self._update_proyectiles()
        # El cliente no simula física de proyectiles: su estado llega por
        # red vía "proy_sync" y se aplica directo en multi_game.py.

    def draw(self, pantalla):
        for p in self.game.proyectiles:
            p.draw(pantalla)

    def _robots_para_colision(self, owner):
        """Todos los robots contra los que un proyectil puede
        colisionar: el robot local y TODOS los remotos, incluido el
        propio dueño. Es la misma lista que se usa tanto para la física
        (rebote/impacto) como para calcular a quién puede afectar la
        explosión (ver robots_afectados en Proyectil)."""
        return [self.game.robot] + list(self.game.robots_estaticos)

    # ------------------------------------------------------------------
    # Física — SOLO se ejecuta en el host
    # ------------------------------------------------------------------
    def _update_proyectiles(self):
        for p in self.game.proyectiles[:]:
            candidatos = self._robots_para_colision(getattr(p, "owner", None))
            # La colisión/rebote/impacto contra tiles y TODOS los robots
            # ya ocurre dentro de p.update(), sub-paso por sub-paso.
            p.update(self.game.tiles, candidatos)
            daño = p.daño

            # Proyectil decide TODO sobre a quién dañar (colisión,
            # exclusión de dueño, ya-dañados). Aquí solo se aplica.
            for robot in p.robots_afectados(candidatos):
                es_dueño = getattr(p, "owner", None) == robot.nombre_jugador
                puntos = daño
                if robot.health - daño <= 0:
                    puntos = daño * 2
                self.aplicar_dano(robot, daño)
                # No dar puntos si el dueño del proyectil es la misma
                # víctima (auto-daño, cuando sí está permitido).
                if not es_dueño:
                    self.game.enviar_evento_puntaje(p.owner, puntos, robot)
                p.danados.add(robot)
                if robot is self.game.robot:
                    print(f"[{p.tipo.upper()}] Host aplica {daño} a {self.game.nombre_jugador} por {p.tipo} de {p.owner}")

            if p.estado == "done":
                try:
                    self.game.proyectiles.remove(p)
                except ValueError:
                    pass

    def aplicar_dano(self, robot, cantidad):
        """Solo se llama desde el host. Aplica el daño localmente y lo
        notifica a todos los clientes."""
        if not self.game.host:
            return
        robot.take_damage(cantidad)
        self.game.enviar({
            "tipo": "damage",
            "jugador": robot.nombre_jugador,
            "cantidad": cantidad,
            "quien": self.game.nombre_jugador,
        })