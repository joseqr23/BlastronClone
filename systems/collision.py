# systems/collision.py
import pygame

def check_collisions(robot, tiles):
    rect = robot.get_rect()
    robot.on_ground = False

    for tile in tiles:
        if rect.colliderect(tile.rect):
            # Colisión desde arriba (pisar plataforma)
            if robot.vel_y >= 0 and rect.bottom <= tile.rect.bottom:
                robot.y = tile.rect.top - robot.height
                robot.vel_y = 0
                robot.on_ground = True
            # Colisión desde abajo (golpe con techo)
            elif robot.vel_y < 0 and rect.top >= tile.rect.bottom:
                robot.y = tile.rect.bottom
                robot.vel_y = 0


def check_collisions_laterales_esquinas(robot, tiles_laterales):
    rect = robot.get_rect()

    for tile in tiles_laterales:
        # Sólo bloqueo lateral para estos tiles especiales (los muros)
        if rect.colliderect(tile.rect):
            # Bloqueo lateral izquierda
            if rect.left < tile.rect.right and robot.vel_x < 0:
                robot.x = tile.rect.right
                robot.vel_x = 0
            # Bloqueo lateral derecha
            elif rect.right > tile.rect.left and robot.vel_x > 0:
                robot.x = tile.rect.left - robot.width
                robot.vel_x = 0

def check_colision_bloque_solido(entidad, tiles):
    """Muro/bloque TOTAL: bloquea por los 4 lados sin importar la forma
    del tile. A diferencia de check_collisions() y
    check_collisions_laterales_esquinas() — que cada una asume una forma
    específica (plataforma corta / pared alta) y se rompen con la forma
    contraria — esta resuelve calculando cuál de los 4 solapamientos
    posibles es el MENOR (AABB "Minimum Translation Vector"): ese es
    siempre el lado real de contacto, sin importar las proporciones."""
    for tile in tiles:
        rect = entidad.get_rect()
        if not rect.colliderect(tile.rect):
            continue

        solape_izq = rect.right - tile.rect.left
        solape_der = tile.rect.right - rect.left
        solape_arriba = rect.bottom - tile.rect.top
        solape_abajo = tile.rect.bottom - rect.top

        lado, _ = min(
            (("izquierda", solape_izq), ("derecha", solape_der),
             ("arriba", solape_arriba), ("abajo", solape_abajo)),
            key=lambda o: o[1]
        )

        if lado == "arriba":
            entidad.y = tile.rect.top - entidad.height
            entidad.vel_y = 0
            entidad.on_ground = True
        elif lado == "abajo":
            entidad.y = tile.rect.bottom
            entidad.vel_y = 0
        elif lado == "izquierda":
            entidad.x = tile.rect.left - entidad.width
            entidad.vel_x = 0
        elif lado == "derecha":
            entidad.x = tile.rect.right
            entidad.vel_x = 0

def check_zonas_dañinas(robot, tiles_dañinas, daño, aplicar_dano_callback=None, intervalo_ms=1000):
    """Aplica daño periódico mientras el robot esté solapado con alguna
    zona dañina. No bloquea movimiento, solo detecta superposición.
    aplicar_dano_callback(robot, daño): si se pasa, se usa en vez de
    robot.take_damage() directo — en multijugador esto DEBE ser
    weapon_manager.aplicar_dano (para que el daño se sincronice por red,
    igual que el de las armas). En modo libre no hace falta pasarlo."""
    rect = robot.get_rect()
    for tile in tiles_dañinas:
        if rect.colliderect(tile.rect):
            ahora = pygame.time.get_ticks()
            ultimo = getattr(robot, "_ultimo_dano_zona", 0)
            if ahora - ultimo >= intervalo_ms:
                robot._ultimo_dano_zona = ahora
                if aplicar_dano_callback:
                    aplicar_dano_callback(robot, daño)
                else:
                    robot.take_damage(daño)
            return
            