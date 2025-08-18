from entities.players.robot import Robot
from systems.collision import check_collisions
from utils.loader import load_spritesheet
import pygame

class RobotEstatico(Robot):
    def __init__(self, x, y, nombre_jugador= "Alfonso", nombre_robot="alfonso"):
        super().__init__(x, y, nombre_jugador, nombre_robot)
        self.es_jugador = False

    def update(self, tiles, armas=None, keys=None):
        if self.is_dead:
            # Mostrar la animación de muerte sin reiniciar
            self.current_animation = "death"
            self.frame_timer += 1
            if self.frame_timer >= 10:
                self.frame_timer = 0
                if self.frame_index < len(self.animations["death"]) - 1:
                    self.frame_index += 1

            self.image = self.animations["death"][self.frame_index]
            if not self.facing_right:
                self.image = pygame.transform.flip(self.image, True, False)
            return
        else:
            self.vel_x = 0  # No se mueve horizontalmente
            self.aplicar_fisica()
            check_collisions(self, tiles)  # Colisión con plataformas

            # --- Colisión con armas ---
            if armas:
                for arma in armas:
                    if self.get_rect().colliderect(arma.get_rect()):
                        if hasattr(arma, "damage"):
                            self.take_damage(arma.damage)
                        else:
                            self.take_damage(20)
                        if hasattr(arma, "activo"):
                            arma.activo = False

            self.actualizar_animacion()

    def debe_eliminarse(self):
        return self.is_dead and self.frame_index >= len(self.animations["death"]) - 1
