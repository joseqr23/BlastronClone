# core/game_modes/solo_game/rewards.py
"""Cálculo puro de estrellas para que pueda reutilizarse en cualquier UI."""

def calculate_stars(victory: bool, health_ratio: float, elapsed_ratio: float) -> int:
    if not victory:
        return 0
    stars = 1
    if health_ratio >= 0.50:
        stars += 1
    if elapsed_ratio <= 0.75:
        stars += 1
    return stars
