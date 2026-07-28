# systems/weapon_manager_free.py
"""
IMPORTANTE: este archivo NO decide a quién le hace daño una explosión —
esa decisión vive ÚNICAMENTE en Proyectil.robots_afectados(). Aquí solo
se itera esa lista y se aplica el daño/puntaje.

Campos opcionales de config.json que maneja este archivo:
  municion            (int)  munición inicial de esa arma. Si no está,
                             el arma es ilimitada. Se descuenta 1 por
                             CADA VEZ que se confirma un disparo (no por
                             cada proyectil que salga de él).
  cantidad            (int)  cuántos proyectiles salen de un solo disparo
                             (por defecto 1), repartidos en abanico.
  dispersion_grados   (float) ancho total del abanico (por defecto 18°).
"""
import math
import pygame
from entities.weapons.proyectil import Proyectil
from utils.weapon_loader import config_arma
from utils.sound_manager import sound_manager


class WeaponManager:
    def __init__(self, game):
        self.game = game
        # {arma_id: cantidad_restante} — solo para armas con "municion"
        # definida en su config.json.
        self.municion_restante = {}
        self.disparos_pendientes = []  # ráfaga escalonada — ver crear_proyectil_host / update
        
    # ------------------------------------------------------------------
    # Munición
    # ------------------------------------------------------------------
    def tiene_municion(self, arma, config):
        return True  # Modo libre: munición infinita para probar armas sin restricciones.

    def consumir_municion(self, arma, config):
        return  # No se descuenta nada en modo libre.

    def municion_actual(self, arma):
        return None  # Sin límite — el HUD no debería mostrar contador aquí.




    # ------------------------------------------------------------------
    # Disparo
    # ------------------------------------------------------------------
    def _generar_disparos(self, config, ancho, alto):
        """Ver mismo método en weapon_manager.py (multijugador) — reparte
        "cantidad" proyectiles en abanico alrededor de la dirección
        apuntada, rotando el vector de velocidad."""
        velocidad_fija = config.get("velocidad_proyectil")
        origen, vel_x, vel_y = self.game.aim.get_datos_disparo(ancho, alto, velocidad_fija=velocidad_fija)
        cantidad = max(1, config.get("cantidad", 1))
        if cantidad == 1:
            return [(origen, vel_x, vel_y)]

        spread_total = config.get("dispersion_grados", 18)
        resultados = []
        for i in range(cantidad):
            t = (i / (cantidad - 1)) - 0.5
            offset_rad = math.radians(t * spread_total)
            vx = vel_x * math.cos(offset_rad) - vel_y * math.sin(offset_rad)
            vy = vel_x * math.sin(offset_rad) + vel_y * math.cos(offset_rad)
            resultados.append((origen, vx, vy))
        return resultados

    def disparar(self):
        arma = self.game.robot.arma_equipada
        config = config_arma(arma)
        if not config:
            return
        if not self.tiene_municion(arma, config):
            print(f"[DEBUG] Sin munición para '{arma}'.")
            return

        ancho = config.get("ancho_proyectil", 40)
        alto = config.get("alto_proyectil", 40)
        self.consumir_municion(arma, config)

        disparos = self._generar_disparos(config, ancho, alto)
        intervalo = config.get("intervalo_disparos_ms", 0)

        angulo_ataque = math.degrees(self.game.aim.get_angulo())

        if intervalo > 0 and len(disparos) > 1:
            ahora = pygame.time.get_ticks()
            for i, (origen, vel_x, vel_y) in enumerate(disparos):
                self.disparos_pendientes.append({
                    "tiempo": ahora + i * intervalo,
                    "arma": arma,
                    "origen": origen, "vel_x": vel_x, "vel_y": vel_y,
                    "facing_right": self.game.robot.facing_right,
                    "angulo_ataque": angulo_ataque,
                })
        else:
            for origen, vel_x, vel_y in disparos:
                p = Proyectil(
                    arma, origen[0], origen[1], vel_x, vel_y,
                    owner=self.game.robot.nombre_jugador,
                    facing_right=self.game.robot.facing_right,
                    angulo_ataque=angulo_ataque,
                )
                self.game.proyectiles.append(p)
            sound_manager.disparo(arma)

    def update(self):
        self._procesar_disparos_pendientes()
        self._update_proyectiles()

    def _procesar_disparos_pendientes(self):
        if not self.disparos_pendientes:
            return
        ahora = pygame.time.get_ticks()
        listos = [d for d in self.disparos_pendientes if d["tiempo"] <= ahora]
        if not listos:
            return
        self.disparos_pendientes = [d for d in self.disparos_pendientes if d["tiempo"] > ahora]
        for d in listos:
            p = Proyectil(
                d["arma"], d["origen"][0], d["origen"][1], d["vel_x"], d["vel_y"],
                owner=self.game.robot.nombre_jugador,
                facing_right=d["facing_right"],
                angulo_ataque=d.get("angulo_ataque"),
            )
            self.game.proyectiles.append(p)
            sound_manager.disparo(d["arma"])

    def draw(self, pantalla):
        for p in self.game.proyectiles:
            p.draw(pantalla)

    def _robots_para_colision(self):
        """p.update() espera una LISTA de robots (no uno solo) y revisa
        colisión en cada sub-paso del movimiento — así se evita que a
        alta velocidad el proyectil traspase a un robot estático."""
        return [r for r in ([self.game.robot] + list(self.game.robots_estaticos)) if not r.is_dead]

    def _update_proyectiles(self):
        for p in self.game.proyectiles[:]:
            candidatos = self._robots_para_colision()
            p.update(self.game.tiles + self.game.tiles_impenetrables, candidatos)
            daño = p.daño

           
            for robot in p.robots_afectados(candidatos):
                robot.take_damage(daño)
                self._aplicar_empuje(p, robot)
                puntos = daño
                if robot.health <= 0:
                    puntos *= 2
                self.game.puntajes[self.game.robot] += puntos
                p.danados.add(robot)

            if p.estado == "done":
                self.game.proyectiles.remove(p)
                
    def _aplicar_empuje(self, p, robot):
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

        robot.aplicar_empuje(vel_x, vel_y)