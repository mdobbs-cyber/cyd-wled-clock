import socket
import json
import time
import ntptime
import dst
from micropython import const

# ---------------------------------------------------------------------------
# RGB565 Color constants
# ---------------------------------------------------------------------------
C_BLACK  = const(0x0000)
C_WHITE  = const(0xFFFF)
C_RED    = const(0xF800)
C_GREEN  = const(0x07E0)
C_BLUE   = const(0x001F)
C_PINK   = const(0xF81F)
C_GREY   = const(0x8410)
C_DARK   = const(0x4208)
C_YELLOW = const(0xFFE0)
C_CYAN   = const(0x07FF)
C_ORANGE = const(0xFD20)
C_PURPLE = const(0x780F)

# ---------------------------------------------------------------------------
# Colour palette available in the Settings colour pickers (tap to cycle)
# ---------------------------------------------------------------------------
PALETTE = [
    ("GREEN",  C_GREEN),
    ("WHITE",  C_WHITE),
    ("CYAN",   C_CYAN),
    ("YELLOW", C_YELLOW),
    ("ORANGE", C_ORANGE),
    ("RED",    C_RED),
    ("PINK",   C_PINK),
    ("BLUE",   C_BLUE),
    ("PURPLE", C_PURPLE),
    ("BLACK",  C_BLACK),
]
PALETTE_COLORS = [c for _, c in PALETTE]

import vector_font


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _palette_index(color):
    """Return index of color in PALETTE_COLORS, or 0 if not found."""
    try:
        return PALETTE_COLORS.index(color)
    except ValueError:
        return 0


def _next_palette_color(color):
    """Cycle to the next color in the palette."""
    idx = (_palette_index(color) + 1) % len(PALETTE_COLORS)
    return PALETTE_COLORS[idx]


def _rgb565_to_888(c):
    """Convert RGB565 int to (r, g, b) 8-bit tuple."""
    r = ((c >> 11) & 0x1F) << 3
    g = ((c >> 5)  & 0x3F) << 2
    b = ( c        & 0x1F) << 3
    return r, g, b


def _contrasting_text(bg):
    """Return C_BLACK or C_WHITE depending on bg luminance."""
    r, g, b = _rgb565_to_888(bg)
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    return C_BLACK if lum > 128 else C_WHITE


# ---------------------------------------------------------------------------
# DashboardApp
# ---------------------------------------------------------------------------
class DashboardApp:

    # --- Modes ---
    MODE_CLOCK    = "CLOCK"
    MODE_CONTROL  = "CONTROL"
    MODE_SETTINGS = "SETTINGS"

    def __init__(self, display, config, bl_pwm=None):
        self.display  = display
        self.config   = config
        self.bl_pwm   = bl_pwm

        # WLED
        self.ip   = config.get('wled_ip', '')
        self.port = 80

        # Timezone / DST
        self.tz_offset   = config.get('timezone_offset', 0)
        self.dst_enabled = config.get('dst_enabled', True)

        # ---- Colour settings (loaded from config, defaults to classic look) ----
        self.color_bg    = config.get('color_bg',    C_BLACK)
        self.color_digit = config.get('color_digit', C_GREEN)
        self.color_ampm  = config.get('color_ampm',  C_YELLOW)
        self.color_date  = config.get('color_date',  C_GREY)

        # Brightness: 0-255 for config; 0-1023 for PWM duty
        self.display_brightness = config.get('display_brightness', 200)

        # WLED brightness (separate from display backlight)
        self.wled_brightness = 128

        # Mode / interaction
        self.mode             = self.MODE_CLOCK
        self.last_interaction = time.time()
        self.TIMEOUT          = 30  # seconds before CONTROL auto-returns to CLOCK

        self.last_draw_min = -1
        self.last_draw_sec = -1  # used to blink colon

        # Vector Font instances
        self.font_small = vector_font.VectorFont(display, 32, 50)   # 32×50 px per digit
        self.font_large = vector_font.VectorFont(display, 50, 90)   # 50×90 px per digit

        # ---- CONTROL screen — WLED Buttons ----
        btn_y = 90
        btn_h = 40
        self.wled_buttons = [
            ("ON",  20,  btn_y, 130, btn_h, C_WHITE, {"on": True}),
            ("OFF", 170, btn_y, 130, btn_h, C_GREY,  {"on": False}),

            ("WHT",  10, 140, 50, btn_h, C_WHITE, {"seg": [{"col": [[255, 255, 255]]}]}),
            ("RED",  70, 140, 50, btn_h, C_RED,   {"seg": [{"col": [[255, 0,   0  ]]}]}),
            ("GRN", 130, 140, 50, btn_h, C_GREEN, {"seg": [{"col": [[0,   255, 0  ]]}]}),
            ("BLU", 190, 140, 50, btn_h, C_BLUE,  {"seg": [{"col": [[0,   0,   255]]}]}),
            ("PNK", 250, 140, 50, btn_h, C_PINK,  {"seg": [{"col": [[255, 0,   128]]}]}),
        ]

        # WLED brightness slider (CONTROL screen)
        self.wled_slider_y     = 200
        self.wled_slider_h     = 25
        self.wled_slider_min_x = 20
        self.wled_slider_max_x = 260  # leave room for ⚙ button

        # ---- SETTINGS screen layout ----
        # Vertical brightness bar occupies the far-right column (x=294..318)
        # Colour swatches fill the remaining width (x=0..285)
        self._bl_bar_x = 294   # left edge of vertical bar
        self._bl_bar_y = 10    # top of bar
        self._bl_bar_w = 20    # bar width
        self._bl_bar_h = 178   # bar height (ends at y≈188)

        # Four colour pickers: BG, Digit, AM/PM, Date
        self._settings_rows = [
            # (label,       attr_name,    y)
            ("Background",  "color_bg",   18),
            ("Digits",      "color_digit", 62),
            ("AM / PM",     "color_ampm", 106),
            ("Date",        "color_date", 150),
        ]
        # Swatch geometry — shifted left to leave room for brightness bar
        self._sw_x = 92    # x start of colour swatch
        self._sw_w = 196   # swatch width (reaches x≈288)
        self._sw_h = 36    # swatch height

    # -----------------------------------------------------------------------
    # Time helpers
    # -----------------------------------------------------------------------
    def sync_time(self):
        try:
            print("Syncing NTP...")
            ntptime.settime()
            print("NTP Synced")
            self.last_draw_min = -1
        except Exception as e:
            print("NTP Failed:", e)

    def get_time_tuple(self):
        """Return local time tuple with TZ and DST applied."""
        now_utc = time.time()
        # Compute the current standard-time local time for DST check
        # (use the UTC time + std offset to get approx local datetime)
        std_local = time.localtime(now_utc + self.tz_offset * 3600)
        dst_offset = 0
        if self.dst_enabled:
            dst_offset = dst.get_dst_offset(
                std_local[0], std_local[1], std_local[2], std_local[3]
            )
        return time.localtime(now_utc + (self.tz_offset + dst_offset) * 3600)

    # -----------------------------------------------------------------------
    # Backlight
    # -----------------------------------------------------------------------
    def _apply_backlight(self, bri_0_255):
        """Set backlight PWM from 0-255 value."""
        if self.bl_pwm is not None:
            duty = int(bri_0_255 / 255 * 1023)
            self.bl_pwm.duty(duty)

    # -----------------------------------------------------------------------
    # Config persistence
    # -----------------------------------------------------------------------
    def _save_config(self):
        """Write current colour & brightness settings back to config.json."""
        self.config['color_bg']           = self.color_bg
        self.config['color_digit']        = self.color_digit
        self.config['color_ampm']         = self.color_ampm
        self.config['color_date']         = self.color_date
        self.config['display_brightness'] = self.display_brightness
        try:
            with open('config.json', 'w') as f:
                json.dump(self.config, f)
            print("Config saved")
        except Exception as e:
            print("Config save error:", e)

    # -----------------------------------------------------------------------
    # Mode switching
    # -----------------------------------------------------------------------
    def switch_mode(self, new_mode):
        if new_mode == self.MODE_SETTINGS and self.mode != self.MODE_SETTINGS:
            # Save any pending state before entering settings
            pass

        self.mode          = new_mode
        self.last_draw_min = -1
        self.last_draw_sec = -1
        self.display.fill(self.color_bg)

        if self.mode == self.MODE_CONTROL:
            self._draw_control_static()
            self.draw_clock_small(force=True)
        elif self.mode == self.MODE_CLOCK:
            self.draw_clock_large(force=True)
        elif self.mode == self.MODE_SETTINGS:
            self._draw_settings_screen()

        self.last_interaction = time.time()

    # -----------------------------------------------------------------------
    # CONTROL screen — static elements
    # -----------------------------------------------------------------------
    def _draw_control_static(self):
        """Draw WLED buttons, slider, and the ⚙ Colors nav button."""
        # WLED on/off + colour buttons
        for label, x, y, w, h, col, _ in self.wled_buttons:
            self.display.fill_rect(x, y, w, h, col)
            txt_col = _contrasting_text(col)
            tx = x + (w - len(label) * 8) // 2
            ty = y + (h - 8) // 2
            self.display.draw_text(label, tx, ty, txt_col, col)

        # WLED brightness slider
        self.display.draw_text("WLED BRIGHTNESS", 80, 188, C_WHITE)
        self.display.rect(
            self.wled_slider_min_x, self.wled_slider_y,
            self.wled_slider_max_x - self.wled_slider_min_x, self.wled_slider_h,
            C_WHITE
        )
        self._draw_wled_slider_knob(self.wled_brightness)

        # ⚙ COLORS navigation button (bottom-right)
        self._draw_settings_nav_btn()

    def _draw_settings_nav_btn(self):
        bx, by, bw, bh = 270, 195, 45, 35
        self.display.fill_rect(bx, by, bw, bh, C_DARK)
        self.display.rect(bx, by, bw, bh, C_GREY)
        self.display.draw_text("CLR", bx + 5, by + 5, C_WHITE, C_DARK)
        self.display.draw_text("SET", bx + 5, by + 17, C_WHITE, C_DARK)

    def _draw_wled_slider_knob(self, val):
        self.wled_brightness = val
        r = self.wled_slider_min_x
        w = self.wled_slider_max_x - r
        knob_x = r + int((val / 255.0) * w)
        self.display.fill_rect(r + 1, self.wled_slider_y + 1, w - 2, self.wled_slider_h - 2, C_BLACK)
        self.display.fill_rect(knob_x - 5, self.wled_slider_y, 10, self.wled_slider_h, C_RED)

    # -----------------------------------------------------------------------
    # SETTINGS screen
    # -----------------------------------------------------------------------
    def _draw_settings_screen(self):
        """Render the full settings screen."""
        self.display.fill(C_BLACK)

        # Title
        self.display.draw_text("CLOCK SETTINGS", 70, 3, C_CYAN, C_BLACK)

        # Colour picker rows
        for label, attr, row_y in self._settings_rows:
            self._draw_swatch_row(label, attr, row_y)

        # Vertical brightness bar (far right)
        self._draw_bl_bar_static()
        self._draw_bl_bar_fill(self.display_brightness)

        # Navigation buttons
        self._draw_back_btn()
        self._draw_home_btn()
        self._draw_save_btn()

    def _draw_swatch_row(self, label, attr, row_y):
        """Draw label + colour swatch for one settings row."""
        color = getattr(self, attr)
        # Label (left side, ~88px wide column)
        self.display.draw_text(label, 3, row_y + 13, C_WHITE, C_BLACK)
        # Swatch box
        self.display.fill_rect(self._sw_x, row_y, self._sw_w, self._sw_h, color)
        self.display.rect(self._sw_x, row_y, self._sw_w, self._sw_h, C_GREY)
        # Color name centred inside swatch
        name = PALETTE[_palette_index(color)][0]
        txt_col = _contrasting_text(color)
        name_x = self._sw_x + (self._sw_w - len(name) * 8) // 2
        self.display.draw_text(name, name_x, row_y + 14, txt_col, color)

    # --- Vertical brightness bar (SETTINGS screen) ---

    def _draw_bl_bar_static(self):
        """Draw the outline and label for the vertical brightness bar."""
        bx = self._bl_bar_x
        by = self._bl_bar_y
        bw = self._bl_bar_w
        bh = self._bl_bar_h
        self.display.rect(bx, by, bw, bh, C_WHITE)
        # "BRI" label above bar
        self.display.draw_text("BRI", bx, by - 11, C_WHITE, C_BLACK)

    def _draw_bl_bar_fill(self, val):
        """Fill the brightness bar from the bottom up to indicate level."""
        self.display_brightness = val
        bx = self._bl_bar_x + 1
        by = self._bl_bar_y + 1
        bw = self._bl_bar_w - 2
        bh = self._bl_bar_h - 2
        # Clear interior
        self.display.fill_rect(bx, by, bw, bh, C_BLACK)
        # Fill from bottom upward
        fill_h = int(val / 255.0 * bh)
        if fill_h > 0:
            self.display.fill_rect(bx, by + bh - fill_h, bw, fill_h, C_CYAN)
        self._apply_backlight(val)

    # --- Navigation buttons ---

    def _draw_back_btn(self):
        """< BACK — returns to CONTROL screen (does NOT auto-save)."""
        bx, by, bw, bh = 3, 202, 78, 32
        self.display.fill_rect(bx, by, bw, bh, C_DARK)
        self.display.rect(bx, by, bw, bh, C_GREY)
        self.display.draw_text("< BACK", bx + 10, by + 11, C_WHITE, C_DARK)

    def _draw_home_btn(self):
        """HOME — returns directly to the clock face (does NOT auto-save)."""
        bx, by, bw, bh = 89, 202, 78, 32
        self.display.fill_rect(bx, by, bw, bh, C_DARK)
        self.display.rect(bx, by, bw, bh, C_CYAN)
        self.display.draw_text("* HOME", bx + 8, by + 11, C_CYAN, C_DARK)

    def _draw_save_btn(self, saved=False):
        """SAVE — writes settings to config.json."""
        bx, by, bw, bh = 175, 202, 78, 32
        col = C_GREEN if saved else C_DARK
        txt = " SAVED" if saved else " SAVE "
        self.display.fill_rect(bx, by, bw, bh, col)
        border = C_GREEN
        self.display.rect(bx, by, bw, bh, border)
        txt_col = C_BLACK if saved else C_GREEN
        self.display.draw_text(txt, bx + 8, by + 11, txt_col, col)

    # -----------------------------------------------------------------------
    # Clock drawing — small (used in CONTROL mode header)
    # -----------------------------------------------------------------------
    def draw_clock_small(self, force=False):
        now  = self.get_time_tuple()
        h_24 = now[3]
        m    = now[4]

        if m != self.last_draw_min or force:
            self.display.fill_rect(0, 0, 320, 85, self.color_bg)

            h_12 = h_24 % 12
            if h_12 == 0:
                h_12 = 12
            ampm = "AM" if h_24 < 12 else "PM"

            start_x = 72
            y       = 10

            if h_12 >= 10:
                self.font_small.draw_digit(h_12 // 10, start_x, y, self.color_digit)
            self.font_small.draw_digit(h_12 % 10, start_x + 40, y, self.color_digit)

            # Colon
            self.display.fill_rect(start_x + 92, y + 15, 6, 6, C_WHITE)
            self.display.fill_rect(start_x + 92, y + 35, 6, 6, C_WHITE)

            self.font_small.draw_digit(m // 10, start_x + 100, y, self.color_digit)
            self.font_small.draw_digit(m % 10,  start_x + 140, y, self.color_digit)

            self.display.draw_text(ampm, start_x + 190, y + 35, self.color_ampm, self.color_bg)

            date_str = "{:04}-{:02}-{:02}".format(now[0], now[1], now[2])
            self.display.draw_text(date_str, 120, 65, self.color_date, self.color_bg)

            self.last_draw_min = m

    # -----------------------------------------------------------------------
    # Clock drawing — large (CLOCK mode)
    # -----------------------------------------------------------------------
    def draw_clock_large(self, force=False):
        now  = self.get_time_tuple()
        h_24 = now[3]
        m    = now[4]
        s    = now[5]

        # Redraw digits only when minute changes (or forced)
        if m != self.last_draw_min or force:
            if not force:
                self.display.fill(self.color_bg)

            h_12 = h_24 % 12
            if h_12 == 0:
                h_12 = 12
            ampm = "AM" if h_24 < 12 else "PM"

            start_x = 20
            y       = 55

            if h_12 >= 10:
                self.font_large.draw_digit(h_12 // 10, start_x, y, self.color_digit)
            self.font_large.draw_digit(h_12 % 10, start_x + 60, y, self.color_digit)

            # Colon (static, managed per-second below)
            self.display.fill_rect(start_x + 120, y + 28, 8, 8, C_WHITE)
            self.display.fill_rect(start_x + 120, y + 58, 8, 8, C_WHITE)

            self.font_large.draw_digit(m // 10, start_x + 140, y, self.color_digit)
            self.font_large.draw_digit(m % 10,  start_x + 200, y, self.color_digit)

            self.display.draw_text(ampm, 280, y + 72, self.color_ampm, self.color_bg)

            date_str = "{:04}-{:02}-{:02}".format(now[0], now[1], now[2])
            self.display.draw_text(date_str, 100, 175, self.color_date, self.color_bg)

            # DST indicator
            dst_active = dst.get_dst_offset(now[0], now[1], now[2], now[3]) if self.dst_enabled else 0
            dst_label  = "DST" if dst_active else "STD"
            self.display.draw_text(dst_label, 270, 175, C_GREY, self.color_bg)

            self.last_draw_min = m
            self.last_draw_sec = s

        # Blinking colon — update every second
        elif s != self.last_draw_sec:
            start_x = 20
            y       = 55
            col = C_WHITE if (s % 2 == 0) else self.color_bg
            self.display.fill_rect(start_x + 120, y + 28, 8, 8, col)
            self.display.fill_rect(start_x + 120, y + 58, 8, 8, col)
            self.last_draw_sec = s

    # -----------------------------------------------------------------------
    # Main update loop
    # -----------------------------------------------------------------------
    def update(self):
        current_time = time.time()

        # Auto-timeout back to CLOCK from CONTROL
        if self.mode == self.MODE_CONTROL:
            if current_time - self.last_interaction > self.TIMEOUT:
                self.switch_mode(self.MODE_CLOCK)
                return

        if self.mode == self.MODE_CONTROL:
            self.draw_clock_small()
        elif self.mode == self.MODE_CLOCK:
            self.draw_clock_large()
        # SETTINGS screen is fully static; no update needed

    # -----------------------------------------------------------------------
    # WLED communication
    # -----------------------------------------------------------------------
    def send_wled(self, data):
        try:
            addr = socket.getaddrinfo(self.ip, self.port)[0][-1]
            s = socket.socket()
            s.settimeout(0.5)
            s.connect(addr)
            json_str = json.dumps(data)
            req = (
                "POST /json/state HTTP/1.1\r\n"
                "Host: {}\r\n"
                "Content-Type: application/json\r\n"
                "Content-Length: {}\r\n"
                "Connection: close\r\n\r\n{}"
            ).format(self.ip, len(json_str), json_str)
            s.send(req.encode())
            s.close()
        except Exception as e:
            print("WLED Err:", e)

    # -----------------------------------------------------------------------
    # Touch handling
    # -----------------------------------------------------------------------
    def handle_touch(self, x, y):
        self.last_interaction = time.time()

        # ---- CLOCK mode — any tap wakes to CONTROL ----
        if self.mode == self.MODE_CLOCK:
            self.switch_mode(self.MODE_CONTROL)
            return

        # ---- CONTROL mode ----
        if self.mode == self.MODE_CONTROL:
            # ⚙ Colors button (bottom-right)
            if 270 <= x <= 315 and 195 <= y <= 230:
                self.switch_mode(self.MODE_SETTINGS)
                return

            # WLED colour/on-off buttons
            for label, bx, by, bw, bh, _, data in self.wled_buttons:
                if bx <= x <= bx + bw and by <= y <= by + bh:
                    print("WLED Button:", label)
                    self.send_wled(data)
                    return

            # WLED brightness slider
            sl_y  = self.wled_slider_y
            sl_h  = self.wled_slider_h
            sl_x0 = self.wled_slider_min_x
            sl_x1 = self.wled_slider_max_x
            if sl_x0 <= x <= sl_x1 and (sl_y - 10) <= y <= (sl_y + sl_h + 10):
                pct = (x - sl_x0) / (sl_x1 - sl_x0)
                val = max(0, min(255, int(pct * 255)))
                self._draw_wled_slider_knob(val)
                self.send_wled({"bri": val})
            return

        # ---- SETTINGS mode ----
        if self.mode == self.MODE_SETTINGS:
            # < BACK button → CONTROL (no auto-save)
            if 3 <= x <= 81 and 202 <= y <= 234:
                self.switch_mode(self.MODE_CONTROL)
                return

            # HOME button → CLOCK directly (no auto-save)
            if 89 <= x <= 167 and 202 <= y <= 234:
                self.switch_mode(self.MODE_CLOCK)
                return

            # SAVE button — write to config.json, flash button green briefly
            if 175 <= x <= 253 and 202 <= y <= 234:
                self._save_config()
                self._draw_save_btn(saved=True)   # flash green
                return

            # Colour swatch rows
            for label, attr, row_y in self._settings_rows:
                if self._sw_x <= x <= self._sw_x + self._sw_w and row_y <= y <= row_y + self._sw_h:
                    current = getattr(self, attr)
                    setattr(self, attr, _next_palette_color(current))
                    self._draw_swatch_row(label, attr, row_y)
                    if attr == "color_bg":
                        self.last_draw_min = -1
                    return

            # Vertical brightness bar (right side)
            bx0 = self._bl_bar_x - 8   # generous touch target
            bx1 = self._bl_bar_x + self._bl_bar_w + 4
            by0 = self._bl_bar_y
            by1 = self._bl_bar_y + self._bl_bar_h
            if bx0 <= x <= bx1 and by0 <= y <= by1:
                # y=by0 → max brightness; y=by1 → min brightness
                pct = (by1 - y) / self._bl_bar_h
                val = max(10, min(255, int(pct * 255)))
                self._draw_bl_bar_fill(val)
