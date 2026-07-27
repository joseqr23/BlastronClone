from entities.players.robot import Robot
from systems.collision import (
    check_collisions,
    check_collisions_laterales_esquinas,
    check_colision_bloque_solido,
)
import pygame


class RobotEstatico(Robot):
    def __init__(self, x, y, nombre_jugador="Alfonso", nombre_robot="alfonso"):
        super().__init__(x, y, nombre_jugador, nombre_robot)
        self.es_jugador = False

    def update(
        self,
        tiles,
        tiles_laterales=None,
        tiles_impenetrables=None,
        armas=None,
        keys=None,
    ):
        if self.is_dead:
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

        if pygame.time.get_ticks() >= self.aturdido_hasta:
            self.vel_x = 0

        self.aplicar_fisica()

        # Plataformas: bloquean arriba y abajo.
        check_collisions(self, tiles)

        # Límites/paredes laterales normales.
        if tiles_laterales:
            check_collisions_laterales_esquinas(self, tiles_laterales)

        # Bloques totalmente sólidos: bloquean por los cuatro lados.
        if tiles_impenetrables:
            check_colision_bloque_solido(self, tiles_impenetrables)

        if armas:
            for arma in armas:
                if self.get_rect().colliderect(arma.get_rect()):
                    self.take_damage(getattr(arma, "damage", 20))
                    if hasattr(arma, "activo"):
                        arma.activo = False

        self.actualizar_animacion()

    def debe_eliminarse(self):
        return self.is_dead and self.frame_index >= len(self.animations["death"]) - 1