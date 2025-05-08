from ssd1306 import SSD1306_I2C

class Display(SSD1306_I2C):
    """helper/extension class to SSD1306_I2C to reduce the amount of repetitive display updating"""
    def __init__(self, *args, line_spacing, **kwargs):
        super().__init__(*args, **kwargs)
        self.line_spacing = line_spacing
        
        # ppg position cache
        self._ppg_x = 0
        self._ppg_prev_y = self.height // 2
        
    def clear(self):
        self.fill(0)      
    
    def texts(self, texts, start_y = 0, clear = True):
        """display multiple lines of texts [] in the same method"""
        if clear:
            self.clear()
        
        if isinstance(texts, (str, int)):
            texts = (texts,)

        text_height = getattr(self, "text_size", 10)
        line_spacing = getattr(self, "line_spacing", 2)
        line_height = text_height + line_spacing

        for i, line in enumerate(texts):
            self.text(line, 0, start_y + i * line_height)

        self.show()
        
    def centered_texts(self, texts, start_y = 0, clear = True):
        """display multiple lines of texts [] centered (x pos) on the screen"""
        if clear:
            self.clear()

        if isinstance(texts, (str, int)):
            texts = (str(texts),)
        elif isinstance(texts, list):
            texts = tuple(texts)

        char_width = 8
        text_height = getattr(self, "text_size", 10)
        line_spacing = getattr(self, "line_spacing", 2)
        line_height = text_height + line_spacing

        for i, line in enumerate(texts):
            line_str = str(line)
            x = max((self.width - len(line_str) * char_width) // 2, 0)
            y = start_y + i * line_height
            self.text(line_str, x, y)

        self.show()
        
    def heading(self, left_text, right_text, y = 0, clear = True, clear_only_heading = False):
        """display a text on the top of the screen. supports 2 texts, 1 on the left and 1 on the right"""
        if clear:
            if clear_only_heading:
                self.fill_rect(0, y, self.width, 10, 0)
            else:
                self.clear()
            
        self.text(left_text, 0, y, 1)
        right_x = self.width - (len(right_text) * 8)
        self.text(right_text, max(right_x, 0), y, 1)
        
        self.show()
        
    def menu(self, options, pointer, start_y = 0, text_size = 10, clear = True):
        """display a scrollable menu with a pointer"""
        if clear: # since the menu needs constant refreshing, only clear the menu area
            menu_height = len(options) * (text_size + self.line_spacing)
            self.fill_rect(0, start_y, self.width, menu_height, 0)
        
        text_x_offset = 10
        
        for i, line in enumerate(options):
            y = start_y + i * (text_size + self.line_spacing)
            if i == pointer:
                self.text(">", 0, y, 1)
            self.text(line, text_x_offset, y, 1)

        self.show()
        
    def draw_ppg_graph(self, new_val, min_val, max_val):
        graph_top = 14
        graph_bottom = 58
        graph_height = graph_bottom - graph_top

        if max_val == min_val:
            return 

        scale_factor = graph_height / (max_val - min_val)
        y = int(graph_bottom - (new_val - min_val) * scale_factor)
        
        if y <= graph_top:
            y = graph_top + 1  # Prevent drawing at the top edge
        elif y >= graph_bottom:
            y = graph_bottom - 1  # Prevent drawing at the bottom edge

        self.fill_rect(self._ppg_x, graph_top, 1, graph_height, 0)

        if self._ppg_x != 0:
            self.line(self._ppg_x - 1, self._ppg_prev_y, self._ppg_x, y, 1)

        self._ppg_x = (self._ppg_x + 1) % self.width
        self._ppg_prev_y = y

        self.show()


