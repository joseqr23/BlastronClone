class HUDManager:
    def __init__(self, game):
        self.game = game

    def draw(self, pantalla):
        self.game.hud_armas.draw(pantalla, self.game.font)
        self.game.hud_puntajes.draw(pantalla)
