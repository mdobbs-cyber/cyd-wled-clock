# ESP32 "Cheap Yellow Display" WLED Clock

A MicroPython-based persistent clock and WLED controller for the ESP32-2432S028 (known as the "Cheap Yellow Display" or CYD).

## Features

- **Clock Mode**: Full-screen large vector-font digital clock with date, blinking colon, and a DST/STD indicator.
- **Auto DST**: Automatically applies US Daylight Saving Time (2nd Sunday in March → 1st Sunday in November) — no API or zip code needed.
- **Dashboard Mode**: Tap the screen to reveal WLED controls:
  - Small clock header with date
  - **WLED Power**: On / Off buttons
  - **WLED Color Presets**: White, Red, Green, Blue, Pink
  - **WLED Brightness Slider**: Drag to adjust strip brightness
- **Clock Settings Screen**: Tap **[CLR SET]** on the Dashboard to customize:
  - **Background color** — fill behind all clock elements
  - **Digit color** — hour and minute strokes
  - **AM/PM label color**
  - **Date label color**
  - **Display Brightness** — vertical bar slider controls backlight PWM in real time
  - **[SAVE]** button writes settings to `config.json` (persists on reboot)
- **Vector Fonts**: Custom vector-based font rendering for a smooth, scalable look.
- **WiFi & NTP**: Automatically syncs time from the internet on boot.

## Hardware Required

- **ESP32-2432S028** ("Cheap Yellow Display" / CYD) — available on AliExpress / Amazon
- **WLED Device**: Any WLED-compatible LED strip on the same WiFi network

## Files

| File | Purpose |
|------|---------|
| `main.py` | Entry point — sets up SPI, PWM backlight, display, touch, and main loop |
| `boot.py` | Connects to WiFi on startup |
| `app_dashboard.py` | All screen modes, touch handling, WLED communication |
| `dst.py` | US DST auto-detection (pure date math, no network) |
| `vector_font.py` | Scalable vector digit renderer |
| `ili9341.py` | ILI9341 display driver |
| `xpt2046.py` | XPT2046 touch driver (calibrated for Landscape) |
| `config.json` | WiFi, WLED, timezone, and colour settings |

## Installation

1. **Flash MicroPython**: Install standard ESP32 MicroPython firmware on your CYD.
2. **Upload all files** to the root `/` of the device (via Thonny or `mpremote`):
   - `main.py`, `boot.py`, `app_dashboard.py`, `dst.py`
   - `vector_font.py`, `ili9341.py`, `xpt2046.py`
   - `config.json`
3. **Edit `config.json`** with your network and timezone settings (see below).
4. **Reset** the device — it will connect to WiFi, sync NTP, and start the clock.

## Configuration

Edit `config.json` on the device:

```json
{
    "wifi_ssid": "YOUR_WIFI_NAME",
    "wifi_password": "YOUR_WIFI_PASSWORD",
    "wled_ip": "192.168.1.xxx",
    "timezone_offset": -5,
    "dst_enabled": true,
    "color_bg": 0,
    "color_digit": 1824,
    "color_ampm": 65504,
    "color_date": 33808,
    "display_brightness": 200
}
```

| Key | Description |
|-----|-------------|
| `wifi_ssid` | Your WiFi network name |
| `wifi_password` | Your WiFi password |
| `wled_ip` | IP address of your WLED device |
| `timezone_offset` | UTC offset in hours for **standard time** (e.g. `-5` = EST, `-6` = CST, `-7` = MST, `-8` = PST) |
| `dst_enabled` | `true` to auto-apply US DST; set `false` for Arizona, Hawaii, etc. |
| `color_bg` | Background color (RGB565 integer) |
| `color_digit` | Clock digit color (RGB565 integer) |
| `color_ampm` | AM/PM label color (RGB565 integer) |
| `color_date` | Date label color (RGB565 integer) |
| `display_brightness` | Backlight brightness 0–255 (default `200`) |

> **Note:** Color and brightness settings are managed through the on-screen Settings UI and saved automatically when you tap **[SAVE]**. You do not need to edit them manually.

## Screen Flow

```
CLOCK (large digits, blinking colon)
   │ any tap
   ▼
DASHBOARD (small clock + WLED controls)
   │ tap [CLR SET]                        │ 30 s timeout
   ▼                                       ▼
SETTINGS (colour pickers + BL bar)      CLOCK
   │ [< BACK]   [* HOME]   [SAVE]
   │     │          │
   ▼     │          └──────────────► CLOCK
DASHBOARD                             (no save)
```

## Settings Screen Controls

| Control | Location | Action |
|---------|----------|--------|
| Colour swatch | Tap row swatch | Cycles through 10 colour presets |
| Brightness bar | Far-right vertical bar | Tap high = bright · Tap low = dim |
| **[< BACK]** | Bottom-left | Return to Dashboard (unsaved) |
| **[* HOME]** | Bottom-centre | Return to Clock face (unsaved) |
| **[SAVE]** | Bottom-right | Write all settings to `config.json` |

### Colour Presets (tap swatch to cycle)

Green → White → Cyan → Yellow → Orange → Red → Pink → Blue → Purple → Black

## Pinout (CYD Standard)

**Display (ILI9341)**
| Pin | GPIO |
|-----|------|
| SCK | 14 |
| MOSI | 13 |
| MISO | 12 |
| CS | 15 |
| DC | 2 |
| BL (PWM) | 21 |

**Touch (XPT2046)**
| Pin | GPIO |
|-----|------|
| CLK | 25 |
| CS | 33 |
| DIN | 32 |
| DO | 39 |

> **Backlight note:** GPIO 21 is driven by a 1 kHz PWM signal. Brightness is set from `config.json` on boot and can be adjusted live in the Settings screen.

## Usage

1. **Boot** — device connects to WiFi and syncs NTP time.
2. **Clock Mode** — displays large clock. DST or STD shown bottom-right.
3. **Tap anywhere** → Dashboard with WLED controls appears.
4. **Tap [CLR SET]** → Settings screen to change colours and brightness.
5. **Tap [SAVE]** → saves settings; tap **[< BACK]** or **[* HOME]** to navigate without saving.
6. **30-second timeout** — Dashboard auto-returns to Clock mode if idle.
