# core/game_modes/multi_game/lobby.py

"""Sala de espera. La red pertenece a MultiplayerGame, no al menú."""

import pygame
from utils.paths import resource_path


class LobbyScreen:
    def __init__(self, game):
        self.game = game
        self.start_rect = None
        self.ready_rect = None
        self.back_rect = None
        self.notice = "Esperando jugadores..."
        self.portraits = {}

    def _portrait(self, robot_name):
        if robot_name not in self.portraits:
            try:
                path = resource_path(f"assets/robots/{robot_name}/portrait.png")
                image = pygame.image.load(path).convert_alpha()
                self.portraits[robot_name] = pygame.transform.smoothscale(image, (64, 64))
            except Exception:
                self.portraits[robot_name] = None
        return self.portraits[robot_name]

    def run(self):
        game = self.game
        if game.network.connection_error:
            return self._run_connection_error()
        if not game.host:
            game.enviar({"tipo": "hello", "jugador": game.nombre_jugador, "personaje": game.personaje})
        while not game.partida_iniciada:
            game.messages.process_pending()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return None
                    if game.host and event.key == pygame.K_RETURN:
                        game.start_match_if_possible()
                    elif not game.host and event.key == pygame.K_r:
                        game.set_local_ready(not game.local_ready)
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if game.host and self.start_rect and self.start_rect.collidepoint(event.pos):
                        game.start_match_if_possible()
                    elif not game.host and self.ready_rect and self.ready_rect.collidepoint(event.pos):
                        game.set_local_ready(not game.local_ready)
                    elif self.back_rect and self.back_rect.collidepoint(event.pos):
                        return "host_config" if game.host else "menu"
            self.draw()
            pygame.display.flip()
            game.reloj.tick(30)
        return "start"

    def _run_connection_error(self):
        game, screen = self.game, self.game.pantalla
        font_title = pygame.font.SysFont("Arial", 32, bold=True)
        font_text = pygame.font.SysFont("Arial", 17)
        font_button = pygame.font.SysFont("Arial", 18, bold=True)
        button = pygame.Rect(0, 0, 220, 44)
        button.center = (screen.get_width() // 2, screen.get_height() // 2 + 100)
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN):
                    return "menu"
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and button.collidepoint(event.pos):
                    return "menu"
            screen.fill((28, 24, 31))
            title = font_title.render("No se pudo conectar al Host", True, (255, 145, 120))
            screen.blit(title, title.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2 - 70)))
            message = game.network.connection_error
            lines = self._wrap_text(font_text, message, screen.get_width() - 100)
            for index, line in enumerate(lines):
                text = font_text.render(line, True, (225, 225, 232))
                screen.blit(text, text.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2 - 18 + index * 25)))
            pygame.draw.rect(screen, (70, 110, 185), button, border_radius=9)
            pygame.draw.rect(screen, (230, 235, 250), button, width=2, border_radius=9)
            text = font_button.render("VOLVER AL MENÚ", True, (255, 255, 255))
            screen.blit(text, text.get_rect(center=button.center))
            pygame.display.flip()
            game.reloj.tick(30)

    @staticmethod
    def _wrap_text(font, text, max_width):
        words, lines, current = text.split(), [], ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if current and font.size(candidate)[0] > max_width:
                lines.append(current); current = word
            else:
                current = candidate
        return lines + ([current] if current else [])

    def draw(self):
        game, screen = self.game, self.game.pantalla
        screen.fill((20, 24, 34))
        title_font = pygame.font.SysFont("Arial", 36, bold=True)
        subtitle_font = pygame.font.SysFont("Arial", 17)
        card_font = pygame.font.SysFont("Arial", 20, bold=True)
        small_font = pygame.font.SysFont("Arial", 15, bold=True)
        screen.blit(title_font.render("SALA DE ESPERA", True, (245, 245, 250)), (48, 28))
        map_label = f"{game.tiempo_total // 60} min   •   {game.modo.etiqueta_podio()}"
        screen.blit(subtitle_font.render(map_label, True, (170, 178, 195)), (50, 76))
        config_rect = pygame.Rect(screen.get_width() - 260, 20, 212, 82)
        pygame.draw.rect(screen, (38, 44, 59), config_rect, border_radius=10)
        pygame.draw.rect(screen, (75, 86, 112), config_rect, width=2, border_radius=10)
        preview = pygame.transform.smoothscale(game.fondo, (94, 58))
        preview_rect = preview.get_rect(midleft=(config_rect.x + 10, config_rect.centery))
        screen.blit(preview, preview_rect)
        screen.blit(small_font.render("MAPA", True, (170, 178, 195)), (preview_rect.right + 10, config_rect.y + 17))
        map_name = subtitle_font.render(str(game.mapa_id).upper(), True, (255, 180, 65))
        screen.blit(map_name, (preview_rect.right + 10, config_rect.y + 42))
        pygame.draw.line(screen, (65, 73, 95), (48, 112), (screen.get_width() - 48, 112), 2)

        players = list(game.lobby_players.values())
        if not players:
            players = [{"nombre": game.nombre_jugador, "personaje": game.personaje, "listo": game.host}]
        x, y, card_w, card_h = 50, 140, 250, 116
        for index, player in enumerate(players):
            rect = pygame.Rect(x + (index % 3) * (card_w + 18), y + (index // 3) * (card_h + 18), card_w, card_h)
            is_host = player["nombre"] == game.host_name
            ready = player.get("listo", False)
            pygame.draw.rect(screen, (42, 49, 66), rect, border_radius=12)
            pygame.draw.rect(screen, (255, 140, 0) if is_host else (82, 92, 120), rect, width=2, border_radius=12)
            portrait_box = pygame.Rect(rect.x + 14, rect.y + 17, 70, 70)
            pygame.draw.rect(screen, (23, 28, 40), portrait_box, border_radius=8)
            portrait = self._portrait(player.get("personaje", "robot"))
            if portrait:
                screen.blit(portrait, portrait.get_rect(center=portrait_box.center))
            screen.blit(card_font.render(player["nombre"], True, (240, 240, 245)), (rect.x + 96, rect.y + 17))
            screen.blit(subtitle_font.render(player.get("personaje", "robot"), True, (175, 182, 198)), (rect.x + 96, rect.y + 48))
            state = "HOST" if is_host else ("LISTO" if ready else "NO LISTO")
            color = (255, 165, 40) if is_host else ((80, 210, 130) if ready else (200, 110, 100))
            badge = small_font.render(state, True, color)
            screen.blit(badge, (rect.x + 96, rect.bottom - 28))

        bottom_y = screen.get_height() - 86
        self.back_rect = pygame.Rect(50, bottom_y, 230, 44)
        pygame.draw.rect(screen, (62, 85, 130), self.back_rect, border_radius=10)
        pygame.draw.rect(screen, (215, 225, 245), self.back_rect, width=2, border_radius=10)
        back_text = "VOLVER A CONFIGURACIÓN" if game.host else "VOLVER AL MENÚ"
        text = small_font.render(back_text, True, (255, 255, 255))
        screen.blit(text, text.get_rect(center=self.back_rect.center))
        if game.host:
            can_start = game.can_start_match()
            self.start_rect = pygame.Rect(screen.get_width() - 290, bottom_y, 240, 44)
            color = (255, 140, 0) if can_start else (95, 70, 45)
            pygame.draw.rect(screen, color, self.start_rect, border_radius=10)
            pygame.draw.rect(screen, (255, 185, 80), self.start_rect, width=2, border_radius=10)
            text = small_font.render("EMPEZAR PARTIDA", True, (25, 22, 18))
            screen.blit(text, text.get_rect(center=self.start_rect.center))
            hint = "Se necesitan 2 jugadores y todos los clientes listos"
        else:
            self.ready_rect = pygame.Rect(screen.get_width() - 290, bottom_y, 240, 44)
            color = (70, 165, 105) if game.local_ready else (70, 95, 145)
            pygame.draw.rect(screen, color, self.ready_rect, border_radius=10)
            pygame.draw.rect(screen, (215, 225, 245), self.ready_rect, width=2, border_radius=10)
            text = small_font.render("LISTO" if game.local_ready else "MARCAR COMO LISTO", True, (255, 255, 255))
            screen.blit(text, text.get_rect(center=self.ready_rect.center))
            hint = "Pulsa R para cambiar tu estado"
        screen.blit(subtitle_font.render(hint, True, (170, 178, 195)), (300, bottom_y + 13))
