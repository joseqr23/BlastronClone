import pygame
from entities.players.robot_estatico import RobotEstatico


class EventHandler:
    def __init__(self, game):
        self.game = game

    def handle_events(self):
        """Procesa eventos de teclado, mouse y HUD. Devuelve False si se cierra el juego."""
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                return False

            # Chat
            self.game.chat.handle_event(evento)

            # HUD armas
            arma_seleccionada = self.game.hud_armas.manejar_evento(evento)
            if arma_seleccionada is not None:
                if arma_seleccionada == "spawn_robot":
                    nuevo_robot = RobotEstatico(400, 300)
                    self.game.robots_estaticos.append(nuevo_robot)
                else:
                    self.game.robot.arma_equipada = arma_seleccionada

            # Disparo
            if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                if not self.game.mouse_click_sostenido:
                    clic_sobre_hud = any(
                        rect.collidepoint(evento.pos) for _, rect in self.game.hud_armas.botones
                    )
                    if not clic_sobre_hud and self.game.robot.arma_equipada not in [None, 'nada']:
                        self.game.weapon_manager.disparar()
                        self.game.mouse_click_sostenido = True

            if evento.type == pygame.MOUSEBUTTONUP and evento.button == 1:
                self.game.mouse_click_sostenido = False

        return True
