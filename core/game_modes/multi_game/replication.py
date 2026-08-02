# core/game_modes/multi_game/replication.py

"""Sincronización de jugadores y proyectiles entre Host y Clientes."""

import pygame

from entities.weapons.proyectil import Proyectil
from utils.sound_manager import sound_manager


class Replication:
    def __init__(self, game):
        self.game = game
        self.projectile_id = 0

    def next_projectile_id(self):
        self.projectile_id += 1
        return self.projectile_id

    def send_local_state(self):
        game = self.game
        game._seq_local += 1
        mouse = game.mouse_logico()
        origin = game.robot.get_centro()
        ammo = game.weapon_manager.municion_actual(game.robot.arma_equipada)
        game.enviar({
            "tipo": "update", "jugador": game.nombre_jugador, "personaje": game.personaje,
            "seq": game._seq_local, "x": float(game.robot.x), "y": float(game.robot.y),
            "frame": game.robot.frame_index, "estado": game.robot.current_animation,
            "direccion": 1 if game.robot.facing_right else -1, "health": game.robot.health,
            "arma": game.robot.arma_equipada, "sin_municion": ammo is not None and ammo <= 0,
            "aim_dx": mouse[0] - origin[0], "aim_dy": mouse[1] - origin[1],
        })

    def sync_projectiles(self):
        game = self.game
        if not game.host:
            return
        items = []
        for projectile in game.proyectiles:
            items.append({
                "id": getattr(projectile, "proj_id", None), "tipo": projectile.tipo,
                "owner": getattr(projectile, "owner", None), "x": projectile.x, "y": projectile.y,
                "vel_x": projectile.vel_x, "vel_y": projectile.vel_y,
                "estado": getattr(projectile, "estado", None),
                "explotado": getattr(projectile, "explotado", False),
                "facing_right": getattr(projectile, "_facing_right", True),
                "angulo_ataque": getattr(projectile, "angulo_ataque", None),
            })
        game.enviar({"tipo": "proy_sync", "items": items})

    def apply_projectile_sync(self, items):
        game = self.game
        received_ids = set()
        for item in items:
            projectile_id = item.get("id")
            if projectile_id is None:
                continue
            received_ids.add(projectile_id)
            proxy = next((p for p in game.proyectiles if getattr(p, "proj_id", None) == projectile_id), None)
            if proxy is None:
                proxy = Proyectil(item["tipo"], item["x"], item["y"], 0, 0,
                                  owner=item.get("owner"), facing_right=item.get("facing_right", True),
                                  angulo_ataque=item.get("angulo_ataque"))
                proxy.proj_id = projectile_id
                proxy.danados = set()
                proxy.ya_hizo_dano = True
                game.proyectiles.append(proxy)
                sound_manager.disparo(item["tipo"])
            was_exploded = proxy.explotado
            proxy.x, proxy.y = item["x"], item["y"]
            proxy.vel_x = item.get("vel_x", proxy.vel_x)
            proxy.vel_y = item.get("vel_y", proxy.vel_y)
            proxy.estado = item.get("estado")
            proxy.explotado = item.get("explotado", False)
            proxy._facing_right = item.get("facing_right", proxy._facing_right)
            proxy.angulo_ataque = item.get("angulo_ataque", proxy.angulo_ataque)
            if proxy.explotado and not was_exploded:
                sound_manager.explosion(item["tipo"])
                game.activar_shake(proxy.config.get("sacudida_intensidad", 0), proxy.config.get("sacudida_duracion_ms", 0))
        game.proyectiles = [p for p in game.proyectiles if getattr(p, "proj_id", None) in received_ids]

    def interpolate_remotes(self, factor=0.35):
        for robot in self.game.robots_remotos.values():
            robot.x += (getattr(robot, "target_x", robot.x) - robot.x) * factor
            robot.y += (getattr(robot, "target_y", robot.y) - robot.y) * factor
