# ui_widgets.py
# Thư viện UI v4: Nâng cấp ListMenu có thanh cuộn (Scrollbar)

import st7789.vga2_bold_16x16 as default_font
from st7789 import st7789py
from time import sleep

# --- MÀU SẮC ---
BLACK = 0x0000
WHITE = 0xFFFF
RED = 0xF800
GREEN = 0x07E0
BLUE = 0x001F
CYAN = 0x07FF
YELLOW = 0xFFE0
GRAY = 0x8410
LIGHT_GRAY = 0xC618
DARK_GRAY = 0x4208
ORANGE = 0xFD20

class Widget:
    """Lớp cơ sở"""
    def __init__(self, tft, x, y, w, h, font=None):
        self.tft = tft
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.visible = True
        self.font = font if font is not None else default_font

    def contains(self, tx, ty):
        return self.visible and (self.x <= tx <= self.x + self.w) and (self.y <= ty <= self.y + self.h)

    def draw(self): pass

    def _draw_text_auto(self, text, x, y, color, bg):
        """Tự động chọn lệnh text() hoặc write() tùy loại font"""
        if hasattr(self.font, 'get_width'): 
            self.tft.write(self.font, text, x, y, color, bg)
        else:
            self.tft.text(self.font, text, x, y, color, bg)

    def _get_text_size(self, text):
        """Tính kích thước text"""
        if hasattr(self.font, 'get_width'):
            return self.font.get_width(text), self.font.height()
        else:
            return len(text) * self.font.WIDTH, self.font.HEIGHT

# --- CÁC WIDGET CƠ BẢN ---

class Button(Widget):
    def __init__(self, tft, x, y, w, h, text, color=BLUE, text_color=WHITE, callback=None, font=None):
        super().__init__(tft, x, y, w, h, font)
        self.text = text
        self.color = color
        self.text_color = text_color
        self.callback = callback
        self.pressed = False

    def draw(self):
        if not self.visible: return
        fill_c = GRAY if self.pressed else self.color
        self.tft.fill_rect(self.x, self.y, self.w, self.h, fill_c)
        self.tft.rect(self.x, self.y, self.w, self.h, WHITE)
        
        txt_w, txt_h = self._get_text_size(self.text)
        text_x = self.x + (self.w - txt_w) // 2
        text_y = self.y + (self.h - txt_h) // 2
        self._draw_text_auto(self.text, text_x, text_y, self.text_color, fill_c)

    def touch(self, tx, ty):
        if self.contains(tx, ty):
            self.pressed = True
            self.draw()
            sleep(0.1)
            self.pressed = False
            self.draw()
            if self.callback: self.callback(self)
            return True
        return False

class Checkbox(Widget):
    def __init__(self, tft, x, y, w=30, h=30, label="", state=False, callback=None, font=None):
        super().__init__(tft, x, y, w, h, font)
        self.label = label
        self.state = state
        self.callback = callback

    def draw(self):
        if not self.visible: return
        self.tft.rect(self.x, self.y, self.w, self.h, WHITE)
        fill = GREEN if self.state else BLACK
        self.tft.fill_rect(self.x + 4, self.y + 4, self.w - 8, self.h - 8, fill)
        
        if self.label:
            _, txt_h = self._get_text_size(self.label)
            txt_y = self.y + (self.h - txt_h) // 2
            self._draw_text_auto(self.label, self.x + self.w + 10, txt_y, WHITE, BLACK)

    def touch(self, tx, ty):
        click_w = self.w + (100 if self.label else 0)
        if self.visible and (self.x <= tx <= self.x + click_w) and (self.y <= ty <= self.y + self.h):
            self.state = not self.state
            self.draw()
            if self.callback: self.callback(self.state)
            return True
        return False

# --- WIDGET NÂNG CẤP: LIST MENU CÓ SCROLL ---

class ListMenu(Widget):
    """Menu danh sách có thanh cuộn bên phải"""
    def __init__(self, tft, x, y, w, h, items, callback=None, font=None):
        super().__init__(tft, x, y, w, h, font)
        self.items = items 
        self.callback = callback
        self.selected_index = -1
        
        # Cấu hình kích thước dòng
        _, font_h = self._get_text_size("A")
        self.item_h = font_h + 16 # Padding thoáng hơn
        
        # Tính số dòng hiển thị được
        self.visible_rows = self.h // self.item_h
        self.start_index = 0 # Vị trí bắt đầu hiển thị
        
        # Cấu hình thanh cuộn
        self.scrollbar_w = 40 # Độ rộng thanh cuộn
        self.list_w = self.w - self.scrollbar_w # Độ rộng phần list

    def draw(self):
        if not self.visible: return
        
        # 1. Vẽ nền List
        self.tft.fill_rect(self.x, self.y, self.list_w, self.h, BLACK)
        self.tft.rect(self.x, self.y, self.list_w, self.h, WHITE)
        
        # 2. Vẽ các Item (chỉ vẽ các mục trong vùng nhìn thấy)
        end_index = min(self.start_index + self.visible_rows, len(self.items))
        
        for i in range(self.start_index, end_index):
            # Vị trí vẽ (relative so với start_index)
            rel_idx = i - self.start_index
            item_y = self.y + (rel_idx * self.item_h)
            
            # Highlight
            if i == self.selected_index:
                self.tft.fill_rect(self.x + 2, item_y + 2, self.list_w - 4, self.item_h - 4, BLUE)
                text_col = WHITE
                bg_col = BLUE
            else:
                self.tft.rect(self.x + 2, item_y + 2, self.list_w - 4, self.item_h - 4, DARK_GRAY)
                text_col = WHITE
                bg_col = BLACK
            
            # Căn giữa text
            item_text = self.items[i]
            txt_w, txt_h = self._get_text_size(item_text)
            # Cắt bớt text nếu quá dài
            if txt_w > self.list_w - 15:
                item_text = item_text[:15] + ".."
            
            text_offset_y = (self.item_h - txt_h) // 2
            self._draw_text_auto(item_text, self.x + 10, item_y + text_offset_y, text_col, bg_col)

        # 3. Vẽ thanh cuộn (Bên phải)
        sb_x = self.x + self.list_w
        btn_h = self.h // 2
        
        # Nút Lên (UP)
        self.tft.fill_rect(sb_x, self.y, self.scrollbar_w, btn_h, DARK_GRAY)
        self.tft.rect(sb_x, self.y, self.scrollbar_w, btn_h, WHITE)
        self._draw_arrow(sb_x + self.scrollbar_w//2, self.y + btn_h//2, "UP")
        
        # Nút Xuống (DOWN)
        self.tft.fill_rect(sb_x, self.y + btn_h, self.scrollbar_w, btn_h, DARK_GRAY)
        self.tft.rect(sb_x, self.y + btn_h, self.scrollbar_w, btn_h, WHITE)
        self._draw_arrow(sb_x + self.scrollbar_w//2, self.y + btn_h + btn_h//2, "DOWN")

    def _draw_arrow(self, cx, cy, direction):
        """Vẽ tam giác đơn giản"""
        size = 10
        color = YELLOW
        if direction == "UP":
            # Đỉnh ở trên
            p1 = (cx, cy - size)
            p2 = (cx - size, cy + size)
            p3 = (cx + size, cy + size)
        else:
            # Đỉnh ở dưới
            p1 = (cx, cy + size)
            p2 = (cx - size, cy - size)
            p3 = (cx + size, cy - size)
        
        try:
            self.tft.polygon([p1, p2, p3], 0, 0, color)
            # Fill giả bằng cách vẽ thêm 1 tam giác nhỏ hơn (nếu thư viện hỗ trợ fill polygon thì tốt hơn)
        except:
            # Fallback nếu không có polygon: Vẽ ký tự
            char = "^" if direction == "UP" else "v"
            self.tft.text(default_font, char, cx - 8, cy - 8, WHITE, DARK_GRAY)

    def scroll_up(self):
        if self.start_index > 0:
            self.start_index -= 1
            self.draw()

    def scroll_down(self):
        if self.start_index + self.visible_rows < len(self.items):
            self.start_index += 1
            self.draw()

    def touch(self, tx, ty):
        if not self.contains(tx, ty): return False
        
        # Kiểm tra xem bấm vào Thanh cuộn hay Danh sách
        if tx > self.x + self.list_w:
            # --- BẤM VÀO THANH CUỘN ---
            btn_h = self.h // 2
            if ty < self.y + btn_h:
                self.scroll_up()
            else:
                self.scroll_down()
            return True
        else:
            # --- BẤM VÀO ITEM ---
            # Tính offset y tương đối so với widget
            rel_y = ty - self.y
            row_idx = rel_y // self.item_h
            
            # Index thực tế trong mảng items
            actual_idx = self.start_index + row_idx
            
            if 0 <= actual_idx < len(self.items):
                self.selected_index = actual_idx
                self.draw()
                sleep(0.1)
                self.selected_index = -1 
                self.draw()
                
                if self.callback:
                    self.callback(self.items[actual_idx])
                return True
        return False

class InputField(Widget):
    # (Giữ nguyên như phiên bản trước)
    def __init__(self, tft, x, y, w, h, label="Input:", initial_text="", font=None):
        super().__init__(tft, x, y, w, h, font)
        self.label = label
        self.text = initial_text
        self.keyboard = None 
        
    def set_keyboard(self, kbd):
        self.keyboard = kbd

    def draw(self):
        if not self.visible: return
        self._draw_text_auto(self.label, self.x, self.y, YELLOW, BLACK)
        _, font_h = self._get_text_size("A")
        box_h = font_h + 10
        box_y = self.y + font_h + 5 
        self.tft.fill_rect(self.x, box_y, self.w, box_h, BLACK) 
        self.tft.rect(self.x, box_y, self.w, box_h, WHITE)
        self._draw_text_auto(self.text, self.x + 5, box_y + 5, WHITE, BLACK)
        text_w, _ = self._get_text_size(self.text)
        cursor_x = self.x + 5 + text_w
        if cursor_x < self.x + self.w - 10:
            self._draw_text_auto("_", cursor_x, box_y + 5, GREEN, BLACK)

    def add_char(self, char):
        txt_w, _ = self._get_text_size(self.text + char)
        if txt_w < self.w - 15: 
            self.text += char
            self.draw()
            
    def del_char(self):
        if len(self.text) > 0:
            self.text = self.text[:-1]
            self.draw()

    def touch(self, tx, ty):
        if self.visible and (self.x <= tx <= self.x + self.w) and (self.y <= ty <= self.y + 60):
            if self.keyboard:
                self.keyboard.input_field = self 
                self.keyboard.show()
            return True
        return False

class OnScreenKeyboard(Widget):
    # (Giữ nguyên như phiên bản trước, nhưng cần import class Widget nếu tách file)
    # Để ngắn gọn tôi không paste lại phần này nếu bạn đã có, 
    # nhưng nếu bạn copy đè file thì hãy copy lại phần Keyboard từ câu trả lời trước nhé.
    # Dưới đây là bản tóm tắt để file chạy được:
    def __init__(self, tft, input_field, callback_ok=None):
        super().__init__(tft, 0, 110, 320, 130, font=None) 
        self.input_field = input_field 
        self.callback_ok = callback_ok
        self.visible = False 
        self.rows = ["1234567890", "qwertyuiop", "asdfghjkl", " zxcvbnm "]
        
    def show(self): self.visible = True; self.draw()
    def hide(self): self.visible = False; self.tft.fill_rect(self.x, self.y, self.w, self.h, BLACK)
        
    def draw(self):
        if not self.visible: return
        self.tft.fill_rect(self.x, self.y, self.w, self.h, DARK_GRAY)
        key_w, key_h = 32, 25
        for r_idx, row_str in enumerate(self.rows):
            for c_idx, char in enumerate(row_str):
                if char == ' ': continue 
                kx = self.x + c_idx * key_w
                ky = self.y + r_idx * key_h + 5
                self.tft.fill_rect(kx+1, ky+1, key_w-2, key_h-2, LIGHT_GRAY)
                self.tft.text(default_font, char, kx+8, ky+4, BLACK, LIGHT_GRAY)
        # Nút OK/DEL đơn giản
        self.tft.fill_rect(240, self.y+105, 70, 20, BLUE)
        self.tft.text(default_font, "OK", 260, self.y+107, WHITE, BLUE)

    def touch(self, tx, ty):
        if not self.visible or not self.contains(tx, ty): return False
        if ty > self.y + 105 and tx > 240: 
            self.hide(); 
            if self.callback_ok: self.callback_ok(self.input_field.text)
            return True
        # Xử lý phím bấm cơ bản
        key_w, key_h = 32, 25
        rel_y = ty - self.y - 5
        row_idx = rel_y // key_h
        if 0 <= row_idx < 4:
            col_idx = (tx - self.x) // key_w
            if col_idx < len(self.rows[row_idx]):
                char = self.rows[row_idx][col_idx]
                if char != ' ': self.input_field.add_char(char); return True
        return False