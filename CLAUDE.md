# NeoPixel Controller — ESP32-C3 SuperMini

MicroPython project for controlling 24 WS2812B NeoPixels with an OLED display and two buttons, running on an ESP32-C3 SuperMini.

---

## Project Overview

A standalone NeoPixel controller with:
- 24 WS2812B NeoPixel LEDs
- 0.91" SSD1306 OLED display (I2C, 128x32)
- 2 momentary push buttons (mode + color)
- USB-C breakout board for shared power delivery
- ESP32-C3 SuperMini as the microcontroller

---

## Hardware & Pinout (ESP32-C3 SuperMini)

Pin assignments are based on the ESP32-C3 SuperMini's actual pinout. GPIO8/GPIO9 are the hardware I2C SDA/SCL pins on this board — do NOT reassign them to anything else.

| GPIO | Role | Notes |
|------|------|-------|
| GPIO5 | NeoPixel DIN | Through 470Ω series resistor |
| GPIO8 | OLED SDA | Hardware I2C — do not change |
| GPIO9 | OLED SCL | Hardware I2C — do not change |
| GPIO10 | Button 1 (Mode) | Internal pullup, active LOW |
| GPIO20 | Button 2 (Color) | Internal pullup, active LOW |
| 5V | Power input | Via diode from USB-C breakout |
| 3.3V | OLED VCC | Do not use 5V for OLED |
| GND | Common ground | Shared by all components |

---

## Power Architecture

The USB-C breakout board is the single power source for the whole circuit. A 1N4007 diode sits between the USB-C breakout 5V rail and the ESP32's 5V/VIN pin. This is intentional and solves a specific problem:

- When the ESP32 is plugged into a computer for programming, its USB port provides 5V to the ESP32. Without the diode, that 5V would backfeed through the shared rail and try to power 24 NeoPixels off the computer's USB port — which can damage the port or the LEDs.
- The diode allows current from the USB-C breakout → ESP32 when running normally, but blocks reverse current from ESP32 USB → NeoPixel rail when programming.
- The 0.7V drop from the 1N4007 is acceptable here because the ESP32 only draws ~250mA. If you want to reduce it, swap for a Schottky diode (1N5817 or SS34) with ~0.3V drop.

The NeoPixel 5V rail connects directly to the USB-C breakout (no diode on this path). A 470µF 16V electrolytic capacitor sits across the NeoPixel power input (close to the strip) to absorb voltage spikes when LEDs switch states.

```
USB-C Breakout 5V ──┬── [1N4007 Diode] ──→ ESP32 5V/VIN
                    │
                    └── [470µF Cap] ──→ NeoPixel 5V

USB-C Breakout GND ─── Common GND (ESP32, NeoPixels, Capacitor, Buttons, OLED)
```

---

## Components & Parts

| Component | Value / Part | Polarity? | Notes |
|-----------|-------------|-----------|-------|
| Diode D1 | 1N4007 (or Schottky 1N5817) | YES — Anode to USB-C, Cathode to ESP32 | Protects against USB backfeeding |
| Capacitor C1 | 470µF 16V electrolytic | YES — + to 5V, - to GND | Place close to NeoPixel input |
| Resistor R1 | 470Ω, 1/4W | No | Series on data line, protects first LED |
| Buttons | Momentary tactile, any | No | Connect GPIO to GND, use internal pullups |
| OLED | 0.91" SSD1306 I2C 128x32 | No | I2C address usually 0x3C |

---

## MicroPython Setup

The `ssd1306.py` driver must be uploaded to the ESP32 alongside `main.py`. Download it from:
https://github.com/micropython/micropython/blob/master/drivers/display/ssd1306.py

The code handles a missing driver gracefully — it will print a warning and run without the display if `ssd1306.py` is not found.

### Files to upload to ESP32

```
main.py          ← rename neopixel_test.py to this, runs automatically on boot
ssd1306.py       ← OLED driver, download from link above
```

---

## Code Structure

Everything lives in a single file (`neopixel_test.py`). Structure:

1. **Imports & pin definitions** — all GPIO assignments at the top, change them here only
2. **OLED initialization** — I2C scan + SSD1306 setup, gracefully disabled if not found
3. **Button debouncing** — 200ms debounce using `time.ticks_ms()` / `time.ticks_diff()`
4. **Color & effect tables** — `colors[]` and `effect_names[]` define the available options
5. **`update_display()`** — renders current mode, color, and status to the OLED (3 lines, 128x32)
6. **`check_buttons()`** — polls both buttons, updates state, calls `update_display()`. Returns `True` if a button was pressed — effect functions use this to interrupt mid-animation
7. **Effect functions** — each effect is a standalone function that loops internally and calls `check_buttons()` frequently so it can be interrupted instantly
8. **Main loop** — calls `check_buttons()` then dispatches to the current effect function

### Adding a new effect

1. Write a new `effect_xxx()` function following the same pattern as the others — loop internally, call `check_buttons()` each iteration, return immediately if it returns `True`
2. Add the name to `effect_names[]`
3. Add an `elif` branch in the main loop dispatching to it

### Adding a new color

Just append an `(R, G, B)` tuple to `colors[]` and the matching name string to `color_names[]`. Everything else updates automatically.

### Adjusting brightness

Global brightness is controlled via the `brightness` parameter in `set_color()` and `set_all()`. Default is `0.2` (20%). The pulse effect ramps up to `0.5` (50%). For full white at high brightness, keep it ≤ 0.3 to stay within your power supply headroom.

---

## Troubleshooting

- **LEDs flicker or show wrong colors:** Check the 470Ω resistor on the data line. If still flickering, you may need a 3.3V → 5V logic level shifter between GPIO5 and NeoPixel DIN.
- **OLED doesn't light up:** Run an I2C scan (the code does this on boot — check serial output). Your display might be at address 0x3D instead of 0x3C. Also confirm VCC is connected to 3.3V, not 5V.
- **Buttons don't respond:** Confirm they're wired GPIO → button → GND. The code uses internal pullups so no external resistor is needed. Check debounce delay if presses are being missed.
- **LEDs stay off when running on external power:** Check the diode orientation. Anode (unmarked) must face the USB-C breakout, cathode (stripe) must face the ESP32. If flipped, no power reaches anything.
- **LEDs turn on when programming via USB:** The diode should prevent this. If it's still happening, the diode is likely installed backwards — flip it.
