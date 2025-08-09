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