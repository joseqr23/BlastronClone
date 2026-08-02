# core/game_modes/solo_game/intro_screen.py
"""Pantalla de presentación previa al nivel: un mensaje por robot que
tenga "mensaje" en su config.json de nivel (bot o jefe), mostrado uno a
la vez con su retrato, como una escena de diálogo corta. Si ningún
robot del nivel define mensaje, run() no dibuja nada."""
import pygame
from utils.paths import resource_path
import glob

def _cargar_portrait(robot_id, tam=150):
    patron = resource_path(f"assets/robots/{robot_id}/portrait*.png")
    candidatos = sorted(glob.glob(patron))
    if not candidatos:
        return None
    try:
        imagen = pygame.image.load(candidatos[0]).convert_alpha()
        return pygame.transform.smoothscale(imagen, (tam, tam))
    except Exception:
        return None


def _envolver_texto(texto, fuente, ancho_max):
    palabras, lineas, actual = texto.split(" "), [], ""
    for palabra in palabras:
        prueba = f"{actual} {palabra}".strip()
        if fuente.size(prueba)[0] <= ancho_max:
            actual = prueba
        else:
            if actual:
                lineas.append(actual)
            actual = palabra
    if actual:
        lineas.append(actual)
    return lineas


class IntroScreen:
    def __init__(self, game, entradas):
        # entradas: [(robot_id, nombre, mensaje), ...]
        self.game = game
        self.entradas = [e for e in entradas if e[2]]
        self.indice = 0
        self.continue_rect = None
        self._portraits = {}

    def _portrait(self, robot_id):
        if robot_id not in self._portraits:
            self._portraits[robot_id] = _cargar_portrait(robot_id)
        return self._portraits[robot_id]

    def run(self):
        if not self.entradas:
            return "start"
        game = self.game
        while self.indice < len(self.entradas):
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    return None
                if evento.type == pygame.KEYDOWN and evento.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
                    if evento.key == pygame.K_ESCAPE:
                        return "start"
                    self.indice += 1
                if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                    if self.continue_rect and self.continue_rect.collidepoint(game.convertir_coordenadas(evento.pos)):
                        self.indice += 1
            if self.indice >= len(self.entradas):
                break
            self._draw()
            game.presentar()
            game.reloj.tick(30)
        return "start"

    def _draw(self):
        pantalla = self.game.pantalla
        ancho, alto = pantalla.get_size()
        pantalla.fill((18, 20, 28))

        robot_id, nombre, mensaje = self.entradas[self.indice]
        panel = pygame.Rect(ancho // 2 - 320, alto // 2 - 130, 640, 220)
        pygame.draw.rect(pantalla, (32, 36, 48), panel, border_radius=14)
        pygame.draw.rect(pantalla, (255, 140, 0), panel, width=2, border_radius=14)

        portrait_box = pygame.Rect(panel.x + 20, panel.y + 20, 150, 150)
        pygame.draw.rect(pantalla, (15, 18, 25), portrait_box, border_radius=10)
        portrait = self._portrait(robot_id)
        if portrait:
            pantalla.blit(portrait, portrait.get_rect(center=portrait_box.center))

        fuente_nombre = pygame.font.SysFont("Arial", 25, bold=True)
        fuente_texto = pygame.font.SysFont("Arial", 20)
        texto_x = portrait_box.right + 20
        texto_ancho = panel.right - texto_x - 20

        pantalla.blit(fuente_nombre.render(nombre, True, (255, 210, 140)), (texto_x, panel.y + 20))

        y = panel.y + 55
        for linea in _envolver_texto(mensaje, fuente_texto, texto_ancho):
            pantalla.blit(fuente_texto.render(linea, True, (230, 230, 235)), (texto_x, y))
            y += 22

        self.continue_rect = pygame.Rect(panel.centerx - 90, panel.bottom - 46, 180, 34)
        pygame.draw.rect(pantalla, (255, 140, 0), self.continue_rect, border_radius=8)
        etiqueta = "CONTINUAR" if self.indice < len(self.entradas) - 1 else "EMPEZAR"
        fuente_boton = pygame.font.SysFont("Arial", 15, bold=True)
        texto_boton = fuente_boton.render(etiqueta, True, (25, 20, 15))
        pantalla.blit(texto_boton, texto_boton.get_rect(center=self.continue_rect.center))