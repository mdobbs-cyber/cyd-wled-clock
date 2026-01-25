from machine import Pin, SPI
import time
import json
import ili9341
import xpt2046
import ili9341
import xpt2046

# Pin Definitions (Common for ESP32-2432S028 / CYD)
# Display SPI (HSPI/SPI1 default-ish)
TFT_SCK = 14
TFT_MOSI = 13
TFT_MISO = 12
TFT_CS = 15
TFT_DC = 2
TFT_RST = -1
TFT_BL = 21

# Touch SPI (User Provided)
TOUCH_CLK = 25
TOUCH_CS = 33
TOUCH_DIN = 32 # MOSI
TOUCH_DO = 39  # MISO

def main():
    # Load Config
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
    except:
        config = {}

    # Setup SPIs
    
    # 1. Display SPI (Fast)
    # Using SPI(1) or SPI(2). Let's use SPI(1) as before.
    # We can go fast now! 40MHz.
    tft_spi = SPI(1, baudrate=40000000, sck=Pin(TFT_SCK), mosi=Pin(TFT_MOSI), miso=Pin(TFT_MISO))

    # 2. Touch SPI (Slower, Separate Bus)
    # Using SPI(2) or SoftSPI. Hard SPI(2) should work with remapping.
    # Note: GPIO 39 is Input Only, which is fine for MISO.
    touch_spi = SPI(2, baudrate=1000000, sck=Pin(TOUCH_CLK), mosi=Pin(TOUCH_DIN), miso=Pin(TOUCH_DO))

    # Setup Display
    display = ili9341.ILI9341(
        tft_spi, 
        cs=Pin(TFT_CS), 
        dc=Pin(TFT_DC), 
        rst=None, 
        bl=Pin(TFT_BL),
        rotation=3 # Landscape (Inverted/Corrected for CYD)
    )
    
    # Setup Touch
    touch = xpt2046.XPT2046(
        touch_spi, 
        cs=Pin(TOUCH_CS),
        width=320,
        height=240,
        x_min=300, x_max=3900, y_min=200, y_max=3800
    )

    # App
    import app_dashboard
    dashboard = app_dashboard.DashboardApp(display, config)

    # Initial Sync
    dashboard.sync_time()
    
    # Start in Clock Mode
    dashboard.switch_mode("CLOCK")

    screen_last_touched = 0

    while True:
        # Update Dashboard (Clock)
        dashboard.update()
        
        # Touch
        t = touch.get_touch()
        if t:
            # print("Touch:", t)
            if time.time() - screen_last_touched > 0.2: # Debounce
                dashboard.handle_touch(t[0], t[1])
                screen_last_touched = time.time()
                
        time.sleep(0.05)

if __name__ == '__main__':
    main()
