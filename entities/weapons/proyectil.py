# entities/weapons/proyectil.py
"""
Proyectil genérico — reemplaza a las clases Granada/Misil separadas.

Toda arma (granada, misil, mina, y cualquiera que agregues después) es una
instancia de esta misma clase, configurada por su config.json vía
utils/weapon_loader.py. Lo único que varía entre armas es DATA, excepto
la física de colisión, que se resuelve mediante un "comportamiento"
(ver COMPORTAMIENTOS al final de este archivo):

    "rebote"   -> rebota contra tiles/robots, solo detona por tiempo
                  (así se comportaba Granada).
    "impacto"  -> detona al primer contacto con tiles o con cualquier
                  robot que no sea su propio dueño, con un breve margen
                  de gracia al salir del arma (así se comportaba Misil).
    "mina"     -> cae, se asienta en el primer tile que toca y se queda
                  fija ahí. Ya no detona por tiempo: solo por contacto
                  directo con un robot o por proximidad (radio configurable
                  vía "radio_proximidad" en el JSON del arma).

Si algún día necesitas un arma con física genuinamente distinta, se agrega
UNA función más aquí abajo y se registra en COMPORTAMIENTOS — sigue siendo
un único lugar del código, no un archivo nuevo por arma.
"""
import pygame
import math
from utils.sound_manager import sound_manager
from utils.weapon_loader import config_arma


class Proyectil:
    def __init__(self, tipo, x, y, vel_x, vel_y, owner=None):
        self.tipo = tipo
        self.config = config_arma(tipo) or {}
        self.x = x
        self.y = y
        self.owner = owner
        self.width = self.config.get("ancho", 40)
        self.height = self.config.get("alto", 40)
        # Tamaño de la EXPLOSIÓN, si el arma lo define aparte del tamaño
        # del proyectil (p. ej. un misil grande con una onda expansiva aún
        # más grande). Si no se especifica, se mantiene el comportamiento
        # de siempre: la animación se dibuja al doble del tamaño del
        # proyectil, y el hitbox de daño usa el tamaño normal del proyectil
        # — así no le cambia el balance a ningún arma existente.
        self.explosion_width = self.config.get("ancho_explosion")
        self.explosion_height = self.config.get("alto_explosion")
        self.danados = set()

        ahora = pygame.time.get_ticks()
        self.tiempo_explosion = ahora + self.config.get("tiempo_explosion_ms", 3000)
        self.tiempo_post_explosion = self.config.get("tiempo_post_explosion_ms", 500)
        self.tiempo_eliminar = None
        self.tiempo_creacion = ahora
        self.margen_dueño_ms = self.config.get("margen_dueño_ms", 250)

        self.frames = self.config.get("_frames_img") or []
        self.estado = "idle"
        self.frame_index = 0
        self.explotado = False
        self.muerta = False
        self.ya_hizo_dano = False

        self.vel_x = vel_x
        self.vel_y = vel_y
        self.gravity = self.config.get("gravedad", 0.5)
        self.friccion_aire = self.config.get("friccion_aire", 0.99)
        self.friccion_rebote = self.config.get("friccion_rebote", 0.6)

        self.comportamiento = self.config.get("comportamiento", "impacto")

        # Usado por el comportamiento "mina" (y cualquier otro que necesite
        # congelar por completo la física una vez asentado). Ver update().
        self._detenida = False

    @property
    def daño(self):
        return self.config.get("daño", 50)

    def get_rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)

    def get_hitbox(self):
        if self.estado == "explode" and self.explosion_width and self.explosion_height:
            # Arma con explosión de tamaño propio: el área de daño se
            # centra en el mismo punto que el proyectil, pero con las
            # dimensiones de la explosión (no las del proyectil).
            padding_x = self.config.get("hitbox_padding_x_explosion",
                                         self.config.get("hitbox_padding_x", 4))
            padding_y = self.config.get("hitbox_padding_y_explosion",
                                         self.config.get("hitbox_padding_y", 8))
            centro_x = self.x + self.width / 2
            centro_y = self.y + self.height / 2
            rect = pygame.Rect(0, 0, self.explosion_width, self.explosion_height)
            rect.center = (centro_x, centro_y)
        else:
            padding_x = self.config.get("hitbox_padding_x", 4)
            padding_y = self.config.get("hitbox_padding_y", 8)
            rect = self.get_rect()

        return pygame.Rect(
            rect.left - padding_x, rect.top - padding_y,
            rect.width + 2 * padding_x, rect.height + 2 * padding_y
        )

    def _detonar(self):
        if self.explotado:
            return
        ahora = pygame.time.get_ticks()
        self.estado = "explode"
        self.explotado = True
        self.tiempo_eliminar = ahora + self.tiempo_post_explosion
        sound_manager.explosion(self.tipo)

    def update(self, tiles, robots):
        """robots: lista de robots contra los que puede colisionar. Se
        revisa colisión en CADA sub-paso del movimiento, no solo al final
        del frame, para evitar tunneling a alta velocidad."""
        ahora = pygame.time.get_ticks()

        # La mina no detona por tiempo — solo por contacto/proximidad.
        detona_por_tiempo = self.comportamiento != "mina"

        if not self.explotado and detona_por_tiempo and ahora >= self.tiempo_explosion:
            self._detonar()
        elif not self.explotado and detona_por_tiempo and self.tiempo_explosion - ahora <= 500:
            self.estado = "warning"
        elif not self.explotado:
            self.estado = "idle"

        if not self.explotado:
            handler = COMPORTAMIENTOS.get(self.comportamiento, _comportamiento_impacto)
            if self._detenida:
                # Ya está asentada (p. ej. una mina en el suelo): no se le
                # aplica más física ni movimiento, solo se revisa si algo
                # la activa (proximidad/contacto).
                handler(self, tiles, robots)
            else:
                self.vel_y += self.gravity
                pasos = int(max(abs(self.vel_x), abs(self.vel_y)) // 5) + 1
                dx = self.vel_x / pasos
                dy = self.vel_y / pasos
                for _ in range(pasos):
                    self.x += dx
                    self.y += dy
                    handler(self, tiles, robots)
                    if self._detenida:
                        break
                self.vel_x *= self.friccion_aire

        if self.explotado and ahora >= self.tiempo_eliminar:
            self.estado = "done"
            self.muerta = True

    def draw(self, pantalla):
        if not self.frames:
            return
        if self.estado in ("idle", "warning"):
            idx = 0 if self.estado == "idle" else min(1, len(self.frames) - 1)
            frame = self.frames[idx]
            if self.comportamiento == "impacto":
                # Rota el sprite según la dirección de vuelo (como el misil).
                angulo = math.degrees(math.atan2(-self.vel_y, self.vel_x))
                imagen = pygame.transform.rotozoom(frame, angulo, 1)
                rect = imagen.get_rect(center=(self.x + self.width // 2, self.y + self.height // 2))
                pantalla.blit(imagen, rect.topleft)
            else:
                pantalla.blit(frame, (int(self.x), int(self.y)))
        elif self.estado == "explode":
            idx = min(2, len(self.frames) - 1)
            if self.explosion_width and self.explosion_height:
                ancho_exp, alto_exp = self.explosion_width, self.explosion_height
            else:
                ancho_exp, alto_exp = self.width * 2, self.height * 2  # comportamiento original
            imagen = pygame.transform.scale(self.frames[idx], (ancho_exp, alto_exp))
            centro_x = self.x + self.width / 2
            centro_y = self.y + self.height / 2
            rect = imagen.get_rect(center=(centro_x, centro_y))
            pantalla.blit(imagen, rect.topleft)


# ----------------------------------------------------------------------
# Comportamientos — un handler por tipo de física de colisión. Se llama
# una vez por cada sub-paso del movimiento (ver update() arriba).
# ----------------------------------------------------------------------
def _comportamiento_rebote(p, tiles, robots):
    """Rebota contra tiles y robots según su velocidad. Nunca detona por
    contacto, solo por tiempo (igual que la granada original)."""
    _rebote_con_tiles(p, tiles)
    for robot in robots:
        _rebote_con_robot(p, robot)


def _comportamiento_impacto(p, tiles, robots):
    """Detona al primer contacto con un tile o con cualquier robot que no
    sea su propio dueño (con margen de gracia al salir), igual que el
    misil original."""
    rect = p.get_rect()
    for tile in tiles:
        if rect.colliderect(tile.rect):
            p._detonar()
            return
    ahora = pygame.time.get_ticks()
    for robot in robots:
        es_dueño = getattr(robot, "nombre_jugador", None) == p.owner
        if es_dueño and ahora < p.tiempo_creacion + p.margen_dueño_ms:
            continue
        robot_rect = robot.get_hitbox_lateral()
        if rect.colliderect(robot_rect):
            p._detonar()
            return


def _comportamiento_mina(p, tiles, robots):
    """Cae, se asienta en el primer tile que toca y se congela ahí (ver
    _asentar_en_tiles). Una vez asentada, detona por contacto directo con
    un robot o porque alguno entró en su radio de proximidad."""
    if not p._detenida:
        _asentar_en_tiles(p, tiles)
    _revisar_proximidad(p, robots)


COMPORTAMIENTOS = {
    "rebote": _comportamiento_rebote,
    "impacto": _comportamiento_impacto,
    "mina": _comportamiento_mina,
}


# ----------------------------------------------------------------------
# Física de rebote — misma lógica que tenía Granada, ahora reutilizable
# por cualquier arma con comportamiento="rebote".
# ----------------------------------------------------------------------
def _rebote_con_tiles(p, tiles):
    rect = p.get_rect()
    umbral_suave = 1.0
    for tile in tiles:
        if rect.colliderect(tile.rect):
            velocidad_actual = max(abs(p.vel_x), abs(p.vel_y))
            factor_rebote = p.friccion_rebote * 0.3 if velocidad_actual < umbral_suave else p.friccion_rebote
            if p.vel_y >= 0 and rect.bottom <= tile.rect.bottom:
                p.y = tile.rect.top - p.height
                p.vel_y *= -factor_rebote
            elif p.vel_y < 0 and rect.top <= tile.rect.bottom and rect.top >= tile.rect.bottom - 10:
                p.y = tile.rect.bottom
                p.vel_y *= -factor_rebote
            elif abs(rect.right - tile.rect.left) < 10 and p.vel_x > 0:
                p.x = tile.rect.left - p.width
                p.vel_x *= -factor_rebote
            elif abs(rect.left - tile.rect.right) < 10 and p.vel_x < 0:
                p.x = tile.rect.right
                p.vel_x *= -factor_rebote

            if abs(p.vel_x) < 0.1:
                p.vel_x = 0
            elif abs(p.vel_x) < 0.5:
                p.vel_x *= 0.5
            if abs(p.vel_y) < 0.1:
                p.vel_y = 0
            elif abs(p.vel_y) < 0.5:
                p.vel_y *= 0.5


def _rebote_con_robot(p, robot):
    rect = p.get_rect()
    robot_rect = robot.get_hitbox_lateral()
    if rect.colliderect(robot_rect):
        umbral_suave = 1.0
        velocidad_actual = max(abs(p.vel_x), abs(p.vel_y))
        factor_rebote = p.friccion_rebote * 0.3 if velocidad_actual < umbral_suave else p.friccion_rebote
        if robot.vel_y != 0:
            factor_rebote *= 1.5

        if abs(rect.right - robot_rect.left) < 10 and p.vel_x > 0:
            p.x = robot_rect.left - p.width
            p.vel_x *= -factor_rebote
        elif abs(rect.left - robot_rect.right) < 10 and p.vel_x < 0:
            p.x = robot_rect.right
            p.vel_x *= -factor_rebote
        elif p.vel_y < 0 and rect.top <= robot_rect.bottom and abs(rect.top - robot_rect.bottom) < 10:
            p.y = robot_rect.bottom
            p.vel_y *= -factor_rebote
        elif p.vel_y >= 0 and rect.bottom >= robot_rect.top and abs(rect.bottom - robot_rect.top) < 10:
            p.y = robot_rect.top - p.height
            p.vel_y *= -factor_rebote

        if abs(p.vel_x) < 0.1:
            p.vel_x = 0
        elif abs(p.vel_x) < 0.5:
            p.vel_x *= 0.5
        if abs(p.vel_y) < 0.1:
            p.vel_y = 0
        elif abs(p.vel_y) < 0.5:
            p.vel_y *= 0.5


# ----------------------------------------------------------------------
# Física de la mina — se congela apenas toca un tile (ver _detenida en
# Proyectil.update, que corta el resto de la física una vez True).
# ----------------------------------------------------------------------
def _asentar_en_tiles(p, tiles):
    rect = p.get_rect()
    for tile in tiles:
        if rect.colliderect(tile.rect):
            if p.vel_y >= 0:
                p.y = tile.rect.top - p.height
            p.vel_x = 0
            p.vel_y = 0
            p._detenida = True
            return


def _revisar_proximidad(p, robots):
    radio = p.config.get("radio_proximidad", 45)
    centro_x = p.x + p.width / 2
    centro_y = p.y + p.height / 2
    ahora = pygame.time.get_ticks()
    rect = p.get_rect()
    for robot in robots:
        es_dueño = getattr(robot, "nombre_jugador", None) == p.owner
        if es_dueño and ahora < p.tiempo_creacion + p.margen_dueño_ms:
            continue
        robot_rect = robot.get_hitbox_lateral()

        # Contacto directo -> detona sin importar el radio configurado.
        if rect.colliderect(robot_rect):
            p._detonar()
            return

        # Proximidad: distancia del centro de la mina al punto más cercano
        # del hitbox del robot.
        rx = max(robot_rect.left, min(centro_x, robot_rect.right))
        ry = max(robot_rect.top, min(centro_y, robot_rect.bottom))
        dist = math.hypot(centro_x - rx, centro_y - ry)
        if dist <= radio:
            p._detonar()
            return