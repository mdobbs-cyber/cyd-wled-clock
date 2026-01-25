import socket
import json
import time
import ntptime
from micropython import const

# Colors
C_BLACK = 0x0000
C_WHITE = 0xFFFF
C_RED = 0xF800
C_GREEN = 0x07E0
C_BLUE = 0x001F
C_PINK = 0xF81F
C_GREY = 0x8410
C_DARK = 0x4208
C_YELLOW = 0xFFE0

import vector_font

class DashboardApp:
    def __init__(self, display, config):
        self.display = display
        self.ip = config.get('wled_ip', '')
        self.tz_offset = config.get('timezone_offset', 0)
        self.port = 80
        self.brightness = 128
        
        self.mode = "CLOCK" # CLOCK or CONTROL
        self.last_interaction = time.time()
        self.TIMEOUT = 30 # seconds
        
        self.last_draw_min = -1
        # Vector Font Instances
        # Small Clock: 32x50
        self.font_small = vector_font.VectorFont(display, 32, 50)
        
        # Large Clock: 50x90
        self.font_large = vector_font.VectorFont(display, 50, 90)
        
        # WLED Buttons
        btn_y = 90
        btn_h = 40
        self.buttons = [
            ("ON", 20, btn_y, 130, btn_h, C_WHITE, {"on": True}),
            ("OFF", 170, btn_y, 130, btn_h, C_GREY, {"on": False}),
            
            ("WHT", 10, 140, 50, btn_h, C_WHITE, {"seg": [{"col": [[255, 255, 255]]}]}),
            ("RED", 70, 140, 50, btn_h, C_RED, {"seg": [{"col": [[255, 0, 0]]}]}),
            ("GRN", 130, 140, 50, btn_h, C_GREEN, {"seg": [{"col": [[0, 255, 0]]}]}),
            ("BLU", 190, 140, 50, btn_h, C_BLUE, {"seg": [{"col": [[0, 0, 255]]}]}),
            ("PNK", 250, 140, 50, btn_h, C_PINK, {"seg": [{"col": [[255, 0, 128]]}]}),
        ]
        
        self.slider_y = 200
        self.slider_h = 25
        self.slider_min_x = 20
        self.slider_max_x = 300

    def sync_time(self):
        try:
            print("Syncing NTP...")
            ntptime.settime()
            print("NTP Synced")
            self.last_draw_min = -1
        except Exception as e:
            print("NTP Failed:", e)

    def switch_mode(self, new_mode):
        self.mode = new_mode
        self.last_draw_min = -1 # Force redraw
        self.display.fill(C_BLACK)
        
        if self.mode == "CONTROL":
            self.draw_static_ui()
            self.draw_clock_small(force=True)
        elif self.mode == "CLOCK":
            self.draw_clock_large(force=True)
            
        self.last_interaction = time.time()

    def draw_static_ui(self):
        # Draw Buttons
        for label, x, y, w, h, col, _ in self.buttons:
            self.display.fill_rect(x, y, w, h, col)
            txt_col = C_BLACK if col in [C_WHITE, C_GREEN, C_YELLOW] else C_WHITE
            tx = x + (w - len(label)*8)//2
            ty = y + (h - 8)//2
            self.display.draw_text(label, tx, ty, txt_col, col)

        # Draw Slider Track
        self.display.draw_text("BRIGHTNESS", 120, 188, C_WHITE)
        self.display.rect(self.slider_min_x, self.slider_y, self.slider_max_x - self.slider_min_x, self.slider_h, C_WHITE)
        self.update_slider_knob(self.brightness)

    def update_slider_knob(self, val):
        self.brightness = val
        range_px = self.slider_max_x - self.slider_min_x
        knob_x = self.slider_min_x + int((val / 255.0) * range_px)
        self.display.fill_rect(self.slider_min_x + 1, self.slider_y + 1, range_px - 2, self.slider_h - 2, C_BLACK)
        self.display.fill_rect(knob_x - 5, self.slider_y, 10, self.slider_h, C_RED)

    def get_time_tuple(self):
        return time.localtime(time.time() + self.tz_offset * 3600)

    def draw_clock_small(self, force=False):
        now = self.get_time_tuple()
        h_24 = now[3]
        m = now[4]
        
        if m != self.last_draw_min or force:
            self.display.fill_rect(0, 0, 320, 85, C_BLACK)
            
            h_12 = h_24 % 12
            if h_12 == 0: h_12 = 12
            ampm = "AM" if h_24 < 12 else "PM"
            
            # Layout (Small)
            start_x = 72
            y = 10
            color = C_WHITE
            
            if h_12 >= 10:
                self.font_small.draw_digit(h_12 // 10, start_x, y, color)
            self.font_small.draw_digit(h_12 % 10, start_x + 40, y, color)
            
            # Colon (+92)
            self.display.fill_rect(start_x + 92, y + 15, 6, 6, C_WHITE)
            self.display.fill_rect(start_x + 92, y + 35, 6, 6, C_WHITE)
            
            self.font_small.draw_digit(m // 10, start_x + 100, y, color)
            self.font_small.draw_digit(m % 10, start_x + 140, y, color)
            
            self.display.draw_text(ampm, start_x + 190, y + 35, C_YELLOW, C_BLACK)
            
            date_str = "{:04}-{:02}-{:02}".format(now[0], now[1], now[2])
            self.display.draw_text(date_str, 120, 65, C_GREY, C_BLACK)
            
            self.last_draw_min = m

    def draw_clock_large(self, force=False):
        now = self.get_time_tuple()
        h_24 = now[3]
        m = now[4]
        
        if m != self.last_draw_min or force:
            if not force:
                self.display.fill(C_BLACK)
                
            h_12 = h_24 % 12
            if h_12 == 0: h_12 = 12
            ampm = "AM" if h_24 < 12 else "PM"
            
            # Layout (Large)
            start_x = 20
            y = 60
            color = C_GREEN
            
            if h_12 >= 10:
                self.font_large.draw_digit(h_12 // 10, start_x, y, color)
            self.font_large.draw_digit(h_12 % 10, start_x + 60, y, color)
            
            # Colon
            self.display.fill_rect(start_x + 120, y + 30, 8, 8, C_WHITE)
            self.display.fill_rect(start_x + 120, y + 60, 8, 8, C_WHITE)
            
            self.font_large.draw_digit(m // 10, start_x + 140, y, color)
            self.font_large.draw_digit(m % 10, start_x + 200, y, color)
            
            self.display.draw_text(ampm, 280, y + 70, C_YELLOW, C_BLACK)
            
            date_str = "{:04}-{:02}-{:02}".format(now[0], now[1], now[2])
            self.display.draw_text(date_str, 110, 180, color, C_BLACK)
            
            self.last_draw_min = m

    def update(self):
        current_time = time.time()
        
        # Check Timeout
        if self.mode == "CONTROL":
            if current_time - self.last_interaction > self.TIMEOUT:
                # print("Timeout -> CLOCK")
                self.switch_mode("CLOCK")
                return

        # Draw
        if self.mode == "CONTROL":
            self.draw_clock_small()
        else:
            self.draw_clock_large()

    def send_wled(self, data):
        try:
            addr = socket.getaddrinfo(self.ip, self.port)[0][-1]
            s = socket.socket()
            s.settimeout(0.5)
            s.connect(addr)
            json_str = json.dumps(data)
            req = "POST /json/state HTTP/1.1\r\nHost: {}\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}".format(self.ip, len(json_str), json_str)
            s.send(req.encode())
            s.close()
        except Exception as e:
            print("WLED Err:", e)

    def handle_touch(self, x, y):
        self.last_interaction = time.time()
        
        # If in Clock mode, wake up
        if self.mode == "CLOCK":
            self.switch_mode("CONTROL")
            return
            
        # CONTROL Mode Logic
        
        # Check Control Buttons
        for label, bx, by, bw, bh, _, data in self.buttons:
            if bx <= x <= bx+bw and by <= y <= by+bh:
                print("Button:", label)
                self.send_wled(data)
                return
        
        # Check Slider
        if self.slider_min_x <= x <= self.slider_max_x and (self.slider_y - 10) <= y <= (self.slider_y + self.slider_h + 10):
            range_px = self.slider_max_x - self.slider_min_x
            pct = (x - self.slider_min_x) / range_px
            val = int(pct * 255)
            val = max(0, min(255, val))
            
            # print("Slider:", val)
            self.update_slider_knob(val)
            self.send_wled({"bri": val})
