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

Campos opcionales de config.json que maneja este archivo:
  municion            (int)  munición inicial de esa arma para este
                             jugador. Si no está, el arma es ilimitada.
                             Se descuenta 1 por CADA VEZ que se confirma
                             un disparo (no por cada proyectil que salga
                             de él si "cantidad" > 1).
  cantidad            (int)  cuántos proyectiles salen de un solo disparo
                             (por defecto 1). Se reparten en abanico
                             alrededor de la dirección apuntada.
  dispersion_grados   (float) ancho total del abanico cuando cantidad > 1
                             (por defecto 18°).

Host: dueño real de la física de proyectiles (colisión, rebote,
explosión, daño). Cliente: no simula nada, solo dibuja lo que el host
le manda por 'proy_sync' (ver multi_game.py).
"""
import math
from entities.weapons.proyectil import Proyectil
from utils.weapon_loader import config_arma
from utils.sound_manager import sound_manager


class WeaponManager:
    def __init__(self, game):
        self.game = game
        # {arma_id: cantidad_restante} — solo se llena para armas que
        # tienen "municion" definida en su config.json. Persiste durante
        # toda la partida (no se reinicia entre turnos).
        self.municion_restante = {}

    # ------------------------------------------------------------------
    # Munición
    # ------------------------------------------------------------------
    def tiene_municion(self, arma, config):
        limite = config.get("municion")
        if limite is None:
            return True  # arma ilimitada
        restante = self.municion_restante.setdefault(arma, limite)
        return restante > 0

    def consumir_municion(self, arma, config):
        if config.get("municion") is None:
            return
        actual = self.municion_restante.get(arma, config.get("municion"))
        self.municion_restante[arma] = max(0, actual - 1)

    def municion_actual(self, arma):
        """Usado por el HUD. None = munición ilimitada (no mostrar nada)."""
        config = config_arma(arma)
        if not config or config.get("municion") is None:
            return None
        return self.municion_restante.get(arma, config.get("municion"))

    # ------------------------------------------------------------------
    # Disparo
    # ------------------------------------------------------------------
    def _generar_disparos(self, config, ancho, alto):
        """Devuelve una lista de (origen, vel_x, vel_y) — una por cada
        proyectil que debe salir de este disparo. Con "cantidad" > 1 se
        reparten en abanico (mismo origen, ángulos repartidos alrededor
        de la dirección apuntada) rotando el vector de velocidad."""
        velocidad_fija = config.get("velocidad_proyectil")
        origen, vel_x, vel_y = self.game.aim.get_datos_disparo(ancho, alto, velocidad_fija=velocidad_fija)
        cantidad = max(1, config.get("cantidad", 1))
        if cantidad == 1:
            return [(origen, vel_x, vel_y)]

        spread_total = config.get("dispersion_grados", 18)
        resultados = []
        for i in range(cantidad):
            t = (i / (cantidad - 1)) - 0.5  # de -0.5 a 0.5
            offset_rad = math.radians(t * spread_total)
            vx = vel_x * math.cos(offset_rad) - vel_y * math.sin(offset_rad)
            vy = vel_x * math.sin(offset_rad) + vel_y * math.cos(offset_rad)
            resultados.append((origen, vx, vy))
        return resultados

    def disparar(self):
        tm = self.game.turn_manager
        if tm.jugador_actual() != self.game.nombre_jugador or not tm.puede_disparar():
            print(f"[DEBUG] {self.game.nombre_jugador} intentó disparar fuera de turno o ya disparó.")
            return

        arma = self.game.robot.arma_equipada
        config = config_arma(arma)
        if not config:
            return

        if not self.tiene_municion(arma, config):
            print(f"[DEBUG] {self.game.nombre_jugador} sin munición para '{arma}'.")
            return

        ancho = config.get("ancho_proyectil", 40)
        alto = config.get("alto_proyectil", 40)
        disparos = self._generar_disparos(config, ancho, alto)

        msg = {
            "tipo": "disparo",
            "jugador": self.game.nombre_jugador,
            "arma": arma,
            "facing_right": self.game.robot.facing_right,
            "disparos": [
                {"x": origen[0], "y": origen[1], "dir_x": vx, "dir_y": vy}
                for origen, vx, vy in disparos
            ],
        }

        # Bloqueo local inmediato: evita que un doble-click dispare dos
        # veces mientras se espera la confirmación por red. La munición
        # se descuenta acá también (por disparo, no por proyectil).
        tm.disparo_hecho = True
        self.consumir_municion(arma, config)

        if self.game.host:
            self.crear_proyectil_host(msg)
        else:
            self.game.enviar(msg)

    def crear_proyectil_host(self, msg):
        """Solo el host llama esto (directo al disparar localmente, o al
        recibir un 'disparo' de un cliente). Crea TODOS los proyectiles
        del disparo (uno o varios si "cantidad" > 1) y arranca la fase
        post_disparo del turno una sola vez."""
        game = self.game
        if not game.host:
            return
        jugador = msg["jugador"]
        arma = msg["arma"]
        if not config_arma(arma):
            print(f"[WeaponManager] Arma desconocida: '{arma}'")
            return

        for disparo in msg.get("disparos", []):
            pid = game._next_proy_id()
            p = Proyectil(
                arma, disparo["x"], disparo["y"], disparo["dir_x"], disparo["dir_y"],
                owner=jugador, facing_right=msg.get("facing_right"),
            )
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
                self._aplicar_empuje(p, robot)
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

    def _aplicar_empuje(self, p, robot):
        """Empuje/knockback opcional al golpear. config.json opcional:
        empuje_ancho (se espeja según hacia dónde miraba el arma al
        golpear) y empuje_alto (negativo = hacia arriba). Si la víctima
        es un jugador remoto, el host no controla su física real (solo
        interpola una copia visual) — se le avisa por red para que su
        propio cliente aplique el empuje a su robot real."""
        empuje_ancho = p.config.get("empuje_ancho", 0)
        empuje_alto = p.config.get("empuje_alto", 0)
        if not empuje_ancho and not empuje_alto:
            return
        direccion = 1 if getattr(p, "_facing_right", True) else -1
        vel_x = empuje_ancho * direccion
        vel_y = empuje_alto
        if robot is self.game.robot:
            robot.aplicar_empuje(vel_x, vel_y)
        else:
            self.game.enviar({
                "tipo": "empuje",
                "jugador": robot.nombre_jugador,
                "vel_x": vel_x,
                "vel_y": vel_y,
            })