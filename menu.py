class Menu:
    def __init__(self, display, options, actions, text_size = 10, start_y = 0):
        self.display = display
        self.options = options
        self.actions = actions
        self.pointer = 0
        self.text_size = text_size # does not actually change text size, but adds a bit of spacing
        self.start_y = start_y # where the menu starts
        
    def show(self, clear = True):
        self.display.menu(self.options, self.pointer, self.start_y, self.text_size, clear)
        
    def move_pointer(self, delta):
        self.pointer = max(0, min(self.pointer + delta, len(self.options) - 1))
        
    def select(self):
        return self.actions[self.pointer]

    def current_option(self):
        return self.options[self.pointer]