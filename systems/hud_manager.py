# systems/hud_manager.py
class HUDManager:
    def __init__(self, game):
        self.game = game

    def draw(self, pantalla):
        self.game.hud_armas.draw(pantalla, self.game.font, weapon_manager=self.game.weapon_manager, mouse_pos=self.game.mouse_logico())
        self.game.hud_puntajes.draw(pantalla)
