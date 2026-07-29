# ui/hud.py
import pygame
from entities.players.robot import Robot
from utils.weapon_loader import cargar_armas
from settings import ANCHO
import math
from utils.paths import resource_path # Para exportar en main.exe PyInstaller

COL_PANEL_FONDO = (14, 14, 18, 220)
COL_PANEL_BORDE = (255, 196, 60)
COL_BOTON_IDLE = (42, 42, 50)
COL_BOTON_HOVER = (65, 65, 76)
COL_BOTON_SELECCIONADO = (60, 90, 45)
COL_BORDE_SELECCIONADO = (255, 196, 60)
COL_BORDE_BOTON = (90, 90, 100)
COL_LABEL_CATEGORIA = (200, 200, 210)
COL_SCROLLBAR = (255, 196, 60, 210)
COL_SCROLLBAR_RIEL = (255, 255, 255, 25)
 
ALTO_LABEL_CATEGORIA = 18

def _draw_crown(pantalla, x, y, size=14, color=(255, 215, 0)):
    """Dibuja una corona simple (sin depender de ninguna imagen) junto al
    primer lugar del marcador de puntajes."""
    base_y = y + size
    puntos = [
        (x, base_y),
        (x, y + size * 0.4),
        (x + size * 0.25, y + size * 0.7),
        (x + size * 0.5, y),
        (x + size * 0.75, y + size * 0.7),
        (x + size, y + size * 0.4),
        (x + size, base_y),
    ]
    pygame.draw.polygon(pantalla, color, puntos)
    pygame.draw.polygon(pantalla, (150, 110, 0), puntos, width=1)




class HUDArmas:
    """
    Selector de armas en cuadrícula, agrupado por categoría ("tipo" en el
    config.json de cada arma) y con scroll vertical: el panel nunca crece
    más allá de `filas_visibles` filas, sin importar cuántas armas nuevas
    agregues — desplazás con la rueda del mouse dentro del panel.
 
    Incluye:
      - Botón de colapsar/expandir a la derecha de la cuadrícula. Al
        colapsar se muestra un pequeño indicador con el arma
        actualmente seleccionada al lado del botón.
      - Panel de fondo semitransparente con bordes redondeados.
      - Tooltip con el nombre legible del arma al pasar el mouse.
      - Indicador de munición restante (opcional vía weapon_manager).
      - Cualquier clic dentro del panel (huecos entre botones incluidos)
        cuenta como "sobre el HUD" — no solo los botones — para que
        nunca se dispare sin querer al clickear al costado de un arma.
 
    Íconos: busca assets/hud/<arma>.png primero; si no existe, usa el
    primer frame del sprite propio del arma como ícono automático.
    """
 
    def __init__(self, armas_disponibles, posicion=(600, 10), margen_derecho=20,
                 max_por_fila=None, filas_visibles=3):
        self.armas = ['nada', 'spawn_robot'] + armas_disponibles
        self.pos = posicion
        self.seleccion = 'nada'
        self.colapsado = True
 
        self.ancho_boton = 60
        self.alto_boton = 60
        self.padding = 10
        self.ancho_toggle = 30
        self.margen_derecho = margen_derecho
        self.max_por_fila = max_por_fila
        self.filas_visibles = max(1, filas_visibles)
        self.scroll_px = 0
 
        self.botones = []               # (arma, rect_local) — coords dentro del contenido scrolleable
        self.categorias_layout = []      # (etiqueta, y_local)
        self.rect_toggle = pygame.Rect(0, 0, 0, 0)
        self.rect_viewport = pygame.Rect(0, 0, 0, 0)
        self.rect_panel = pygame.Rect(0, 0, 0, 0)
        self.rect_panel_colapsado = pygame.Rect(0, 0, 0, 0)
        self.rect_indicador_colapsado = pygame.Rect(0, 0, 0, 0)
        self.ancho_indicador_colapsado = 44
        self.alto_contenido_total = self.alto_boton
        self.ancho_contenido = self.ancho_boton
 
        self.imagenes = {}
        self.nombres_legibles = {}
        self.font_toggle = pygame.font.SysFont("Arial", 20, bold=True)
        self.font_tooltip = pygame.font.SysFont("Arial", 14, bold=True)
        self.font_municion = pygame.font.SysFont("Arial", 13, bold=True)
        self.font_categoria = pygame.font.SysFont("Arial", 11, bold=True)
 
        self.crear_botones()
        self.cargar_imagenes()
 
    # ------------------------------------------------------------------
    # Categorías
    # ------------------------------------------------------------------
    def _agrupar_armas(self):
        catalogo = cargar_armas()
        categorias = {}
        for arma in self.armas:
            if arma in ('nada', 'spawn_robot'):
                continue
            config = catalogo.get(arma, {})
            tipo = config.get("tipo") or "Otras"
            categorias.setdefault(tipo, []).append(arma)

        grupos = [("", ['nada', 'spawn_robot'])] + list(categorias.items())
        return grupos
 
    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _calcular_por_fila(self):
        if self.max_por_fila is not None:
            return max(1, self.max_por_fila)
        disponible = max(
            self.ancho_boton,
            (ANCHO - self.margen_derecho) - self.pos[0] - self.ancho_toggle - self.padding
        )
        return max(1, int((disponible + self.padding) // (self.ancho_boton + self.padding)))
 
    def crear_botones(self):
        x, y = self.pos
        por_fila = self._calcular_por_fila()
        grupos = self._agrupar_armas()
 
        self.botones = []
        self.categorias_layout = []
        y_local = 0
        ancho_contenido = por_fila * (self.ancho_boton + self.padding) - self.padding
 
        for etiqueta, armas_grupo in grupos:
            if not armas_grupo:
                continue
            if etiqueta:
                self.categorias_layout.append((etiqueta, y_local))
                y_local += ALTO_LABEL_CATEGORIA
            for i, arma in enumerate(armas_grupo):
                fila, col = divmod(i, por_fila)
                rect = pygame.Rect(
                    col * (self.ancho_boton + self.padding),
                    y_local + fila * (self.alto_boton + self.padding),
                    self.ancho_boton, self.alto_boton,
                )
                self.botones.append((arma, rect))
            filas_grupo = (len(armas_grupo) - 1) // por_fila + 1
            y_local += filas_grupo * (self.alto_boton + self.padding) - self.padding
            y_local += 10  # separación entre categorías
 
        self.ancho_contenido = ancho_contenido
        self.alto_contenido_total = max(y_local, self.alto_boton)
 
        alto_viewport_max = self.filas_visibles * (self.alto_boton + self.padding) - self.padding + ALTO_LABEL_CATEGORIA
        self.alto_viewport = min(self.alto_contenido_total, alto_viewport_max)
        self.rect_viewport = pygame.Rect(x, y, ancho_contenido, self.alto_viewport)
 
        max_scroll = max(0, self.alto_contenido_total - self.alto_viewport)
        self.scroll_px = min(self.scroll_px, max_scroll)
 
        x_toggle = x + ancho_contenido + self.padding
        self.rect_toggle = pygame.Rect(x_toggle, y, self.ancho_toggle, self.alto_boton)
 
        self.rect_indicador_colapsado = pygame.Rect(
            self.rect_toggle.left - self.padding - self.ancho_indicador_colapsado,
            self.rect_toggle.top, self.ancho_indicador_colapsado, self.alto_boton,
        )
        self.rect_panel_colapsado = self.rect_indicador_colapsado.union(self.rect_toggle).inflate(6, 6)
 
        margen = 6
        self.rect_panel = pygame.Rect(
            x - margen, y - margen,
            ancho_contenido + self.padding + self.ancho_toggle + margen * 2,
            max(self.alto_boton, self.alto_viewport) + margen * 2,
        )
 
    # ------------------------------------------------------------------
    # Recursos
    # ------------------------------------------------------------------
    def cargar_imagenes(self):
        catalogo = cargar_armas()
        for arma in self.armas:
            imagen = None
            try:
                imagen = pygame.image.load(resource_path(f"assets/hud/{arma}.png")).convert_alpha()  # Para exportar en main.exe PyInstaller
                imagen = pygame.transform.smoothscale(imagen, (40, 40))
            except Exception:
                config = catalogo.get(arma)
                frames = config.get("_frames_img") if config else None
                if frames:
                    try:
                        imagen = pygame.transform.smoothscale(frames[0], (40, 40))
                    except Exception:
                        imagen = None
            self.imagenes[arma] = imagen
 
            config = catalogo.get(arma)
            if config and config.get("nombre"):
                self.nombres_legibles[arma] = config["nombre"]
            elif arma == 'nada':
                self.nombres_legibles[arma] = 'Ninguna'
            elif arma == 'spawn_robot':
                self.nombres_legibles[arma] = 'Invocar robot'
            else:
                self.nombres_legibles[arma] = arma.capitalize()
 
    # ------------------------------------------------------------------
    # Eventos
    # ------------------------------------------------------------------
    def punto_sobre_hud(self, pos):
        if self.colapsado:
            return self.rect_panel_colapsado.collidepoint(pos)
        return self.rect_panel.collidepoint(pos)
 
    def manejar_evento(self, evento):
        if evento.type == pygame.MOUSEBUTTONDOWN:
            pos = evento.pos
            if evento.button == 1:
                if self.rect_toggle.collidepoint(pos):
                    self.colapsado = not self.colapsado
                    return None
                if self.colapsado or not self.rect_viewport.collidepoint(pos):
                    return None
                local = (pos[0] - self.rect_viewport.x, pos[1] - self.rect_viewport.y + self.scroll_px)
                for arma, rect in self.botones:
                    if rect.collidepoint(local):
                        self.seleccion = arma
                        return arma
            elif not self.colapsado and self.rect_viewport.collidepoint(pos) and evento.button in (4, 5):
                max_scroll = max(0, self.alto_contenido_total - self.alto_viewport)
                paso = self.alto_boton + self.padding
                if evento.button == 4:    # rueda arriba
                    self.scroll_px = max(0, self.scroll_px - paso)
                else:                     # rueda abajo
                    self.scroll_px = min(max_scroll, self.scroll_px + paso)
        return None
 
    # ------------------------------------------------------------------
    # Dibujo
    # ------------------------------------------------------------------
    def draw(self, pantalla, font, weapon_manager=None):
        panel = self.rect_panel_colapsado if self.colapsado else self.rect_panel
        fondo = pygame.Surface((panel.width, panel.height), pygame.SRCALPHA)
        fondo.fill(COL_PANEL_FONDO)
        pantalla.blit(fondo, panel.topleft)
        pygame.draw.rect(pantalla, COL_PANEL_BORDE, panel, width=2, border_radius=10)
 
        mouse_pos = pygame.mouse.get_pos()
        toggle_color = COL_BOTON_HOVER if self.rect_toggle.collidepoint(mouse_pos) else COL_BOTON_IDLE
        pygame.draw.rect(pantalla, toggle_color, self.rect_toggle, border_radius=6)
        pygame.draw.rect(pantalla, COL_PANEL_BORDE, self.rect_toggle, width=2, border_radius=6)
        flecha = "G" if self.colapsado else "G"
        texto_flecha = self.font_toggle.render(flecha, True, (255, 255, 255))
        pantalla.blit(texto_flecha, texto_flecha.get_rect(center=self.rect_toggle.center))
 
        if self.colapsado:
            # Indicador del arma actualmente equipada, al lado del toggle.
            pygame.draw.rect(pantalla, COL_BOTON_IDLE, self.rect_indicador_colapsado, border_radius=8)
            pygame.draw.rect(pantalla, COL_BORDE_SELECCIONADO, self.rect_indicador_colapsado, width=2, border_radius=8)
            imagen = self.imagenes.get(self.seleccion)
            if imagen:
                pantalla.blit(imagen, imagen.get_rect(center=self.rect_indicador_colapsado.center))
            else:
                texto = self.nombres_legibles.get(self.seleccion, self.seleccion.capitalize())
                render = font.render(texto, True, (235, 235, 235))
                pantalla.blit(render, render.get_rect(center=self.rect_indicador_colapsado.center))
            return
 
        # Contenido completo (todas las categorías/armas) se dibuja en una
        # superficie aparte; solo se muestra el recorte que corresponde
        # al scroll actual — así el panel visible nunca crece.
        contenido = pygame.Surface((self.ancho_contenido, self.alto_contenido_total), pygame.SRCALPHA)
        for etiqueta, y_local in self.categorias_layout:
            render_etiqueta = self.font_categoria.render(etiqueta.upper(), True, COL_LABEL_CATEGORIA)
            contenido.blit(render_etiqueta, (2, y_local + 2))
 
        mouse_local = (mouse_pos[0] - self.rect_viewport.x, mouse_pos[1] - self.rect_viewport.y + self.scroll_px)
        hover = None
        for arma, rect in self.botones:
            seleccionado = self.seleccion == arma
            sobre = rect.collidepoint(mouse_local)
            if seleccionado:
                color, borde, grosor = COL_BOTON_SELECCIONADO, COL_BORDE_SELECCIONADO, 3
            elif sobre:
                color, borde, grosor = COL_BOTON_HOVER, COL_BORDE_BOTON, 2
            else:
                color, borde, grosor = COL_BOTON_IDLE, COL_BORDE_BOTON, 1
            pygame.draw.rect(contenido, color, rect, border_radius=8)
            pygame.draw.rect(contenido, borde, rect, width=grosor, border_radius=8)
 
            imagen = self.imagenes.get(arma)
            if imagen:
                contenido.blit(imagen, imagen.get_rect(center=rect.center))
            else:
                texto_mostrar = self.nombres_legibles.get(arma, arma.capitalize())
                text = font.render(texto_mostrar, True, (235, 235, 235))
                contenido.blit(text, text.get_rect(center=rect.center))
 
            if weapon_manager is not None:
                self._draw_municion(contenido, arma, rect, weapon_manager)
 
            if sobre:
                hover = (arma, rect)
 
        recorte = pygame.Rect(0, self.scroll_px, self.ancho_contenido, self.rect_viewport.height)
        pantalla.blit(contenido.subsurface(recorte), self.rect_viewport.topleft)
 
        if self.alto_contenido_total > self.rect_viewport.height:
            self._draw_scrollbar(pantalla)
 
        if hover is not None:
            arma_hover, rect_local = hover
            rect_pantalla = rect_local.move(self.rect_viewport.x, self.rect_viewport.y - self.scroll_px)
            self._draw_tooltip(pantalla, arma_hover, rect_pantalla)
 
    def _draw_scrollbar(self, pantalla):
        vp = self.rect_viewport
        riel_rect = pygame.Rect(vp.right - 5, vp.y, 3, vp.height)
        riel = pygame.Surface(riel_rect.size, pygame.SRCALPHA)
        riel.fill(COL_SCROLLBAR_RIEL)
        pantalla.blit(riel, riel_rect.topleft)
 
        max_scroll = self.alto_contenido_total - vp.height
        ratio_visible = vp.height / self.alto_contenido_total
        alto_barra = max(14, int(vp.height * ratio_visible))
        pos_barra = int((self.scroll_px / max_scroll) * (vp.height - alto_barra)) if max_scroll else 0
        barra_rect = pygame.Rect(riel_rect.x, riel_rect.y + pos_barra, 3, alto_barra)
        barra = pygame.Surface(barra_rect.size, pygame.SRCALPHA)
        barra.fill(COL_SCROLLBAR)
        pantalla.blit(barra, barra_rect.topleft)
 
    def _draw_municion(self, pantalla, arma, rect, weapon_manager):
        restante = weapon_manager.municion_actual(arma)
        if restante is None:
            return
        texto = self.font_municion.render(str(restante), True, (255, 255, 255))
        fondo_rect = texto.get_rect()
        fondo_rect.inflate_ip(8, 4)
        fondo_rect.bottomright = (rect.right - 2, rect.bottom - 2)
        color_fondo = (200, 40, 40) if restante == 0 else (25, 25, 30)
        pygame.draw.rect(pantalla, color_fondo, fondo_rect, border_radius=5)
        pygame.draw.rect(pantalla, (255, 255, 255), fondo_rect, width=1, border_radius=5)
        pantalla.blit(texto, texto.get_rect(center=fondo_rect.center))
 
    def _draw_tooltip(self, pantalla, arma, rect):
        texto = self.nombres_legibles.get(arma, arma.capitalize())
        render = self.font_tooltip.render(texto, True, (255, 255, 255))
        padding = 5
        fondo_rect = render.get_rect()
        fondo_rect.inflate_ip(padding * 2, padding * 2)
        fondo_rect.midtop = (rect.centerx, rect.bottom + 6)
        if fondo_rect.right > ANCHO:
            fondo_rect.right = ANCHO - 2
        fondo = pygame.Surface(fondo_rect.size, pygame.SRCALPHA)
        fondo.fill((10, 10, 14, 230))
        pantalla.blit(fondo, fondo_rect.topleft)
        pygame.draw.rect(pantalla, COL_PANEL_BORDE, fondo_rect, width=1, border_radius=5)
        pantalla.blit(render, render.get_rect(center=fondo_rect.center))


class HUDPuntajes:
    """Marcador de puntajes para el modo libre. Ordenado de mayor a menor;
    el primer lugar siempre lleva una corona al lado del nombre."""

    def __init__(self, game, posicion=(10, 10)):
        self.game = game
        self.pos = posicion
        self.font = pygame.font.SysFont("Arial", 17, bold=True)
        self.font_title = pygame.font.SysFont("Arial", 20, bold=True)

    def _entradas(self):
        entradas = [(
            self.game.robot.nombre_jugador,
            self.game.puntajes.get(self.game.robot, 0),
            getattr(self.game.robot, "color_nombre", (0, 0, 0)),
        )]
        for robot in self.game.robots_estaticos:
            if not robot.is_dead:
                entradas.append((
                    robot.nombre_jugador,
                    self.game.puntajes.get(robot, 0),
                    getattr(robot, "color_nombre", (0, 0, 0)),
                ))
        entradas.sort(key=lambda e: e[1], reverse=True)
        return entradas

    def draw(self, pantalla):
        x, y = self.pos
        titulo = self.font_title.render("Puntuación", True, (0, 0, 0))
        pantalla.blit(titulo, (x, y))
        y += 25
        for i, (nombre, score, color) in enumerate(self._entradas()):
            text_x = x
            if i == 0:
                _draw_crown(pantalla, x, y - 2)
                text_x = x + 20
            texto = self.font.render(f"{nombre}: {score}", True, color)
            pantalla.blit(texto, (text_x, y))
            y += 20


class HUDPuntajesMultiplayer:
    """Marcador para multijugador. Ordenado de mayor a menor según lo que
    defina el modo de partida activo (puntaje, muertes, o vida restante
    en last man standing); el primer lugar lleva corona, y tu propia
    fila queda resaltada."""
    def __init__(self, game, posicion=(10, 10)):
        self.game = game
        self.pos = posicion
        self.font = pygame.font.SysFont("Arial", 16, bold=True)
        self.font_title = pygame.font.SysFont("Arial", 19, bold=True)

    def _entradas(self):
        valores = self.game.modo.valores_actuales()
        entradas = []
        for jugador, valor in valores.items():
            if self.game.robot and self.game.robot.nombre_jugador == jugador:
                robot = self.game.robot
            else:
                robot = self.game.robots_remotos.get(jugador)
            color = getattr(robot, "color_nombre", (255, 255, 255)) if robot else (255, 255, 255)
            entradas.append((jugador, valor, color))
        entradas.sort(key=lambda e: e[1], reverse=True)
        return entradas

    def _texto_con_borde(self, superficie, texto, pos, color, fuente):
        render_borde = fuente.render(texto, True, (0, 0, 0))
        render = fuente.render(texto, True, color)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                superficie.blit(render_borde, (pos[0] + dx, pos[1] + dy))
        superficie.blit(render, pos)

    def draw(self, pantalla):
        entradas = self._entradas()
        if not entradas:
            return

        max_valor = max((abs(v) for _, v, _ in entradas), default=1) or 1
        alto_fila = 26
        ancho_panel = 220
        alto_panel = 34 + alto_fila * len(entradas) + 8

        superficie = pygame.Surface((ancho_panel, alto_panel), pygame.SRCALPHA)
        pygame.draw.rect(superficie, (20, 20, 20, 160), superficie.get_rect(), border_radius=12)
        pygame.draw.rect(superficie, (255, 215, 0, 200), superficie.get_rect(), width=2, border_radius=12)

        self._texto_con_borde(superficie, self.game.modo.etiqueta_actual(), (14, 8), (255, 255, 255), self.font_title)

        y = 34
        for i, (jugador, valor, color) in enumerate(entradas):
            es_yo = jugador == self.game.nombre_jugador
            fila_rect = pygame.Rect(6, y, ancho_panel - 12, alto_fila - 4)
            if es_yo:
                pygame.draw.rect(superficie, (255, 255, 255, 35), fila_rect, border_radius=8)

            text_x = 12
            if i == 0:
                _draw_crown(superficie, text_x, y - 1)
                text_x += 20

            nombre = f"{jugador}{' (Tú)' if es_yo else ''}"
            self._texto_con_borde(superficie, f"{nombre}: {valor}", (text_x, y), color, self.font)

            # Mini barra proporcional al valor más alto de la lista
            barra_y = y + alto_fila - 8
            barra_ancho_total = ancho_panel - text_x - 12
            fraccion = min(1.0, abs(valor) / max_valor)
            pygame.draw.rect(superficie, (255, 255, 255, 40), (text_x, barra_y, barra_ancho_total, 4), border_radius=2)
            pygame.draw.rect(superficie, (*color, 220), (text_x, barra_y, int(barra_ancho_total * fraccion), 4), border_radius=2)

            y += alto_fila

        pantalla.blit(superficie, self.pos)

class HUDTimer:
    def __init__(self, game, duracion=180, posicion=(400, 10)):
        self.game = game
        self.duracion = duracion
        self.posicion = posicion
        self.font = pygame.font.SysFont("Arial", 26, bold=True)

    def _dibujar_reloj(self, superficie, cx, cy, radio, color):
        pygame.draw.circle(superficie, color, (cx, cy), radio, width=2)
        # Manecillas puramente decorativas (no marcan la hora real).
        pygame.draw.line(superficie, color, (cx, cy), (cx, cy - radio + 3), 2)
        pygame.draw.line(superficie, color, (cx, cy), (cx + radio - 5, cy), 2)

    def draw(self, pantalla):
        restante = max(0, self.game.tiempo_restante)
        minutos = restante // 60
        segundos = restante % 60
        texto = f"{minutos:02}:{segundos:02}"

        if restante <= 10:
            color = (255, 60, 60)
        elif restante <= 30:
            color = (255, 165, 0)
        else:
            color = (255, 255, 255)

        # Pulso de urgencia en los últimos 10 segundos
        escala = 1.0
        if restante <= 10:
            pulso = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() / 150)
            escala = 1.0 + pulso * 0.12

        render_texto = self.font.render(texto, True, color)
        render_borde = self.font.render(texto, True, (0, 0, 0))

        radio_reloj = 14
        espacio_icono = radio_reloj * 2 + 10
        ancho_txt, alto_txt = render_texto.get_size()
        padding_x, padding_y = 16, 10
        ancho_total = espacio_icono + ancho_txt + padding_x * 2
        alto_total = max(alto_txt, radio_reloj * 2) + padding_y * 2

        superficie = pygame.Surface((ancho_total, alto_total), pygame.SRCALPHA)
        panel_rect = superficie.get_rect()
        pygame.draw.rect(superficie, (20, 20, 20, 170), panel_rect, border_radius=14)
        pygame.draw.rect(superficie, (*color, 220), panel_rect, width=2, border_radius=14)

        cy = alto_total // 2
        self._dibujar_reloj(superficie, padding_x + radio_reloj, cy, radio_reloj, color)

        texto_x = padding_x + espacio_icono
        centro_texto = (texto_x + ancho_txt // 2, cy)
        grosor = 2
        for dx in (-grosor, 0, grosor):
            for dy in (-grosor, 0, grosor):
                if dx == 0 and dy == 0:
                    continue
                superficie.blit(render_borde, render_borde.get_rect(center=(centro_texto[0] + dx, centro_texto[1] + dy)))
        superficie.blit(render_texto, render_texto.get_rect(center=centro_texto))

        # Barra de progreso fina abajo, con la fracción de tiempo restante.
        fraccion = restante / self.duracion if self.duracion else 0
        barra_y = alto_total - 6
        barra_ancho = ancho_total - padding_x
        pygame.draw.rect(superficie, (255, 255, 255, 40), (padding_x // 2, barra_y, barra_ancho, 4), border_radius=2)
        pygame.draw.rect(superficie, (*color, 220), (padding_x // 2, barra_y, int(barra_ancho * fraccion), 4), border_radius=2)

        if escala != 1.0:
            nuevo_tam = (max(1, int(ancho_total * escala)), max(1, int(alto_total * escala)))
            superficie = pygame.transform.smoothscale(superficie, nuevo_tam)

        rect = superficie.get_rect(center=self.posicion)
        pantalla.blit(superficie, rect)

class HUDTurnos:
    """
    Colores según fase del turno:
      "turno"        -> amarillo   (puede moverse y disparar)
      "post_disparo" -> naranja    (ya disparó, solo puede moverse)
      "cooldown"     -> rojo tenue (turno terminado, esperando el cambio)
    """

    def __init__(self, turn_manager, posicion=(10, 60)):
        self.tm = turn_manager
        self.font = pygame.font.SysFont("Arial", 20, bold=True)
        self.pos = posicion

    def _dibujar_con_borde(self, pantalla, texto, centro, color, color_borde=(0, 0, 0), grosor=2):
        render_borde = self.font.render(texto, True, color_borde)
        render = self.font.render(texto, True, color)
        rect = render.get_rect(center=centro)
        for dx in (-grosor, 0, grosor):
            for dy in (-grosor, 0, grosor):
                if dx == 0 and dy == 0:
                    continue
                pantalla.blit(render_borde, render_borde.get_rect(center=(centro[0] + dx, centro[1] + dy)))
        pantalla.blit(render, rect)

    def draw(self, pantalla):
        jugador = self.tm.jugador_actual()
        if not jugador:
            return
        tiempo = max(0, self.tm.tiempo_restante())
        fase = getattr(self.tm, "fase", "turno")
        es_mi_turno = jugador == getattr(self.tm.game, "nombre_jugador", None)

        if es_mi_turno:
            color = (255, 255, 255)
            texto = f"Tu turno ({tiempo})"
        else:
            if fase == "post_disparo":
                color = (237, 65, 20)
            elif fase == "cooldown":
                color = (237, 65, 20)
            else:
                color = (200, 192, 10)
            texto = f"Turno de {jugador} ({tiempo})"

        self._dibujar_con_borde(pantalla, texto, self.pos, color)


