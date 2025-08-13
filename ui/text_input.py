import pygame

class TextInput:
    PADDING_X = 5

    def __init__(self, rect, font, max_length=22):
        self.rect = pygame.Rect(rect)
        self.font = font
        self.max_length = max_length

        # Estado del texto
        self.text = ""
        self.caret_pos = 0
        self.sel_anchor = None

        # Estado de input
        self.active = False

        # Colores
        self.color_inactive = (180, 180, 180)
        self.color_active = (255, 255, 255)
        self.color_border = (0, 0, 0)
        self.color_sel_bg = (51, 153, 255)
        self.color_sel_text = (255, 255, 255)

        # Cursor parpadeante
        self.cursor_visible = True
        self.cursor_timer = pygame.time.get_ticks()
        self.cursor_interval = 500

    # -------- Utilidades internas --------
    def _has_selection(self):
        return self.sel_anchor is not None and self.sel_anchor != self.caret_pos

    def _sel_bounds(self):
        if not self._has_selection():
            return (self.caret_pos, self.caret_pos)
        a, b = self.sel_anchor, self.caret_pos
        return (min(a, b), max(a, b))

    def _clear_selection(self):
        self.sel_anchor = None

    def _reset_cursor_blink(self):
        self.cursor_visible = True
        self.cursor_timer = pygame.time.get_ticks()

    def _clamp_caret(self):
        self.caret_pos = max(0, min(self.caret_pos, len(self.text)))

    def _index_from_mouse_x(self, mouse_x):
        local_x = mouse_x - (self.rect.x + self.PADDING_X)
        if local_x <= 0:
            return 0
        acc = 0
        for i, ch in enumerate(self.text):
            ch_w = self.font.size(ch)[0]
            if local_x < acc + ch_w / 2:
                return i
            acc += ch_w
            if local_x < acc:
                return i + 1
        return len(self.text)

    def _delete_selection_if_any(self):
        if not self._has_selection():
            return False
        i, j = self._sel_bounds()
        self.text = self.text[:i] + self.text[j:]
        self.caret_pos = i
        self._clear_selection()
        return True

    def _insert_text(self, text):
        self._delete_selection_if_any()
        if not text:
            return
        espacio = self.max_length - len(self.text)
        if espacio <= 0:
            return
        text = text[:espacio]
        self.text = self.text[:self.caret_pos] + text + self.text[self.caret_pos:]
        self.caret_pos += len(text)

    # -------- Eventos --------
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.active = True
                idx = self._index_from_mouse_x(event.pos[0])
                mods = pygame.key.get_mods()
                if mods & pygame.KMOD_SHIFT:
                    if self.sel_anchor is None:
                        self.sel_anchor = self.caret_pos
                    self.caret_pos = idx
                else:
                    self.caret_pos = idx
                    self._clear_selection()
                self._reset_cursor_blink()
            else:
                self.active = False
                self._clear_selection()

        if event.type == pygame.MOUSEMOTION and self.active:
            if event.buttons[0]:
                idx = self._index_from_mouse_x(event.pos[0])
                if self.sel_anchor is None:
                    self.sel_anchor = self.caret_pos
                self.caret_pos = idx
                self._reset_cursor_blink()

        if event.type == pygame.KEYDOWN and self.active:
            mods = event.mod

            if (mods & pygame.KMOD_CTRL) and event.key == pygame.K_a:
                self.sel_anchor = 0
                self.caret_pos = len(self.text)
                self._reset_cursor_blink()
                return

            if event.key == pygame.K_BACKSPACE:
                if not self._delete_selection_if_any():
                    if self.caret_pos > 0:
                        self.text = self.text[:self.caret_pos - 1] + self.text[self.caret_pos:]
                        self.caret_pos -= 1
                self._reset_cursor_blink()
                return

            if event.key == pygame.K_DELETE:
                if not self._delete_selection_if_any():
                    if self.caret_pos < len(self.text):
                        self.text = self.text[:self.caret_pos] + self.text[self.caret_pos + 1:]
                self._reset_cursor_blink()
                return

            if event.key == pygame.K_LEFT:
                if mods & pygame.KMOD_SHIFT:
                    if self.sel_anchor is None:
                        self.sel_anchor = self.caret_pos
                    self.caret_pos -= 1
                    self._clamp_caret()
                else:
                    self.caret_pos -= 1
                    self._clamp_caret()
                    self._clear_selection()
                self._reset_cursor_blink()
                return

            if event.key == pygame.K_RIGHT:
                if mods & pygame.KMOD_SHIFT:
                    if self.sel_anchor is None:
                        self.sel_anchor = self.caret_pos
                    self.caret_pos += 1
                    self._clamp_caret()
                else:
                    self.caret_pos += 1
                    self._clamp_caret()
                    self._clear_selection()
                self._reset_cursor_blink()
                return

            if event.key == pygame.K_HOME:
                if mods & pygame.KMOD_SHIFT:
                    if self.sel_anchor is None:
                        self.sel_anchor = self.caret_pos
                    self.caret_pos = 0
                else:
                    self.caret_pos = 0
                    self._clear_selection()
                self._reset_cursor_blink()
                return

            if event.key == pygame.K_END:
                if mods & pygame.KMOD_SHIFT:
                    if self.sel_anchor is None:
                        self.sel_anchor = self.caret_pos
                    self.caret_pos = len(self.text)
                else:
                    self.caret_pos = len(self.text)
                    self._clear_selection()
                self._reset_cursor_blink()
                return

            if event.unicode and event.unicode.isprintable():
                self._insert_text(event.unicode)
                self._reset_cursor_blink()

    # -------- Dibujo --------
    def draw(self, surface):
        pygame.draw.rect(surface, self.color_active if self.active else self.color_inactive, self.rect)
        pygame.draw.rect(surface, self.color_border, self.rect, 2)

        left = self.rect.x + self.PADDING_X
        top = self.rect.y + 5
        sel_i, sel_j = self._sel_bounds()

        if self._has_selection():
            pre_w = self.font.size(self.text[:sel_i])[0]
            sel_w = self.font.size(self.text[sel_i:sel_j])[0]
            sel_rect = pygame.Rect(left + pre_w, top, sel_w, self.font.get_height())
            sel_rect.width = min(sel_rect.width, self.rect.right - sel_rect.x - 3)
            pygame.draw.rect(surface, self.color_sel_bg, sel_rect)

        text_surf = self.font.render(self.text, True, (0, 0, 0))
        surface.blit(text_surf, (left, top))

        if self.active and (self.cursor_visible or self._has_selection()):
            caret_x = left + self.font.size(self.text[:self.caret_pos])[0]
            caret_y = top
            caret_h = self.font.get_height()
            pygame.draw.line(surface, (0, 0, 0), (caret_x, caret_y), (caret_x, caret_y + caret_h), 2)

    def update(self):
        if pygame.time.get_ticks() - self.cursor_timer >= self.cursor_interval:
            self.cursor_visible = not self.cursor_visible
            self.cursor_timer = pygame.time.get_ticks()

    def get_text(self):
        return self.text.strip()
