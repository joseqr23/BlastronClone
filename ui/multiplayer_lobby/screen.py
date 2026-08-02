# ui/multiplayer_lobby/screen.py
import pygame

from .assets import LobbyAssets
from .widgets import LobbyConfigWidgets


class MultiplayerLobbyScreen:
    """Lobby adaptable: seis jugadores a la izquierda, configuración a la derecha."""
    def __init__(self, game):
        self.game = game
        self.assets = LobbyAssets()
        self.config_widgets = LobbyConfigWidgets(self.assets)
        self.ready_rect = self.start_rect = self.back_rect = None

    def run(self):
        game = self.game
        if not game.host:
            game.enviar({"tipo": "hello", "jugador": game.nombre_jugador, "personaje": game.personaje})
        while not game.partida_iniciada:
            game.messages.process_pending()
            if game.volver_al_menu:
                return "menu"
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                if event.type == pygame.VIDEORESIZE:
                    game.redimensionar_ventana(event.w, event.h)
                    continue
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return "menu"
                    if event.key == pygame.K_F11:
                        game.alternar_pantalla_completa()
                        continue
                    if game.host and event.key == pygame.K_RETURN:
                        game.lobby_controller.start_match()
                    if not game.host and event.key == pygame.K_r:
                        self._toggle_ready()
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    pos = game.convertir_coordenadas(event.pos)
                    if self.back_rect and self.back_rect.collidepoint(pos):
                        return "menu"
                    if game.host:
                        change = self.config_widgets.handle_click(pos, game.lobby_state.config)
                        if change:
                            game.lobby_controller.update_config(**change)
                        elif self.start_rect and self.start_rect.collidepoint(pos):
                            game.lobby_controller.start_match()
                    elif self.ready_rect and self.ready_rect.collidepoint(pos):
                        self._toggle_ready()
            self.draw()
            game.presentar()
            game.reloj.tick(30)
        return "start"

    def _toggle_ready(self):
        game = self.game
        game.enviar({"tipo": "ready", "jugador": game.nombre_jugador, "listo": not game.local_ready})

    def draw(self):
        game, screen, state = self.game, self.game.pantalla, self.game.lobby_state
        width, height = screen.get_size()
        margin, gap, top = 36, 22, 105
        left_width = max(320, int((width - 2 * margin - gap) * .48))
        right_x = margin + left_width + gap
        right_width = width - margin - right_x
        content_height = max(245, height - top - 82)

        screen.fill((20, 24, 34))
        title_font = pygame.font.SysFont("Arial", 34, bold=True)
        text_font = pygame.font.SysFont("Arial", 15)
        small_font = pygame.font.SysFont("Arial", 15, bold=True)
        screen.blit(title_font.render("SALA DE ESPERA", True, (245, 245, 250)), (margin, 20))
        subtitle = "El Host configura la partida; los clientes marcan Listo"
        screen.blit(text_font.render(subtitle, True, (172, 181, 200)), (margin + 2, 66))

        players_rect = pygame.Rect(margin, top, left_width, content_height)
        config_rect = pygame.Rect(right_x, top, right_width, content_height)
        self._draw_players(screen, players_rect, state, text_font, small_font)
        self.config_widgets.draw(screen, config_rect, state.config, game.host)

        bottom_y = height - 54
        self.back_rect = pygame.Rect(margin, bottom_y, 172, 38)
        self._draw_button(screen, self.back_rect, "VOLVER AL MENÚ", (63, 84, 132), small_font)
        if game.host:
            self.start_rect = pygame.Rect(width - margin - 208, bottom_y, 208, 38)
            color = (255, 140, 0) if game.lobby_controller.can_start() else (100, 73, 45)
            self._draw_button(screen, self.start_rect, "EMPEZAR PARTIDA", color, small_font, text_color=(25, 20, 15))
        else:
            self.ready_rect = pygame.Rect(width - margin - 208, bottom_y, 208, 38)
            label = "LISTO" if game.local_ready else "MARCAR COMO LISTO (R)"
            self._draw_button(screen, self.ready_rect, label, (70, 165, 105) if game.local_ready else (70, 95, 145), small_font)

    def _draw_players(self, surface, rect, state, text_font, small_font):
        pygame.draw.rect(surface, (38, 44, 59), rect, border_radius=12)
        pygame.draw.rect(surface, (72, 82, 106), rect, width=2, border_radius=12)
        surface.blit(small_font.render("JUGADORES CONECTADOS", True, (240, 240, 245)), (rect.x + 14, rect.y + 12))
        players = list(state.jugadores.values())[:6]
        if not players:
            waiting = text_font.render("Esperando jugadores...", True, (172, 181, 200))
            surface.blit(waiting, waiting.get_rect(center=rect.center))
            return
        card_gap, card_h = 10, 68
        card_w = (rect.width - 34) // 2
        for index, player in enumerate(players):
            col, row = index % 2, index // 2
            card = pygame.Rect(rect.x + 12 + col * (card_w + card_gap), rect.y + 42 + row * (card_h + 10), card_w, card_h)
            self._draw_player_card(surface, card, player, state.host_id, text_font, small_font)

    def _draw_player_card(self, surface, rect, player, host_id, text_font, small_font):
        is_host, ready = player.nombre == host_id, player.listo
        pygame.draw.rect(surface, (42, 49, 66), rect, border_radius=9)
        pygame.draw.rect(surface, (255, 140, 0) if is_host else (74, 86, 112), rect, width=2, border_radius=9)
        portrait_box = pygame.Rect(rect.x + 8, rect.y + 10, 48, 48)
        pygame.draw.rect(surface, (22, 27, 38), portrait_box, border_radius=7)
        portrait = self.assets.portrait(player.personaje)
        if portrait:
            image = pygame.transform.smoothscale(portrait, (46, 46))
            surface.blit(image, image.get_rect(center=portrait_box.center))
        name = self._fit_text(small_font, player.nombre, rect.width - 70)
        robot = self._fit_text(text_font, player.personaje.capitalize(), rect.width - 70)
        surface.blit(name, (rect.x + 64, rect.y + 9))
        surface.blit(robot, (rect.x + 64, rect.y + 28))
        label = "HOST" if is_host else ("LISTO" if ready else "NO LISTO")
        color = (255, 170, 55) if is_host else ((90, 210, 135) if ready else (220, 125, 115))
        surface.blit(small_font.render(label, True, color), (rect.x + 64, rect.y + 47))

    @staticmethod
    def _draw_button(surface, rect, label, color, font, text_color=(255, 255, 255)):
        pygame.draw.rect(surface, color, rect, border_radius=8)
        pygame.draw.rect(surface, (215, 225, 245), rect, width=1, border_radius=8)
        text = font.render(label, True, text_color)
        surface.blit(text, text.get_rect(center=rect.center))

    @staticmethod
    def _fit_text(font, value, max_width):
        value = str(value)
        while len(value) > 1 and font.size(value)[0] > max_width:
            value = value[:-2] + "…"
        return font.render(value, True, (245, 245, 250))
