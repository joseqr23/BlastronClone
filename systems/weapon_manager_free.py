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
from entities.weapons.proyectil import Proyectil
from utils.weapon_loader import config_arma
from utils.sound_manager import sound_manager


class WeaponManager:
    def __init__(self, game):
        self.game = game
        # {arma_id: cantidad_restante} — solo para armas con "municion"
        # definida en su config.json.
        self.municion_restante = {}

    # ------------------------------------------------------------------
    # Munición
    # ------------------------------------------------------------------
    def tiene_municion(self, arma, config):
        limite = config.get("municion")
        if limite is None:
            return True
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

        for origen, vel_x, vel_y in self._generar_disparos(config, ancho, alto):
            p = Proyectil(
                arma, origen[0], origen[1], vel_x, vel_y,
                owner=self.game.robot.nombre_jugador,
                facing_right=self.game.robot.facing_right,
            )
            self.game.proyectiles.append(p)

        sound_manager.disparo(arma)

    def update(self):
        self._update_proyectiles()

    def draw(self, pantalla):
        for p in self.game.proyectiles:
            p.draw(pantalla)

    def _robots_para_colision(self):
        """p.update() espera una LISTA de robots (no uno solo) y revisa
        colisión en cada sub-paso del movimiento — así se evita que a
        alta velocidad el proyectil traspase a un robot estático."""
        return [self.game.robot] + list(self.game.robots_estaticos)

    def _update_proyectiles(self):
        for p in self.game.proyectiles[:]:
            candidatos = self._robots_para_colision()
            # La colisión/rebote/impacto contra tiles y TODOS los robots
            # ya ocurre dentro de p.update(), sub-paso por sub-paso.
            p.update(self.game.tiles, candidatos)
            daño = p.daño

            # Proyectil decide TODO sobre a quién dañar. Aquí solo se aplica.
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
        direccion = 1 if getattr(p, "_facing_right", True) else -1
        robot.aplicar_empuje(empuje_ancho * direccion, empuje_alto)