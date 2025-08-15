# ui/client_connect_menu.py
import pygame
from ui.text_input import TextInput

def client_connect_menu(pantalla, font_titulo, font_opcion, font_input, nombre, personaje):
    from ui.multiplayer_menu import MultiplayerMenu

    clock = pygame.time.Clock()

    # Campos de texto
    text_ip = TextInput((350, 250, 250, 35), font_input, max_length=15)
    text_puerto = TextInput((350, 300, 250, 35), font_input, max_length=6)

    cursor_actual = None

    while True:
        pantalla.fill((200, 200, 200))
        mouse_pos = pygame.mouse.get_pos()
        cursor_hover = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()

            text_ip.handle_event(event)
            text_puerto.handle_event(event)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Botón conectar
                if pygame.Rect(350, 350, 250, 40).collidepoint(mouse_pos):
                    return {
                        "modo": "Multijugador",
                        "tipo": "Cliente",
                        "nombre_jugador": nombre,
                        "personaje": personaje,
                        "ip": text_ip.get_text(),
                        "puerto": text_puerto.get_text()
                    }
                # Botón volver
                if pygame.Rect(620, 400, 150, 35).collidepoint(mouse_pos):
                    menu = MultiplayerMenu(pantalla, font_titulo, font_opcion, font_input)
                    return menu.show(nombre, personaje)

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    return {
                        "modo": "Multijugador",
                        "tipo": "Cliente",
                        "nombre_jugador": nombre,
                        "personaje": personaje,
                        "ip": text_ip.get_text(),
                        "puerto": text_puerto.get_text()
                    }

        # 🔹 Dibujar textos y campos
        titulo = font_titulo.render("Conectar a Servidor", True, (0,0,0))
        pantalla.blit(titulo, (180, 50))

        # IP
        label_ip = font_input.render("IP del Servidor:", True, (0,0,0))
        pantalla.blit(label_ip, (150, 250))
        text_ip.draw(pantalla)

        # Puerto
        label_puerto = font_input.render("Puerto:", True, (0,0,0))
        pantalla.blit(label_puerto, (150, 300))
        text_puerto.draw(pantalla)

        # Botón Conectar
        rect_boton = pygame.Rect(350, 350, 250, 40)
        pygame.draw.rect(pantalla, (0,200,0), rect_boton, border_radius=5)
        texto_boton = font_input.render("Conectar", True, (255,255,255))
        pantalla.blit(texto_boton, (rect_boton.x + 60, rect_boton.y + 5))

        # Botón volver
        rect_volver = pygame.Rect(620, 400, 150, 35)
        pygame.draw.rect(pantalla, (200,0,0), rect_volver, border_radius=5)
        texto_volver = font_input.render("Volver", True, (255,255,255))
        pantalla.blit(texto_volver, (rect_volver.x + 30, rect_volver.y + 5))

        # Cambiar cursor si hay hover
        hover_area = [rect_boton, rect_volver, text_ip.rect, text_puerto.rect]
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
