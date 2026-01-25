import time
import ustruct
import framebuf
from micropython import const

# Commands
_SWRESET = const(0x01)
_SLEEPOUT = const(0x11)
_GAMMASET = const(0x26)
_DISPLAYON = const(0x29)
_CASET = const(0x2A)
_PASET = const(0x2B)
_RAMWR = const(0x2C)
_MADCTL = const(0x36)
_PIXFMT = const(0x3A)

class ILI9341:
    def __init__(self, spi, cs, dc, rst=None, bl=None, width=240, height=320, rotation=0):
        self.spi = spi
        self.cs = cs
        self.dc = dc
        self.rst = rst
        self.bl = bl
        self.width = width
        self.height = height
        
        self.cs.init(self.cs.OUT, value=1)
        self.dc.init(self.dc.OUT, value=0)
        
        if self.rst:
            self.rst.init(self.rst.OUT, value=1)
        if self.bl:
            self.bl.init(self.bl.OUT, value=1)
            
        self.reset()
        self.init_display()
        self.set_rotation(rotation)

    def reset(self):
        if self.rst:
            self.rst.value(0)
            time.sleep_ms(50)
            self.rst.value(1)
            time.sleep_ms(50)
        else:
            self.write_cmd(_SWRESET)
            time.sleep_ms(200)

    def write_cmd(self, cmd):
        self.dc.value(0)
        self.cs.value(0)
        self.spi.write(bytearray([cmd]))
        self.cs.value(1)

    def write_data(self, buf):
        self.dc.value(1)
        self.cs.value(0)
        self.spi.write(buf)
        self.cs.value(1)

    def init_display(self):
        for cmd, data, delay in [
            (_SWRESET, None, 150),
            (_SLEEPOUT, None, 500),
            (_PIXFMT, b'\x55', 10), # 16-bit color
            (_GAMMASET, b'\x01', 10),
            (_MADCTL, b'\x08', 10),
            (_DISPLAYON, None, 100),
        ]:
            self.write_cmd(cmd)
            if data:
                self.write_data(data)
            if delay:
                time.sleep_ms(delay)

    def set_window(self, x, y, w, h):
        self.write_cmd(_CASET)
        self.write_data(ustruct.pack(">HH", x, x + w - 1))
        self.write_cmd(_PASET)
        self.write_data(ustruct.pack(">HH", y, y + h - 1))
        self.write_cmd(_RAMWR)

    def set_rotation(self, rotation):
        # MADCTL values for rotation 0, 90, 180, 270
        # This depends on how the display is mounted. 
        # For CYD (landscape): often need specific MADCTL
        # 0: Portrait, 1: Landscape, 2: Inv Port, 3: Inv Land
        rotations = [0x40|0x08, 0x20|0x08, 0x80|0x08, 0x40|0x80|0x20|0x08] # Example values, may need tuning for CYD
        # CYD landscape usually requires swapping X/Y
        # Let's try standard values.
        # 0: 0x48 (MX+BGR)
        # 1: 0x28 (MV+BGR)
        # 2: 0x88 (MY+BGR)
        # 3: 0xE8 (MX+MY+MV+BGR)
        
        # Adjusting for CYD specifically which is often landscape by default or naturally portrait? 
        # Usually it's 320x240 physically.
        # Let's assume User wants Landscape (320x240).
        val = 0x08 # BGR order is common
        if rotation == 0: # Portrait
            val |= 0x40
            self.width, self.height = 240, 320
        elif rotation == 1: # Landscape
            val |= 0x20 
            self.width, self.height = 320, 240
        elif rotation == 2: # Inv Portrait
            val |= 0x80
            self.width, self.height = 240, 320
        elif rotation == 3: # Inv Landscape
            val |= 0xE0
            self.width, self.height = 320, 240
            
        self.write_cmd(_MADCTL)
        self.write_data(bytearray([val]))

    def fill_rect(self, x, y, w, h, color):
        # color is 565 16-bit
        self.set_window(x, y, w, h)
        chunk_size = 1024
        total_pixels = w * h
        color_bytes = ustruct.pack(">H", color)
        # We can optimize this if we had a large buffer, but RAM is scarce.
        # Create a small buffer
        buf = color_bytes * (chunk_size if total_pixels > chunk_size else total_pixels)
        
        remaining = total_pixels
        self.dc.value(1)
        self.cs.value(0)
        while remaining > 0:
            to_write = min(remaining, len(buf) // 2)
            self.spi.write(buf[:to_write * 2])
            remaining -= to_write
        self.cs.value(1)

    def fill(self, color):
        self.fill_rect(0, 0, self.width, self.height, color)

    def rect(self, x, y, w, h, color):
        self.fill_rect(x, y, w, 1, color)          # Top
        self.fill_rect(x, y + h - 1, w, 1, color)  # Bottom
        self.fill_rect(x, y, 1, h, color)          # Left
        self.fill_rect(x + w - 1, y, 1, h, color)  # Right

    def line(self, x0, y0, x1, y1, color):
        # Bresenham's Line Algorithm
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        
        while True:
            self.pixel(x0, y0, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy


    def pixel(self, x, y, color):
        self.set_window(x, y, 1, 1)
        self.dc.value(1)
        self.cs.value(0)
        self.spi.write(ustruct.pack(">H", color))
        self.cs.value(1)
        
    def color565(self, r, g, b):
        return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

    def draw_text(self, text, x, y, color, bg=0x0000, size=1):
        # Draw text using framebuf's 8x8 font
        # If size=1, use direct framebuf
        # If size > 1, scaling is needed (expensive in python)
        # We'll just do size=1 for now.
        w = len(text) * 8
        h = 8
        buf = bytearray(w * h * 2)
        fb = framebuf.FrameBuffer(buf, w, h, framebuf.RGB565)
        fb.fill(bg)
        fb.text(text, 0, 0, color)
        
        self.set_window(x, y, w, h)
        self.dc.value(1)
        self.cs.value(0)
        self.spi.write(buf)
        self.cs.value(1)
