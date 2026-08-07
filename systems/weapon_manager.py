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
import pygame
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
        self.disparos_pendientes = []  # ráfaga escalonada — ver crear_proyectil_host / update
        self.proximo_disparo_libre_ms = 0  # cooldown de disparo en modos sin turnos (ver ModoLibre)

    # ------------------------------------------------------------------
    # Munición
    # ------------------------------------------------------------------
    def tiene_municion(self, arma, config):
        if getattr(self.game.modo, "municion_ilimitada", False):
            return True
        limite = config.get("municion")
        if limite is None:
            return True  # arma ilimitada
        restante = self.municion_restante.setdefault(arma, limite)
        return restante > 0

    def consumir_municion(self, arma, config):
        if getattr(self.game.modo, "municion_ilimitada", False):
            return
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
        modo = self.game.modo
        usa_turnos = getattr(modo, "usa_turnos", True)

        if usa_turnos:
            tm = self.game.turn_manager
            if tm.jugador_actual() != self.game.nombre_jugador or not tm.puede_disparar():
                print(f"[DEBUG] {self.game.nombre_jugador} intentó disparar fuera de turno o ya disparó.")
                return
        elif not self._puede_disparar_libre():
            return

        if self.game.robot.is_dead:
            return

        arma = self.game.robot.arma_equipada
        config = config_arma(arma)
        if not config:
            return

        modo = self.game.modo
        if hasattr(modo, "puede_lanzar") and not modo.puede_lanzar(self.game.nombre_jugador, arma):
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
            "angulo_ataque": math.degrees(self.game.aim.get_angulo()),
            "disparos": [
                {"x": origen[0], "y": origen[1], "dir_x": vx, "dir_y": vy}
                for origen, vx, vy in disparos
            ],
        }

        # Bloqueo inmediato: evita que un doble-click dispare dos veces
        # mientras se espera la confirmación por red.
        if usa_turnos:
            self.game.turn_manager.disparo_hecho = True
        else:
            self._registrar_disparo_libre()
        self.consumir_municion(arma, config)

        if self.game.host:
            self.crear_proyectil_host(msg)
        else:
            self.game.enviar(msg)

    def _puede_disparar_libre(self):
        return pygame.time.get_ticks() >= self.proximo_disparo_libre_ms

    def _registrar_disparo_libre(self):
        cooldown = getattr(self.game.modo, "cooldown_ataque_ms", 1000)
        self.proximo_disparo_libre_ms = pygame.time.get_ticks() + cooldown

    def crear_proyectil_host(self, msg):
        game = self.game
        if not game.host:
            return
        jugador = msg["jugador"]
        arma = msg["arma"]
        config = config_arma(arma)
        if not config:
            print(f"[WeaponManager] Arma desconocida: '{arma}'")
            return
        
        modo = game.modo
        if hasattr(modo, "puede_lanzar") and not modo.puede_lanzar(jugador, arma):
            print(f"[WeaponManager] Lanzamiento de '{arma}' rechazado: {jugador} no es portador válido")
            return

        disparos = msg.get("disparos", [])
        intervalo = config.get("intervalo_disparos_ms", 0)

        if intervalo > 0 and len(disparos) > 1:
            ahora = pygame.time.get_ticks()
            for i, disparo in enumerate(disparos):
                self.disparos_pendientes.append({
                    "tiempo": ahora + i * intervalo,
                    "arma": arma,
                    "x": disparo["x"], "y": disparo["y"],
                    "vel_x": disparo["dir_x"], "vel_y": disparo["dir_y"],
                    "owner": jugador,
                    "facing_right": msg.get("facing_right"),
                    "angulo_ataque": msg.get("angulo_ataque"),
                })
        else:
            for disparo in disparos:
                pid = game._next_proy_id()
                p = Proyectil(
                    arma, disparo["x"], disparo["y"], disparo["dir_x"], disparo["dir_y"],
                    owner=jugador, facing_right=msg.get("facing_right"),
                    angulo_ataque=msg.get("angulo_ataque"),
                )
                p.proj_id = pid
                game.proyectiles.append(p)
            sound_manager.disparo(arma)

        if getattr(game.modo, "usa_turnos", True):
            game.turn_manager.registrar_disparo()

    # ------------------------------------------------------------------
    # Update / draw
    # ------------------------------------------------------------------
    def update(self):
        if self.game.host:
            self._procesar_disparos_pendientes()
            self._update_proyectiles()
        # El cliente no simula física de proyectiles: su estado llega por
        # red vía "proy_sync" y se aplica directo en multi_game.py.

    def _procesar_disparos_pendientes(self):
        if not self.disparos_pendientes:
            return
        ahora = pygame.time.get_ticks()
        listos = [d for d in self.disparos_pendientes if d["tiempo"] <= ahora]
        if not listos:
            return
        self.disparos_pendientes = [d for d in self.disparos_pendientes if d["tiempo"] > ahora]
        for d in listos:
            pid = self.game._next_proy_id()
            p = Proyectil(
                d["arma"], d["x"], d["y"], d["vel_x"], d["vel_y"],
                owner=d["owner"], facing_right=d["facing_right"],
                angulo_ataque=d.get("angulo_ataque"),
            )
            p.proj_id = pid
            self.game.proyectiles.append(p)
            sound_manager.disparo(d["arma"])

    def draw(self, pantalla):
        for p in self.game.proyectiles:
            p.draw(pantalla)

    def _robots_para_colision(self, owner):
        """Todos los robots VIVOS contra los que un proyectil puede
        colisionar. Los robots muertos (is_dead=True) quedan excluidos
        — en modos sin respawn como last man standing, el cuerpo se
        queda visible en pantalla pero ya no bloquea ni recibe daño de
        ningún arma."""
        return [r for r in ([self.game.robot] + list(self.game.robots_estaticos)) if not r.is_dead]

    # ------------------------------------------------------------------
    # Física — SOLO se ejecuta en el host
    # ------------------------------------------------------------------
    def _update_proyectiles(self):
        for p in self.game.proyectiles[:]:
            candidatos = self._robots_para_colision(getattr(p, "owner", None))
            # La colisión/rebote/impacto contra tiles y TODOS los robots
            # ya ocurre dentro de p.update(), sub-paso por sub-paso.
            p.update(self.game.tiles + self.game.tiles_impenetrables, candidatos)
            daño = p.daño

            # Aplicar shake al disparar arma
            if p.explotado and not getattr(p, "_shake_aplicado", False):
                p._shake_aplicado = True
                self.game.activar_shake(
                    p.config.get("sacudida_intensidad", 0),
                    p.config.get("sacudida_duracion_ms", 0),
                )

            # Proyectil decide TODO sobre a quién dañar (colisión,
            # exclusión de dueño, ya-dañados). Aquí solo se aplica.
            for robot in p.robots_afectados(candidatos):
                es_dueño = getattr(p, "owner", None) == robot.nombre_jugador
                modo = getattr(self.game, "modo", None)
                if modo is not None and hasattr(modo, "mismo_equipo") and modo.mismo_equipo(p.owner, robot.nombre_jugador):
                    continue
                moria = self.aplicar_dano(robot, daño, atacante=p.owner)
                puntos = daño * 2 if moria else daño
                self._aplicar_empuje(p, robot)
                # Avisa al modo de partida que este robot recibió un golpe
                # — lo usa ModoBasket para soltar el balón. Se hace acá (no
                # dentro de _aplicar_empuje) para que dispare SIEMPRE que
                # un golpe conecta de verdad, sin importar si esa arma en
                # particular define empuje_ancho/empuje_alto o no.
                modo = getattr(self.game, "modo", None)
                if modo is not None and hasattr(modo, "notificar_golpe"):
                    modo.notificar_golpe(robot)
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

    def aplicar_dano(self, robot, cantidad, atacante=None):
        """Solo se llama desde el host. Aplica el daño localmente, lo
        notifica a todos los clientes, y si este golpe mata al robot,
        dispara el registro de muerte — centralizado aquí para que
        CUALQUIER fuente de daño (armas, zonas dañinas del mapa, lo que
        sea) dispare la muerte de forma consistente, sin que cada
        llamador tenga que reimplementarlo. Devuelve True si este golpe
        mató al robot."""
        if not self.game.host:
            return False
        moria = robot.health > 0 and cantidad >= robot.health and not robot.is_dead
        robot.take_damage(cantidad)
        self.game.enviar({
            "tipo": "damage",
            "jugador": robot.nombre_jugador,
            "cantidad": cantidad,
            "quien": self.game.nombre_jugador,
        })
        if moria:
            self.game.enviar_evento_muerte(atacante, robot)
        return moria

    def _aplicar_empuje(self, p, robot):
        """Empuje/knockback opcional al golpear. config.json opcional:
        empuje_ancho y empuje_alto.

        Para "cuerpo_a_cuerpo_direccional": el empuje sigue la dirección
        REAL del golpe (self.angulo_ataque) — empuje_ancho es la fuerza
        total del impulso en esa dirección (no un valor puramente
        horizontal), y empuje_alto se suma aparte como una elevación
        extra opcional (el "pop" de un golpe cuerpo a cuerpo, incluso
        atacando de costado).

        Para el resto de armas, se mantiene la lógica de siempre:
        empuje_por_impacto (según dónde cayó la explosión) o, por
        defecto, según hacia dónde viajaba/apuntaba el arma."""
        empuje_ancho = p.config.get("empuje_ancho", 0)
        empuje_alto = p.config.get("empuje_alto", 0)
        if not empuje_ancho and not empuje_alto:
            return

        if p.comportamiento == "cuerpo_a_cuerpo_direccional":
            angulo = math.radians(p.angulo_ataque)
            vel_x = empuje_ancho * math.cos(angulo)
            vel_y = empuje_ancho * math.sin(angulo) + empuje_alto
        elif p.config.get("empuje_por_impacto", False):
            centro_impacto_x = p.get_hitbox().centerx
            centro_robot_x = robot.get_centro()[0]
            direccion = 1 if centro_robot_x >= centro_impacto_x else -1
            vel_x = empuje_ancho * direccion
            vel_y = empuje_alto
        else:
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

