# entities/weapons/proyectil.py
"""
Proyectil genérico — reemplaza a las clases Granada/Misil separadas.

Toda arma (granada, misil, mina, machete, y cualquiera que agregues
después) es una instancia de esta misma clase, configurada por su
config.json vía utils/weapon_loader.py. Lo único que varía entre armas es
DATA, excepto la física de colisión, que se resuelve mediante un
"comportamiento" (ver COMPORTAMIENTOS al final de este archivo):

    "rebote"          -> rebota contra tiles/robots, solo detona por
                          tiempo (así se comportaba Granada).
    "impacto"         -> detona al primer contacto con tiles o con
                          cualquier robot que no sea su propio dueño, con
                          un breve margen de gracia al salir del arma
                          (así se comportaba Misil).
    "mina"            -> cae, se asienta en el primer tile que toca y se
                          queda fija ahí. Ya no detona por tiempo: solo
                          por contacto directo con un robot o por
                          proximidad (radio configurable vía
                          "radio_proximidad" en el JSON del arma).
    "cuerpo_a_cuerpo" -> no vuela ni choca contra nada: se queda fija en
                          el punto donde se creó y detona por tiempo
                          (tiempo_explosion_ms), igual que la granada.
                          Su dueño NUNCA recibe daño de ella — ver
                          Proyectil.excluye_dueño() y cómo lo usa
                          weapon_manager antes de aplicar cualquier golpe.

Orientación visual: todo proyectil tiene self._facing_right (True = mira
a la derecha, la orientación por defecto del sprite). Para comportamientos
con velocidad real (rebote, mina) se actualiza solo en update() según el
signo de vel_x, y se congela en el último valor conocido cuando vel_x
llega a 0 (mina asentada, granada detenida). Para "cuerpo_a_cuerpo", que
nunca tiene velocidad, DEBE pasarse explícitamente al crear el Proyectil
(ver el parámetro facing_right del constructor) — normalmente
robot.facing_right en el momento del ataque. "impacto" no usa este flag:
ya rota el sprite según el ángulo real de vuelo, lo cual cubre izquierda
y derecha correctamente sin necesidad de flip.

Si algún día necesitas un arma con física genuinamente distinta, se agrega
UNA función más aquí abajo y se registra en COMPORTAMIENTOS — sigue siendo
un único lugar del código, no un archivo nuevo por arma.
"""
import pygame
import math
from utils.sound_manager import sound_manager
from utils.weapon_loader import config_arma


class Proyectil:
    def __init__(self, tipo, x, y, vel_x, vel_y, owner=None, facing_right=None):
        self.tipo = tipo
        self.config = config_arma(tipo) or {}
        self.x = x
        self.y = y
        self.owner = owner
        self.width = self.config.get("ancho_proyectil", 40)
        self.height = self.config.get("alto_proyectil", 40)

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

        # Cuánto antes de detonar pasa de "idle" a "warning" (el frame de
        # "a punto de golpear/explotar"). Por defecto 500ms, igual que
        # siempre — pero armas con un tiempo_explosion_ms muy corto (como
        # un machete) necesitan un umbral más chico, si no "warning" se
        # activa desde el instante de creación y el frame "idle" nunca
        # llega a mostrarse.
        self.advertencia_ms = self.config.get("advertencia_ms", 500)

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

        # Orientación visual — ver docstring del módulo. Si no se pasa
        # explícitamente, se deduce del signo de la velocidad inicial
        # (por defecto mira a la derecha si vel_x es 0).
        self._facing_right = facing_right if facing_right is not None else (vel_x >= 0)

        # Cuántos de los ÚLTIMOS frames del spritesheet se usan para animar
        # la explosión (en vez de mostrar uno solo fijo). Por defecto 1 =
        # el comportamiento de siempre (un único frame estático).
        self.frames_explosion_count = max(1, self.config.get("frames_explosion", 1))

        # Usado por "mina" y "cuerpo_a_cuerpo" (y cualquier otro que
        # necesite congelar por completo la física una vez asentado/fijo).
        # Ver update().
        self._detenida = False

        # Timer LOCAL para animar los frames de explosión (ver draw()).
        # No usa tiempo_eliminar porque en el cliente los proyectiles son
        # "proxies" sincronizados por red — su estado/explotado llega
        # directo del host sin pasar nunca por _detonar(), así que
        # tiempo_eliminar queda en None ahí.
        self._explode_frame_start = None

    @property
    def daño(self):
        return self.config.get("daño", 50)

    def excluye_dueño(self):
        """True si esta arma NUNCA debe hacerle daño a su propio dueño,
        sin importar el tiempo transcurrido ni si se solapan los hitbox."""
        return self.comportamiento == "cuerpo_a_cuerpo"

    def robots_afectados(self, candidatos):
        """Única fuente de verdad de "a quién le hace daño esta explosión
        ahora mismo". weapon_manager NO debe reimplementar ninguna de
        estas reglas — solo debe iterar lo que esto devuelve y aplicar el
        daño. Filtra automáticamente:
          - proyectiles que aún no explotaron (lista vacía)
          - robots que ya recibieron daño de ESTA misma explosión
          - el propio dueño, si el arma lo excluye (ver excluye_dueño())
          - robots cuyo hitbox no se solapa con el de la explosión
        Así, cualquier arma nueva con su propia regla de exclusión queda
        protegida automáticamente sin tocar weapon_manager."""
        if not (self.explotado and self.estado == "explode"):
            return []
        hitbox = self.get_hitbox()
        afectados = []
        for robot in candidatos:
            if robot in self.danados:
                continue
            es_dueño = getattr(robot, "nombre_jugador", None) == self.owner
            if es_dueño and self.excluye_dueño():
                continue
            if hitbox.colliderect(robot.get_rect()):
                afectados.append(robot)
        return afectados

    def get_rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)

    def get_hitbox(self):
        centro_x = self.x + self.width / 2
        centro_y = self.y + self.height / 2
        if self.estado == "explode":
            ancho_visual = self.explosion_width or self.width * 2
            alto_visual = self.explosion_height or self.height * 2
            hitbox_ancho = self.config.get(
                "hitbox_ancho_explosion",
                self.config.get("hitbox_ancho_proyectil", ancho_visual)
            )
            hitbox_alto = self.config.get(
                "hitbox_alto_explosion",
                self.config.get("hitbox_alto_proyectil", alto_visual)
            )
        else:
            hitbox_ancho = self.config.get("hitbox_ancho_proyectil", self.width)
            hitbox_alto = self.config.get("hitbox_alto_proyectil", self.height)
        rect = pygame.Rect(0, 0, hitbox_ancho, hitbox_alto)
        rect.center = (centro_x, centro_y)
        return rect

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
        elif not self.explotado and detona_por_tiempo and self.tiempo_explosion - ahora <= self.advertencia_ms:
            self.estado = "warning"
        elif not self.explotado:
            self.estado = "idle"

        if not self.explotado:
            handler = COMPORTAMIENTOS.get(self.comportamiento, _comportamiento_impacto)
            if self._detenida:
                # Ya está asentada/fija (mina en el suelo, o un arma
                # cuerpo a cuerpo): no se le aplica más física ni
                # movimiento, solo lo que revise el propio handler.
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

            # Orientación visual: se actualiza mientras haya velocidad
            # horizontal real; se congela en el último valor conocido
            # cuando vel_x llega a 0 (reposo). "cuerpo_a_cuerpo" nunca
            # tiene vel_x != 0, así que conserva para siempre el valor
            # que se le pasó al crearlo.
            if self.vel_x > 0:
                self._facing_right = True
            elif self.vel_x < 0:
                self._facing_right = False

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
                angulo = math.degrees(math.atan2(-self.vel_y, self.vel_x))
                frame_render = frame
                if self.vel_x < 0:
                    # Reflejar en vez de rotar el círculo completo: si el vuelo va
                    # hacia la izquierda, rotar 180°+ de más invierte el arte
                    # (ej. detalles que solo están abajo del sprite terminan
                    # arriba). Reflejando primero y rotando solo el ángulo restante,
                    # el misil se ve igual de "derecho" en cualquier dirección.
                    frame_render = pygame.transform.flip(frame, True, False)
                    angulo += 180
                imagen = pygame.transform.rotozoom(frame_render, angulo, 1)
                rect = imagen.get_rect(center=(self.x + self.width // 2, self.y + self.height // 2))
                pantalla.blit(imagen, rect.topleft)
            else:
                imagen = frame if self._facing_right else pygame.transform.flip(frame, True, False)
                pantalla.blit(imagen, (int(self.x), int(self.y)))
        elif self.estado == "explode":
            total_frames = len(self.frames)
            count = min(self.frames_explosion_count, total_frames)
            if count <= 1:
                idx = total_frames - 1
            else:
                if self._explode_frame_start is None:
                    self._explode_frame_start = pygame.time.get_ticks()
                transcurrido = pygame.time.get_ticks() - self._explode_frame_start
                duracion_tramo = max(1, self.tiempo_post_explosion // count)
                paso = min(count - 1, transcurrido // duracion_tramo)
                idx = total_frames - count + paso
            if self.explosion_width and self.explosion_height:
                ancho_exp, alto_exp = self.explosion_width, self.explosion_height
            else:
                ancho_exp, alto_exp = self.width * 2, self.height * 2  # comportamiento original
            frame = self.frames[idx]
            if self.comportamiento != "impacto" and not self._facing_right:
                frame = pygame.transform.flip(frame, True, False)
            imagen = pygame.transform.scale(frame, (ancho_exp, alto_exp))
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
    rect = p.get_hitbox()
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


def _comportamiento_cuerpo_a_cuerpo(p, tiles, robots):
    """Arma cuerpo a cuerpo (ej. machete): no vuela ni choca contra nada,
    se queda fija en el punto donde se creó y detona por TIEMPO
    (tiempo_explosion_ms), igual que la granada. No necesita detectar
    contacto ni pre-marcar a su dueño: la exclusión de daño al dueño la
    garantiza weapon_manager consultando p.excluye_dueño() antes de
    aplicar cualquier golpe — no depende de ningún timing aquí."""
    p._detenida = True


COMPORTAMIENTOS = {
    "rebote": _comportamiento_rebote,
    "impacto": _comportamiento_impacto,
    "mina": _comportamiento_mina,
    "cuerpo_a_cuerpo": _comportamiento_cuerpo_a_cuerpo,
}


# ----------------------------------------------------------------------
# Física de rebote — misma lógica que tenía Granada, ahora reutilizable
# por cualquier arma con comportamiento="rebote".
# ----------------------------------------------------------------------
def _rebote_con_tiles(p, tiles):
    rect = p.get_hitbox()
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
    rect = p.get_hitbox()
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
    rect = p.get_hitbox()
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
    rect = p.get_hitbox()
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