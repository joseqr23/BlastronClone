import pygame

from ..theme import *
from ..widgets import draw_input


class MainScreen:
    MODOS = ["Modo Solo", "Modo Multijugador", "Modo Libre"]
    DESCRIPCIONES = {
        "Modo Solo": "Contra bots — próximamente",
        "Modo Multijugador": "Juega por red con amigos",
        "Modo Libre": "Practica armas y movimiento",
    }
    DISPONIBLES = {"Modo Solo": False, "Modo Multijugador": True, "Modo Libre": True}

    def __init__(self, state, assets, fonts, nombre_input, ip_input, toast):
        self.state, self.assets, self.fonts = state, assets, fonts
        self.nombre_input, self.ip_input, self.toast = nombre_input, ip_input, toast
        self.rect_flecha_izq = self.rect_flecha_der = None
        self.rect_opciones = []
        self.rect_host = self.rect_cliente = self.rect_conectar = self.rect_ir_libre = None

    @property
    def modo_actual(self):
        return self.MODOS[self.state.opcion_seleccionada]

    def _confirmar(self):
        modo = self.modo_actual
        if not self.DISPONIBLES[modo]:
            self.toast.show("Este modo estará disponible próximamente")
            return None
        if modo == "Modo Multijugador":
            return "abrir_host" if self.state.multijugador_opcion == "host" else "conectar_cliente"
        return "abrir_libre"

    def handle_event(self, event, mouse_pos):
        self.nombre_input.handle_event(event)
        if self.modo_actual == "Modo Multijugador" and self.state.multijugador_opcion == "cliente":
            self.ip_input.handle_event(event)
        if event.type == pygame.KEYDOWN and not self.nombre_input.active and not self.ip_input.active:
            if event.key == pygame.K_UP:
                self.state.opcion_seleccionada = (self.state.opcion_seleccionada - 1) % len(self.MODOS)
            elif event.key == pygame.K_DOWN:
                self.state.opcion_seleccionada = (self.state.opcion_seleccionada + 1) % len(self.MODOS)
            elif event.key == pygame.K_LEFT:
                self.state.personaje_idx = (self.state.personaje_idx - 1) % len(self.assets.personajes)
            elif event.key == pygame.K_RIGHT:
                self.state.personaje_idx = (self.state.personaje_idx + 1) % len(self.assets.personajes)
            elif event.key == pygame.K_RETURN:
                return self._confirmar()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect_flecha_izq and self.rect_flecha_izq.collidepoint(mouse_pos):
                self.state.personaje_idx = (self.state.personaje_idx - 1) % len(self.assets.personajes)
            elif self.rect_flecha_der and self.rect_flecha_der.collidepoint(mouse_pos):
                self.state.personaje_idx = (self.state.personaje_idx + 1) % len(self.assets.personajes)
            for i, rect in enumerate(self.rect_opciones):
                if rect.collidepoint(mouse_pos):
                    if self.DISPONIBLES[self.MODOS[i]]:
                        self.state.opcion_seleccionada = i
                    else:
                        self.toast.show("Este modo estará disponible próximamente")
                    return None
            if self.modo_actual == "Modo Multijugador":
                if self.rect_host and self.rect_host.collidepoint(mouse_pos):
                    self.state.multijugador_opcion = "host"
                    return "abrir_host"
                if self.rect_cliente and self.rect_cliente.collidepoint(mouse_pos):
                    self.state.multijugador_opcion = "cliente"
                if self.rect_conectar and self.rect_conectar.collidepoint(mouse_pos):
                    return "conectar_cliente"
            elif self.modo_actual == "Modo Libre" and self.rect_ir_libre and self.rect_ir_libre.collidepoint(mouse_pos):
                return "abrir_libre"
        return None

    def draw(self, surface, mouse_pos):
        self.rect_conectar = self.rect_ir_libre = None
        margin, width = 60, surface.get_width() - 120
        title = self.fonts.titulo.render("BLASTRON", True, COL_TEXT)
        accent = self.fonts.titulo.render(" CLONE", True, COL_ACCENT)
        surface.blit(title, (margin, 34)); surface.blit(accent, (margin + title.get_width(), 34))
        surface.blit(self.fonts.subtitulo.render("Elige tu robot y prepárate para la batalla", True, COL_TEXT_DIM), (margin + 2, 80))
        pygame.draw.line(surface, COL_CARD_BORDER, (margin, 112), (surface.get_width() - margin, 112), 2)
        player = pygame.Rect(margin, 130, width, 150)
        draw_panel(surface, player)
        surface.blit(self.fonts.label.render("NOMBRE DEL JUGADOR", True, COL_TEXT_DIM), (player.x + 24, player.y + 18))
        self.nombre_input.rect = pygame.Rect(player.x + 24, player.y + 42, 260, 38)
        draw_input(surface, self.nombre_input)
        sep = player.x + 320
        pygame.draw.line(surface, COL_CARD_BORDER, (sep, player.y + 16), (sep, player.bottom - 16), 2)
        surface.blit(self.fonts.label.render("PERSONAJE", True, COL_TEXT_DIM), (sep + 24, player.y + 18))
        portrait_box = pygame.Rect(sep + 24, player.y + 50, 76, 76)
        pygame.draw.rect(surface, COL_INPUT_BG, portrait_box, border_radius=10)
        pygame.draw.rect(surface, COL_ACCENT_DIM, portrait_box, 2, border_radius=10)
        personaje = self.assets.personajes[self.state.personaje_idx]
        surface.blit(self.assets.portraits[personaje], self.assets.portraits[personaje].get_rect(center=portrait_box.center))
        self.rect_flecha_izq = pygame.Rect(portrait_box.left - 43, portrait_box.centery - 17, 34, 34)
        self.rect_flecha_der = pygame.Rect(portrait_box.right + 9, portrait_box.centery - 17, 34, 34)
        hover = False
        for rect, symbol in ((self.rect_flecha_izq, "<"), (self.rect_flecha_der, ">")):
            over = rect.collidepoint(mouse_pos)
            pygame.draw.circle(surface, COL_OPTION_HOVER if over else COL_INPUT_BG, rect.center, 17)
            pygame.draw.circle(surface, COL_ACCENT if over else COL_INPUT_BORDER, rect.center, 17, 2)
            text = self.fonts.flecha.render(symbol, True, COL_TEXT); surface.blit(text, text.get_rect(center=rect.center))
            hover |= over
        y = player.bottom + 14; self.rect_opciones = []
        for i, modo in enumerate(self.MODOS):
            selected, available = i == self.state.opcion_seleccionada, self.DISPONIBLES[modo]
            rect = pygame.Rect(margin, y, width, 58); self.rect_opciones.append(rect)
            over = rect.collidepoint(mouse_pos) and available
            color = COL_OPTION_SELECTED if selected and available else (COL_OPTION_HOVER if over else COL_OPTION_IDLE)
            border = COL_ACCENT if selected and available else (COL_ACCENT_DIM if over else COL_CARD_BORDER)
            draw_panel(surface, rect, color, border, 10, 2 if selected or over else 1)
            icon = self.assets.iconos_modo.get(modo)
            if icon: surface.blit(icon, (rect.x + 18, rect.centery - 14))
            text_color = COL_TEXT if available else COL_TEXT_DISABLED
            surface.blit(self.fonts.opcion.render(modo, True, text_color), (rect.x + 58, rect.y + 8))
            surface.blit(self.fonts.opcion_desc.render(self.DESCRIPCIONES[modo], True, COL_TEXT_DIM if available else COL_TEXT_DISABLED), (rect.x + 60, rect.y + 35))
            hover |= over
            y = rect.bottom + 10
            if modo == "Modo Multijugador" and selected:
                hover, y = self._draw_multiplayer(surface, mouse_pos, rect, hover)
            elif modo == "Modo Libre" and selected:
                panel = pygame.Rect(rect.x + 20, rect.bottom + 8, rect.width - 40, 56)
                draw_panel(surface, panel, (26, 30, 41), COL_CARD_BORDER, 10, 1)
                self.rect_ir_libre = pygame.Rect(panel.x + 16, panel.y + 11, 205, 34)
                over = self.rect_ir_libre.collidepoint(mouse_pos)
                draw_panel(surface, self.rect_ir_libre, COL_ACCENT if over else COL_ACCENT_DIM, COL_ACCENT, 8, 2)
                text = self.fonts.pill.render("Configurar y jugar", True, (25, 20, 15)); surface.blit(text, text.get_rect(center=self.rect_ir_libre.center))
                hint = self.fonts.opcion_desc.render("elige mapa antes de empezar", True, COL_TEXT_DIM); surface.blit(hint, (self.rect_ir_libre.right + 14, self.rect_ir_libre.y + 9))
                hover |= over; y = panel.bottom + 10
        self.toast.draw(surface, margin)
        help_text = self.fonts.opcion_desc.render("↑ ↓ elige el modo   •   ← → cambia de robot   •   Enter para confirmar", True, COL_TEXT_DIM)
        surface.blit(help_text, help_text.get_rect(midbottom=(surface.get_width() // 2, surface.get_height() - 14)))
        return hover

    def _draw_multiplayer(self, surface, mouse_pos, option_rect, hover):
        client = self.state.multijugador_opcion == "cliente"
        panel = pygame.Rect(option_rect.x + 20, option_rect.bottom + 8, option_rect.width - 40, 96 if client else 56)
        draw_panel(surface, panel, (26, 30, 41), COL_CARD_BORDER, 10, 1)
        self.rect_host = pygame.Rect(panel.x + 16, panel.y + 12, 100, 32)
        self.rect_cliente = pygame.Rect(panel.x + 128, panel.y + 12, 100, 32)
        for rect, label, active in ((self.rect_host, "Host", not client), (self.rect_cliente, "Cliente", client)):
            over = rect.collidepoint(mouse_pos); hover |= over
            pygame.draw.rect(surface, COL_PILL_ACTIVE if active else COL_PILL_BG, rect, border_radius=16)
            pygame.draw.rect(surface, COL_ACCENT if active else COL_INPUT_BORDER, rect, 2, border_radius=16)
            text = self.fonts.pill.render(label, True, (20, 20, 20) if active else COL_TEXT_DIM); surface.blit(text, text.get_rect(center=rect.center))
        if client:
            surface.blit(self.fonts.opcion_desc.render("IP del servidor:", True, COL_TEXT_DIM), (panel.x + 16, panel.y + 57))
            self.ip_input.rect = pygame.Rect(panel.x + 130, panel.y + 50, 180, 30); draw_input(surface, self.ip_input)
            self.rect_conectar = pygame.Rect(self.ip_input.rect.right + 14, self.ip_input.rect.y - 2, 120, 34)
            over = self.rect_conectar.collidepoint(mouse_pos); hover |= over
            draw_panel(surface, self.rect_conectar, COL_ACCENT if over else COL_ACCENT_DIM, COL_ACCENT, 8, 2)
            text = self.fonts.pill.render("Conectar", True, (25, 20, 15)); surface.blit(text, text.get_rect(center=self.rect_conectar.center))
        else:
            hint = self.fonts.opcion_desc.render("→ abre configuración de partida", True, COL_TEXT_DIM); surface.blit(hint, (self.rect_cliente.right + 14, self.rect_host.y + 8))
        return hover, panel.bottom + 10
