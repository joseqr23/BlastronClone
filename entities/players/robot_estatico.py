from entities.players.robot import Robot
from systems.collision import check_collisions
from utils.loader import load_spritesheet

class RobotEstatico(Robot):
    def __init__(self, x, y, nombre="Alfonso"):
        super().__init__(x, y, nombre)
        self.es_jugador = False
        
        self.animations = {
            "idle": load_spritesheet("assets/robots_boss/alfonso/idle.png", 1, self.width, self.height),
            "run": load_spritesheet("assets/robots_boss/alfonso/run.png", 6, self.width, self.height),
            "jump": load_spritesheet("assets/robots_boss/alfonso/jump.png", 1, self.width, self.height),
            "death": load_spritesheet("assets/robots_boss/alfonso/death.png", 6, self.width, self.height),
        }

    def update(self, tiles, armas=None, keys=None):
        if self.is_dead:
            super().update(keys)  # Mantener animación de muerte
        else:
            self.vel_x = 0  # No se mueve horizontalmente
            self.aplicar_fisica()
            check_collisions(self, tiles)  # Colisión con plataformas

            # --- Colisión con armas ---
            if armas:
                for arma in armas:
                    if self.get_rect().colliderect(arma.get_rect()):
                        # Aquí decides cuánto daño hace cada arma
                        if hasattr(arma, "damage"):
                            self.take_damage(arma.damage)
                        else:
                            self.take_damage(20)  # Daño por defecto
                        # Si quieres que el arma desaparezca al golpear:
                        if hasattr(arma, "activo"):
                            arma.activo = False

            self.actualizar_animacion()
