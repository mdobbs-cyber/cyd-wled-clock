import network
import json
import time

def connect_wifi():
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
    except:
        print("No config.json found!")
        return

    ssid = config.get('wifi_ssid')
    password = config.get('wifi_password')
    
    if not ssid:
        print("No WiFi SSID in config!")
        return

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    if not wlan.isconnected():
        print('Connecting to network...')
        wlan.connect(ssid, password)
        t = 0
        while not wlan.isconnected() and t < 20: # 10s timeout
            time.sleep(0.5)
            t += 1
            
    print('Network config:', wlan.ifconfig())

connect_wifi()
