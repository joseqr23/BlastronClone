# ui/server_config_menu.py
import pygame
from ui.text_input import TextInput

def server_config_menu(pantalla, font_titulo, font_opcion, font_input, nombre, personaje):
    from ui.multiplayer_menu import MultiplayerMenu

    clock = pygame.time.Clock()

    # Opciones
    tipos_partida = ["Por puntos", "Por matanzas"]
    tiempos_partida = ["3 min", "5 min", "7 min"]
    tiempos_turno = ["10 seg", "15 seg", "20 seg"]

    # Valores iniciales seleccionados
    tipo_seleccionado = 0
    tiempo_partida_seleccionado = 0
    tiempo_turno_seleccionado = 0

    # Campos de texto
    text_nombre_partida = TextInput((350, 350, 250, 35), font_input, max_length=20)
    text_puerto = TextInput((350, 400, 250, 35), font_input, max_length=6)

    cursor_actual = None

    while True:
        pantalla.fill((200, 200, 200))
        mouse_pos = pygame.mouse.get_pos()
        cursor_hover = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            text_nombre_partida.handle_event(event)
            text_puerto.handle_event(event)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Tipo de partida
                for i in range(len(tipos_partida)):
                    if pygame.Rect(350 + i*150, 200, 140, 35).collidepoint(mouse_pos):
                        tipo_seleccionado = i
                # Tiempo de partida
                for i in range(len(tiempos_partida)):
                    if pygame.Rect(350 + i*150, 250, 140, 35).collidepoint(mouse_pos):
                        tiempo_partida_seleccionado = i
                # Tiempo turno
                for i in range(len(tiempos_turno)):
                    if pygame.Rect(350 + i*150, 300, 140, 35).collidepoint(mouse_pos):
                        tiempo_turno_seleccionado = i
                # Botón iniciar partida
                if pygame.Rect(350, 450, 250, 40).collidepoint(mouse_pos):
                    return {
                        "modo": "Multijugador",
                        "tipo": "Servidor",
                        "nombre_jugador": nombre,
                        "personaje": personaje,
                        "tipo_partida": tipos_partida[tipo_seleccionado],
                        "tiempo_partida": tiempos_partida[tiempo_partida_seleccionado],
                        "tiempo_turno": tiempos_turno[tiempo_turno_seleccionado],
                        "nombre_partida": text_nombre_partida.get_text(),
                        "puerto": text_puerto.get_text()
                    }
                # Botón volver
                if pygame.Rect(620, 500, 150, 35).collidepoint(mouse_pos):
                    menu = MultiplayerMenu(pantalla, font_titulo, font_opcion, font_input)
                    return menu.show(nombre, personaje)

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    return {
                        "modo": "Multijugador",
                        "tipo": "Servidor",
                        "nombre_jugador": nombre,
                        "personaje": personaje,
                        "tipo_partida": tipos_partida[tipo_seleccionado],
                        "tiempo_partida": tiempos_partida[tiempo_partida_seleccionado],
                        "tiempo_turno": tiempos_turno[tiempo_turno_seleccionado],
                        "nombre_partida": text_nombre_partida.get_text(),
                        "puerto": text_puerto.get_text()
                    }

        # 🔹 Dibujar textos y botones
        titulo = font_titulo.render("Configuración de la partida", True, (0,0,0))
        pantalla.blit(titulo, (150, 50))

        # Tipo de partida
        label_tipo = font_input.render("Tipo de partida:", True, (0,0,0))
        pantalla.blit(label_tipo, (150, 200))
        for i, opcion in enumerate(tipos_partida):
            rect = pygame.Rect(350 + i*150, 200, 140, 35)
            pygame.draw.rect(pantalla, (180,180,180), rect, border_radius=5)
            if i == tipo_seleccionado:
                pygame.draw.rect(pantalla, (255,0,0), rect, 3, border_radius=5)
            texto = font_input.render(opcion, True, (0,0,0))
            pantalla.blit(texto, (rect.x + 10, rect.y + 5))

        # Tiempo de partida
        label_tiempo = font_input.render("Tiempo de partida:", True, (0,0,0))
        pantalla.blit(label_tiempo, (150, 250))
        for i, opcion in enumerate(tiempos_partida):
            rect = pygame.Rect(350 + i*150, 250, 140, 35)
            pygame.draw.rect(pantalla, (180,180,180), rect, border_radius=5)
            if i == tiempo_partida_seleccionado:
                pygame.draw.rect(pantalla, (255,0,0), rect, 3, border_radius=5)
            texto = font_input.render(opcion, True, (0,0,0))
            pantalla.blit(texto, (rect.x + 10, rect.y + 5))

        # Tiempo turno
        label_turno = font_input.render("Tiempo de turno:", True, (0,0,0))
        pantalla.blit(label_turno, (150, 300))
        for i, opcion in enumerate(tiempos_turno):
            rect = pygame.Rect(350 + i*150, 300, 140, 35)
            pygame.draw.rect(pantalla, (180,180,180), rect, border_radius=5)
            if i == tiempo_turno_seleccionado:
                pygame.draw.rect(pantalla, (255,0,0), rect, 3, border_radius=5)
            texto = font_input.render(opcion, True, (0,0,0))
            pantalla.blit(texto, (rect.x + 10, rect.y + 5))

        # Nombre de partida
        label_nombre = font_input.render("Nombre de partida:", True, (0,0,0))
        pantalla.blit(label_nombre, (150, 350))
        text_nombre_partida.draw(pantalla)

        # Puerto/contraseña
        label_puerto = font_input.render("Puerto/Contraseña:", True, (0,0,0))
        pantalla.blit(label_puerto, (150, 400))
        text_puerto.draw(pantalla)

        # Botón iniciar partida
        rect_boton = pygame.Rect(350, 450, 250, 40)
        pygame.draw.rect(pantalla, (0,200,0), rect_boton, border_radius=5)
        texto_boton = font_input.render("Iniciar partida", True, (255,255,255))
        pantalla.blit(texto_boton, (rect_boton.x + 20, rect_boton.y + 5))

        # Botón volver
        rect_volver = pygame.Rect(620, 500, 150, 35)
        pygame.draw.rect(pantalla, (200,0,0), rect_volver, border_radius=5)
        texto_volver = font_input.render("Volver", True, (255,255,255))
        pantalla.blit(texto_volver, (rect_volver.x + 30, rect_volver.y + 5))

        # Cambiar cursor si hay hover
        hover_area = [pygame.Rect(350 + i*150, 200, 140, 35) for i in range(len(tipos_partida))] + \
                     [pygame.Rect(350 + i*150, 250, 140, 35) for i in range(len(tiempos_partida))] + \
                     [pygame.Rect(350 + i*150, 300, 140, 35) for i in range(len(tiempos_turno))] + \
                     [rect_boton, rect_volver, text_nombre_partida.rect, text_puerto.rect]
        if any(r.collidepoint(mouse_pos) for r in hover_area):
            if cursor_actual != "HAND":
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)
                cursor_actual = "HAND"
        else:
            if cursor_actual != "ARROW":
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)
                cursor_actual = "ARROW"

        pygame.display.flip()
        clock.tick(60)
