import time
from micropython import const

class XPT2046:
    def __init__(self, spi, cs, width=240, height=320, x_min=300, y_min=200, x_max=3800, y_max=3800):
        self.spi = spi
        self.cs = cs
        self.width = width
        self.height = height
        self.x_min = x_min
        self.y_min = y_min
        self.x_max = x_max
        self.y_max = y_max
        
        self.cs.init(self.cs.OUT, value=1)

    def get_raw(self):
        # Read X, Y, Z raw
        # CMD: S A2 A1 A0 MODE SER/DFR PD1 PD0
        # X: 11010000 = 0xD0 (12-bit, differential)
        # Y: 10010000 = 0x90
        
        self.cs.value(0)
        self.spi.write(b'\xD0')
        data_x = self.spi.read(2)
        self.spi.write(b'\x90')
        data_y = self.spi.read(2)
        self.cs.value(1)
        
        val_x = ((data_x[0] << 8) | data_x[1]) >> 3
        val_y = ((data_y[0] << 8) | data_y[1]) >> 3
        
        return val_x, val_y

    def get_touch(self):
        # Simple polling, better to use IRQ in main loop to trigger this
        # Takes multiple samples to debounce
        x_sum = 0
        y_sum = 0
        samples = 3
        
        for _ in range(samples):
            raw_x, raw_y = self.get_raw()
            if raw_x == 0 or raw_y == 0 or raw_x == 4095 or raw_y == 4095:
                return None
            x_sum += raw_x
            y_sum += raw_y
            
        x_avg = x_sum // samples
        y_avg = y_sum // samples
        
        # Map to screen coordinates
        # CYD Landscape Specific Mapping (Rotation 3 approx)
        # Raw X (high to low) -> Screen Y (0 to 240)
        # Raw Y (low to high) -> Screen X (0 to 320)
        
        # Calibration constants (Average CYD)
        min_x, max_x = 300, 3900
        min_y, max_y = 200, 3800
        
        # In Landscape, XPT2046 X/Y often swap relative to Display.
        # Let's try standard Swap+Invert logic for "Rotation 3":
        # Screen X = Map(Raw Y, min_y, max_y, 0, 320) ?
        # Screen Y = Map(Raw X, min_x, max_x, 0, 240) ?
        
        # Actually usually:
        # Screen X = (Raw Y - min_y) * 320 / (max_y - min_y)
        # Screen Y = (max_x - Raw X) * 240 / (max_x - min_x)  (Inverted X to Y)
        
        # Let's try this mapping which works for many:
        # X = mapped Y (INVERTED now)
        # Y = mapped X (inverted)
        
        sx = (max_y - y_avg) * 320 // (max_y - min_y)
        sy = (max_x - x_avg) * 240 // (max_x - min_x)
        
        # Clamp
        sx = max(0, min(320 - 1, sx))
        sy = max(0, min(240 - 1, sy))
        
        return sx, sy

    def normalize(self, raw_x, raw_y):
        # Calibration logic placeholder
        return raw_x, raw_y
