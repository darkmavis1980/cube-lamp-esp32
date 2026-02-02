"""
ESP32-C3 NeoPixel with Button Controls and OLED Display (MicroPython)

Hardware Setup (ESP32-C3 SuperMini):
- ESP32-C3 GPIO5 → 470Ω resistor → NeoPixel DIN
- USB-C 5V → [Diode] → ESP32 5V/VIN
- USB-C 5V → NeoPixel 5V (with 470µF capacitor)
- Common GND between all components
- Button 1 (Mode) → GPIO10 (with pullup)
- Button 2 (Color) → GPIO20 (with pullup)
- OLED VCC → ESP32 3.3V
- OLED GND → Common GND
- OLED SCL → GPIO9 (hardware I2C SCL)
- OLED SDA → GPIO8 (hardware I2C SDA)

Button Functions:
- Button 1: Cycle through different effects (rainbow, chase, pulse, etc.)
- Button 2: Change color for single-color effects

OLED Display shows:
- Current effect name
- Current color name
- LED status
"""

from machine import Pin, I2C
from neopixel import NeoPixel
import time
import math
import random

# Try to import SSD1306 driver (needs to be uploaded to ESP32)
try:
    from ssd1306 import SSD1306_I2C
    OLED_AVAILABLE = True
except ImportError:
    print("WARNING: ssd1306.py not found. Display will be disabled.")
    print("Download from: https://github.com/micropython/micropython/blob/master/drivers/display/ssd1306.py")
    OLED_AVAILABLE = False

# Pin definitions
LED_PIN = 5         # GPIO pin connected to NeoPixels (through 470Ω resistor)
LED_COUNT = 66      # Number of NeoPixels
BUTTON1_PIN = 10    # Mode selection button
BUTTON2_PIN = 20    # Color selection button
I2C_SCL = 9         # I2C Clock (hardware SCL on ESP32-C3 SuperMini)
I2C_SDA = 8         # I2C Data (hardware SDA on ESP32-C3 SuperMini)

# Create NeoPixel object
np = NeoPixel(Pin(LED_PIN), LED_COUNT)

# Create button objects with internal pullup resistors
button1 = Pin(BUTTON1_PIN, Pin.IN, Pin.PULL_UP)
button2 = Pin(BUTTON2_PIN, Pin.IN, Pin.PULL_UP)

# Initialize I2C and OLED
oled = None
if OLED_AVAILABLE:
    try:
        i2c = I2C(0, scl=Pin(I2C_SCL), sda=Pin(I2C_SDA), freq=400000)
        # Try common I2C addresses
        devices = i2c.scan()
        if devices:
            print(f"I2C devices found: {[hex(d) for d in devices]}")
            # Most SSD1306 0.91" displays use 128x32 resolution
            oled = SSD1306_I2C(128, 32, i2c)
            oled.fill(0)
            oled.text("NeoPixel", 30, 0)
            oled.text("Controller", 25, 12)
            oled.text("Starting...", 20, 24)
            oled.show()
            print("OLED initialized successfully!")
        else:
            print("No I2C devices found")
            OLED_AVAILABLE = False
    except Exception as e:
        print(f"OLED initialization failed: {e}")
        OLED_AVAILABLE = False
        oled = None

# Global variables for button debouncing
button1_last_state = True
button2_last_state = True
last_button1_time = 0
last_button2_time = 0
debounce_delay = 200  # milliseconds

# OLED display timeout
DISPLAY_TIMEOUT = 30000  # milliseconds (30 seconds)
last_activity_time = 0
display_sleeping = False

# Effect and color state
current_effect = 0
current_color_index = 0

# Predefined colors (R, G, B)
colors = [
    (255, 0, 0),      # Red
    (0, 255, 0),      # Green
    (0, 0, 255),      # Blue
    (255, 255, 0),    # Yellow
    (255, 0, 255),    # Magenta
    (0, 255, 255),    # Cyan
    (255, 128, 0),    # Orange
    (128, 0, 255),    # Purple
    (255, 255, 255),  # White
]

color_names = ["Red", "Green", "Blue", "Yellow", "Magenta", "Cyan", "Orange", "Purple", "White"]

# Effect names
effect_names = [
    "All On",
    "Rainbow",
    "Color Wipe",
    "Chase",
    "Pulse",
    "Runner",
    "Aurora",
    "Fire",
    "Breathing",
    "Off"
]

def display_sleep():
    """Turn off the OLED display to save its lifespan"""
    global display_sleeping
    if oled is None or display_sleeping:
        return
    try:
        oled.fill(0)
        oled.show()
        oled.poweroff()
        display_sleeping = True
    except Exception as e:
        print(f"Display sleep error: {e}")

def display_wake():
    """Wake the OLED display and refresh content"""
    global display_sleeping, last_activity_time
    if oled is None:
        return
    if display_sleeping:
        try:
            oled.poweron()
        except Exception as e:
            print(f"Display wake error: {e}")
    display_sleeping = False
    last_activity_time = time.ticks_ms()
    update_display()

def update_display():
    """Update OLED display with current status"""
    if oled is None or display_sleeping:
        return

    try:
        oled.fill(0)
        # Line 1: Effect name (truncate if needed)
        effect_text = effect_names[current_effect]
        if len(effect_text) > 16:
            effect_text = effect_text[:13] + "..."
        oled.text(f"Mode: {effect_text}", 0, 0)
        
        # Line 2: Color name
        no_color_effects = {1, 6, 7, 9}  # Rainbow, Aurora, Fire, Off
        if current_effect not in no_color_effects:
            color_text = color_names[current_color_index]
            oled.text(f"Color: {color_text}", 0, 12)
        elif current_effect == 1:
            oled.text("Color: Rainbow", 0, 12)
        elif current_effect == 6:
            oled.text("Color: Aurora", 0, 12)
        elif current_effect == 7:
            oled.text("Color: Fire", 0, 12)

        # Line 3: Status
        if current_effect == 9:
            oled.text("Status: OFF", 0, 24)
        else:
            oled.text(f"LEDs: {LED_COUNT}", 0, 24)
        
        oled.show()
    except Exception as e:
        print(f"Display update error: {e}")

def clear():
    """Turn off all LEDs"""
    for i in range(LED_COUNT):
        np[i] = (0, 0, 0)
    np.write()

def set_color(index, r, g, b, brightness=0.3):
    """Set a single LED to a color with brightness control (0.0 to 1.0)"""
    r = int(r * brightness)
    g = int(g * brightness)
    b = int(b * brightness)
    np[index] = (r, g, b)
    np.write()

def set_all(r, g, b, brightness=0.3):
    """Set all LEDs to the same color"""
    r = int(r * brightness)
    g = int(g * brightness)
    b = int(b * brightness)
    for i in range(LED_COUNT):
        np[i] = (r, g, b)
    np.write()

def wheel(pos):
    """Generate rainbow colors across 0-255 positions"""
    if pos < 85:
        return (pos * 3, 255 - pos * 3, 0)
    elif pos < 170:
        pos -= 85
        return (255 - pos * 3, 0, pos * 3)
    else:
        pos -= 170
        return (0, pos * 3, 255 - pos * 3)

def check_buttons():
    """Check button states and handle mode/color changes"""
    global current_effect, current_color_index
    global button1_last_state, button2_last_state
    global last_button1_time, last_button2_time
    global last_activity_time

    current_time = time.ticks_ms()
    button_pressed = False

    # Check Button 1 (Mode)
    button1_state = button1.value()
    if button1_state == False and button1_last_state == True:
        if time.ticks_diff(current_time, last_button1_time) > debounce_delay:
            if display_sleeping:
                display_wake()
            else:
                current_effect = (current_effect + 1) % len(effect_names)
                print(f"Effect changed to: {effect_names[current_effect]}")
                clear()
                update_display()
            last_activity_time = current_time
            last_button1_time = current_time
            button_pressed = True
    button1_last_state = button1_state

    # Check Button 2 (Color)
    button2_state = button2.value()
    if button2_state == False and button2_last_state == True:
        if time.ticks_diff(current_time, last_button2_time) > debounce_delay:
            if display_sleeping:
                display_wake()
            else:
                current_color_index = (current_color_index + 1) % len(colors)
                print(f"Color changed to: {color_names[current_color_index]}")
                update_display()
            last_activity_time = current_time
            last_button2_time = current_time
            button_pressed = True
    button2_last_state = button2_state

    # Check display timeout
    if not display_sleeping and oled is not None:
        if time.ticks_diff(current_time, last_activity_time) > DISPLAY_TIMEOUT:
            display_sleep()

    return button_pressed

# Effect functions
def effect_all_on():
    """Turn all LEDs on with current color"""
    r, g, b = colors[current_color_index]
    set_all(r, g, b)
    time.sleep(0.05)  # Small delay to allow button checking

def effect_rainbow_cycle():
    """Cycle through rainbow colors"""
    for j in range(255):
        if check_buttons():
            return
        for i in range(LED_COUNT):
            pixel_index = (i * 256 // LED_COUNT) + j
            r, g, b = wheel(pixel_index & 255)
            set_color(i, r, g, b, brightness=0.3)
        time.sleep(0.01)

def effect_color_wipe():
    """Light up LEDs one by one"""
    r, g, b = colors[current_color_index]
    for i in range(LED_COUNT):
        if check_buttons():
            return
        set_color(i, r, g, b)
        time.sleep(0.05)
    time.sleep(0.5)
    for i in range(LED_COUNT):
        if check_buttons():
            return
        set_color(i, 0, 0, 0)
        time.sleep(0.05)

def effect_theater_chase():
    """Movie theater light style chaser animation"""
    r, g, b = colors[current_color_index]
    for j in range(10):
        if check_buttons():
            return
        for q in range(3):
            for i in range(0, LED_COUNT, 3):
                if i + q < LED_COUNT:
                    set_color(i + q, r, g, b)
            time.sleep(0.05)
            clear()
            time.sleep(0.05)

def effect_pulse():
    """Pulse all LEDs from dim to bright"""
    r, g, b = colors[current_color_index]
    steps = 50
    for brightness in range(steps):
        if check_buttons():
            return
        bright = brightness / steps
        set_all(r, g, b, brightness=bright * 0.5)
        time.sleep(0.02)
    
    for brightness in range(steps, 0, -1):
        if check_buttons():
            return
        bright = brightness / steps
        set_all(r, g, b, brightness=bright * 0.5)
        time.sleep(0.02)

def effect_running_light():
    """Single LED running back and forth"""
    r, g, b = colors[current_color_index]
    # Forward
    for i in range(LED_COUNT):
        if check_buttons():
            return
        clear()
        set_color(i, r, g, b)
        time.sleep(0.05)
    # Backward
    for i in range(LED_COUNT - 1, -1, -1):
        if check_buttons():
            return
        clear()
        set_color(i, r, g, b)
        time.sleep(0.05)

def effect_aurora():
    """Aurora effect — smoothly blend through green, cyan, blue, and purple across the strip"""
    # Aurora palette: greens, teals, blues, purples
    aurora_colors = [
        (0, 255, 80),     # Green
        (0, 255, 180),    # Teal
        (0, 200, 255),    # Cyan
        (0, 100, 255),    # Sky blue
        (80, 0, 255),     # Blue-purple
        (150, 0, 200),    # Purple
        (0, 180, 130),    # Sea green
    ]
    palette_len = len(aurora_colors)
    offset = 0
    while True:
        if check_buttons():
            return
        for i in range(LED_COUNT):
            # Map each LED to a position in the palette with smooth blending
            pos = ((i * palette_len * 256) // LED_COUNT + offset) % (palette_len * 256)
            idx = pos // 256
            frac = pos % 256
            c1 = aurora_colors[idx]
            c2 = aurora_colors[(idx + 1) % palette_len]
            r = (c1[0] * (256 - frac) + c2[0] * frac) >> 8
            g = (c1[1] * (256 - frac) + c2[1] * frac) >> 8
            b = (c1[2] * (256 - frac) + c2[2] * frac) >> 8
            np[i] = (int(r * 0.3), int(g * 0.3), int(b * 0.3))
        np.write()
        offset = (offset + 3) % (palette_len * 256)
        time.sleep(0.03)

def effect_fire():
    """Fire effect — warm flickering flame simulation"""
    # Per-LED heat values
    heat = [0] * LED_COUNT
    cooling = 10
    sparking = 120
    while True:
        if check_buttons():
            return
        # Cool down each cell
        for i in range(LED_COUNT):
            heat[i] = max(0, heat[i] - random.randint(0, ((cooling * 10) // LED_COUNT) + 2))
        # Heat drifts up
        for i in range(LED_COUNT - 1, 1, -1):
            heat[i] = (heat[i - 1] + heat[i - 2] + heat[i - 2]) // 3
        # Random sparks near bottom
        if random.randint(0, 255) < sparking:
            y = random.randint(0, min(7, LED_COUNT - 1))
            heat[y] = min(255, heat[y] + random.randint(160, 255))
        # Map heat to color
        for i in range(LED_COUNT):
            t = heat[i]
            if t > 170:
                # Hot: yellow-white
                r, g, b = 255, 255, min(255, (t - 170) * 3)
            elif t > 85:
                # Mid: orange-yellow
                r, g, b = 255, min(255, (t - 85) * 3), 0
            else:
                # Cool: red-dark
                r, g, b = min(255, t * 3), 0, 0
            np[i] = (int(r * 0.3), int(g * 0.3), int(b * 0.3))
        np.write()
        time.sleep(0.02)

def effect_breathing():
    """Breathing effect — smooth sine-wave fade using the current color"""
    r, g, b = colors[current_color_index]
    step = 0
    while True:
        if check_buttons():
            return
        # Sine wave from 0.0 to 1.0
        bright = (math.sin(step) + 1.0) / 2.0
        set_all(r, g, b, brightness=bright * 0.3)
        step += 0.04
        if step > 2 * math.pi:
            step -= 2 * math.pi
        time.sleep(0.02)

def effect_off():
    """Turn all LEDs off"""
    clear()
    time.sleep(0.1)

# Main program
print("ESP32-C3 NeoPixel with Button Control and OLED Starting...")
print(f"Testing {LED_COUNT} LEDs on GPIO{LED_PIN}")
print(f"Button 1 (Mode): GPIO{BUTTON1_PIN}")
print(f"Button 2 (Color): GPIO{BUTTON2_PIN}")
print(f"OLED Display: {'Enabled' if oled else 'Disabled'}")
print("\nButton 1: Cycle through effects")
print("Button 2: Change color")
print(f"\nStarting with: {effect_names[current_effect]}, Color: {color_names[current_color_index]}")

# Initialize - turn off all LEDs
clear()
time.sleep(2)  # Show startup message on OLED
update_display()
last_activity_time = time.ticks_ms()
time.sleep(1)

# Main loop
while True:
    check_buttons()
    
    # Run current effect
    if current_effect == 0:  # All On
        effect_all_on()
    elif current_effect == 1:  # Rainbow Cycle
        effect_rainbow_cycle()
    elif current_effect == 2:  # Color Wipe
        effect_color_wipe()
    elif current_effect == 3:  # Theater Chase
        effect_theater_chase()
    elif current_effect == 4:  # Pulse
        effect_pulse()
    elif current_effect == 5:  # Running Light
        effect_running_light()
    elif current_effect == 6:  # Aurora
        effect_aurora()
    elif current_effect == 7:  # Fire
        effect_fire()
    elif current_effect == 8:  # Breathing
        effect_breathing()
    elif current_effect == 9:  # Off
        effect_off()
    
    time.sleep(0.01)  # Small delay between effect loops