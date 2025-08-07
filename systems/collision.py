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
