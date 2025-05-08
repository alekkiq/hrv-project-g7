from machine import ADC
from fifo import Fifo

class SensorFifo(Fifo):
    def __init__(self, size, pin = 26):
        super().__init__(size)
        self.sensor = ADC(pin)
        self.recording = False
        
    def handler(self, tid):
        if self.recording:
            self.put(self.sensor.read_u16())
            
    def reset(self):
        """Clear the FIFO state, making it empty."""
        self.head = 0
        self.tail = 0
        self.dc = 0
