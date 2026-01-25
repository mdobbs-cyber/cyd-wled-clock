# ESP32 "Cheap Yellow Display" WLED Clock

A MicroPython-based persistent clock and WLED controller for the ESP32-2432S028 (known as the "Cheap Yellow Display" or CYD).

## Features

*   **Screensaver Mode**: Large, modern vector-font digital clock with date.
*   **Dashboard Mode**: Tap the screen to reveal:
    *   Small Digital Clock
    *   **WLED Controls**: Power On/Off, Color Presets (White, Red, Green, Blue, Pink).
    *   **Brightness Slider**: Drag to adjust global brightness.
*   **Vector Fonts**: Custom vector-based font rendering for a smooth, scalable look.
*   **WiFi & NTP**: Automatically syncs time from the internet.

## Hardware Required

*   **ESP32-2432S028** ("Cheap Yellow Display" / CYD) - [AliExpress/Amazon]
*   **WLED Device**: Any WLED-compatible light strip accessible on the same WiFi network.

## Installation

1.  **Flash MicroPython**: Install standard ESP32 MicroPython firmware on your CYD.
2.  **Upload Files**: Upload the following files to the root `/` of the device:
    *   `main.py`: Entry point.
    *   `app_dashboard.py`: Main application logic.
    *   `vector_font.py`: Vector font definition.
    *   `ili9341.py`: Display driver (modified for line drawing).
    *   `xpt2046.py`: Touch driver (calibrated for Landscape).
    *   `config.json`: Wifi and WLED settings.
    *   `boot.py`: (Optional) Standard boot script.

## Configuration

Create a `config.json` file in the root with your settings:

```json
{
    "ssid": "YOUR_WIFI_NAME",
    "password": "YOUR_WIFI_PASSWORD",
    "wled_ip": "192.168.1.xxx",
    "timezone_offset": -5
}
```

*   `wled_ip`: The IP address of your WLED device.
*   `timezone_offset`: Your offset from UTC (e.g., -5 for EST, -8 for PST).

## Pinout (CYD Standard)

**Display (ILI9341)**
*   SCK: 14
*   MOSI: 13
*   MISO: 12
*   CS: 15
*   DC: 2
*   BL: 21

**Touch (XPT2046)**
*   CLK: 25
*   CS: 33
*   DIN: 32
*   DO: 39

## Usage

1.  **Boot**: The device connects to WiFi and syncs time.
2.  **Screensaver**: Shows the large clock.
3.  **Interact**: Tap anywhere to show controls.
4.  **Timeout**: After 30 seconds of inactivity, it returns to the screensaver.
