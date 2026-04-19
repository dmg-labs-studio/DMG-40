import json
import network
import requests
import ntptime
import machine
import time
from machine import Pin, SPI, RTC
from time import sleep
import max7219

# --- Load Configuration ---
def load_config():
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except:
        return {}

config = load_config()

# --- Hardware Setup ---
spi = SPI(0, sck=Pin(2), mosi=Pin(3))
cs = Pin(5, Pin.OUT)
display = max7219.Matrix8x8(spi, cs, 4)
rtc = RTC()
display.brightness(config['settings'].get('brightness', 1))
request_timeout = 20
# --- Global Config Variables ---
SSID = config['wifi']['ssid']
PASSWORD = config['wifi']['password']
VAG_NET = config['settings']['vag_network']
HID = config['settings']['hid']

def draw_pacman_pixel(x, direction="LEFT", mouth_open=True):
    bitmap_open = [0x38, 0x7C, 0xF8, 0xF0, 0xF0, 0xF8, 0x7C, 0x38]
    bitmap_closed = [0x38, 0x7C, 0xFE, 0xFE, 0xFE, 0xFE, 0x7C, 0x38]
    current_map = bitmap_closed if not mouth_open else bitmap_open
    for y, row in enumerate(current_map):
        for bit in range(8):
            pixel_val = (row >> (7 - bit)) & 1 if direction == "RIGHT" else (row >> bit) & 1
            if pixel_val: display.pixel(x + bit, y, 1)

def welcome_animation():
    for x in range(32, -12, -1):
        display.fill(0)
        if x > 4: display.fill_rect(x-6, 3, 2, 2, 1) 
        draw_pacman_pixel(x, "LEFT", mouth_open=(x % 4 != 0))
        display.show(); sleep(0.06)
    for x in range(-12, 13, 1):
        display.fill(0)
        draw_pacman_pixel(x, "RIGHT", mouth_open=(x % 4 != 0))
        display.show(); sleep(0.09)
    display.fill(0)
    display.write_text("DM", 6, 1, min_x=0)
    draw_pacman_pixel(18, "RIGHT", mouth_open=True)
    display.show()

def init_wifi(ssid, password):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(ssid, password)
        timeout = 15
        while timeout > 0 and not wlan.isconnected():
            timeout -= 1
            time.sleep(1)
    
    if wlan.isconnected():
        try:
            ntptime.settime()
            l = time.localtime(time.time() + 7200)
            rtc.datetime((l[0], l[1], l[2], l[6], l[3], l[4], l[5], 0))
        except: pass
        return True
    return False

def query_VAG_API(stop_id, line):
    url = f'https://start.vag.de/dm/api/abfahrten.json/{VAG_NET}/{stop_id}/{line}'
    response = None
    try:
        # CRITICAL: Strict timeout ensures the script never waits more than specified
        response = requests.get(url, timeout=request_timeout) 
        data = response.json()
        deps = data.get('Abfahrten', [])
        return [d["Richtungstext"] for d in deps], [d["AbfahrtszeitIst"] for d in deps]
    except Exception as e:
        print(f"Connection error for {line}: {e}")
        return [], []
    finally:
        # CRITICAL: Always close the connection to free up memory
        if response:
            response.close()

def get_mins(t_str):
    try:
        target = time.mktime((int(t_str[0:4]), int(t_str[5:7]), int(t_str[8:10]), int(t_str[11:13]), int(t_str[14:16]), int(t_str[17:19]), 0, 0))
        return int((target - time.time()) / 60)
    except: return 0

# --- Initial Execution ---
welcome_animation()
wifi_status = init_wifi(SSID, PASSWORD)

while True:
    # 1. Regional Lines
    for line_cfg in config['lines']:
        dirs, tms = query_VAG_API(line_cfg['id'], line_cfg['code'])
        
        # We only show the first departure to keep the loop moving
        if tms:
            mins = get_mins(tms[0])
            display.scroll_text_split_rect(line_cfg['num'], dirs[0], delay_ms=45, scroll_start=line_cfg['scroll'])
            
            display.fill(0)
            box_w = 12 if line_cfg['num'] > 9 else 8
            display.vline(0, 0, 8, 1); display.hline(1, 0, box_w-2, 1)
            display.vline(box_w-2, 0, 8, 1); display.hline(1, 7, box_w-2, 1)
            for j, char in enumerate(str(line_cfg['num'])): display.draw_digit(int(char), j*5+1, 1)

            txt = "NOW" if mins <= 0 else str(mins)
            lx = display.write_text(txt, line_cfg['scroll'], 1)
            if mins > 0: display.write_text("M", lx + 1, 1)
            display.show()
            sleep(4)

    # 2. Clock Phase
    for _ in range(config['settings'].get('clock_duration_seconds', 30)):
        t = rtc.datetime()
        display.draw_clock(t[4], t[5], show_colon=(t[6] % 2 == 0))
        display.show()
        sleep(1.0)
    
    # 3. Metro Phase
    m_dirs, m_tms = query_VAG_API(HID, "U1")
    if m_tms:
        mins = get_mins(m_tms[0])
        display.scroll_text_split(m_dirs[0], delay_ms=45)
        display.fill(0); display.draw_8x8_circle(0); display.draw_one(2, 1)
        txt = "NOW" if mins <= 0 else str(mins); lx = display.write_text(txt, 9, 1)
        if mins > 0: display.write_text("MIN", lx, 1, 1, -1)
        display.show(); sleep(4)
