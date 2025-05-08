from machine import Pin

class Button(Pin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.press = 0
        self.release = 0
        self.state = False
        self.down = False

    def pressed(self):
        if self.value() == 0:
            self.release = 0
            self.press += 1
            if self.press >= 3:
                self.press = 3
                self.state = True
        else:
            self.press = 0
            self.release += 1
            if self.release >= 3:
                self.release = 3
                self.state = False
        return self.state
    
    def single_press(self):
        if self.down:
            if not self.pressed():
                self.down = False
        else:
            if self.pressed():
                self.down = True
                return True
        return False

class Switch(Button):
    pass