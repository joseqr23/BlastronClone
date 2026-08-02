# systems/event_handler.py
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

            if evento.type == pygame.VIDEORESIZE:
                self.game.redimensionar_ventana(evento.w, evento.h)
                continue
            if evento.type == pygame.KEYDOWN and evento.key == pygame.K_F11:
                self.game.alternar_pantalla_completa()
                continue

            if evento.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
                evento.pos = self.game.convertir_coordenadas(evento.pos)

            # Multijugador puede pedir confirmación antes de abandonar.
            # FreeGame no activa esta bandera y conserva su salida inmediata.
            if getattr(self.game, "confirmando_salida", False):
                if evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
                    self.game.confirmando_salida = False
                elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                    if self.game.rect_confirmar_salida and self.game.rect_confirmar_salida.collidepoint(evento.pos):
                        self.game.volver_al_menu = True
                    elif self.game.rect_cancelar_salida and self.game.rect_cancelar_salida.collidepoint(evento.pos):
                        self.game.confirmando_salida = False
                continue

            # Botones de acceso rápido
            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_g and not self.game.chat.activo:
                    self.game.hud_armas.colapsado = not self.game.hud_armas.colapsado
                elif evento.key == pygame.K_m and not self.game.chat.activo:
                    self.game.sound_manager.alternar_mute()
                elif evento.key == pygame.K_ESCAPE and not self.game.chat.activo:
                    if hasattr(self.game, "volver_al_menu"):
                        if getattr(self.game, "requiere_confirmacion_menu", False):
                            self.game.confirmando_salida = True
                        else:
                            self.game.volver_al_menu = True

            # Chat
            self.game.chat.handle_event(evento)

            # HUD armas
            arma_seleccionada = self.game.hud_armas.manejar_evento(evento)
            if arma_seleccionada is not None:
                if arma_seleccionada == "spawn_robot":
                    nuevo_robot = RobotEstatico(400, 300)
                    self.game.robots_estaticos.append(nuevo_robot)
                elif not getattr(self.game.modo, "arma_bloqueada", False):
                    self.game.robot.arma_equipada = arma_seleccionada

            # Click: botones propios de la pantalla (volver al menú,
            # mute) tienen prioridad sobre el disparo, para que hacerles
            # click no dispare el arma equipada por accidente.
            if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                rect_menu = getattr(self.game, "rect_volver_menu", None)
                rect_mute = getattr(self.game, "rect_mute", None)
                if rect_menu and rect_menu.collidepoint(evento.pos):
                    if getattr(self.game, "requiere_confirmacion_menu", False):
                        self.game.confirmando_salida = True
                    else:
                        self.game.volver_al_menu = True
                elif rect_mute and rect_mute.collidepoint(evento.pos):
                    self.game.sound_manager.alternar_mute()
                elif not self.game.mouse_click_sostenido:
                    clic_sobre_hud = self.game.hud_armas.punto_sobre_hud(evento.pos)
                    if not clic_sobre_hud and self.game.robot.arma_equipada not in [None, 'nada']:
                        self.game.weapon_manager.disparar()
                        self.game.mouse_click_sostenido = True
            if evento.type == pygame.MOUSEBUTTONUP and evento.button == 1:
                self.game.mouse_click_sostenido = False
        return True
