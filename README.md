# Cube Lamp — ESP32-C3 NeoPixel Controller

A MicroPython project for controlling WS2812B NeoPixels with an OLED display and button interface, running on an ESP32-C3 SuperMini.

## Features

- **10 LED effects:** All On, Aurora, Color Wipe, Ocean, Candle, Runner, Rainbow, Fire, Breathing, Off
- **9 colors:** Red, Green, Blue, Yellow, Magenta, Cyan, Orange, Purple, White
- **OLED display** showing current effect, color, and LED count
- **Two-button control** — one for cycling effects, one for changing colors
- **Instant interrupts** — button presses interrupt animations immediately

## Hardware

| Component | Spec |
|-----------|------|
| Microcontroller | ESP32-C3 SuperMini |
| LEDs | 66x WS2812B NeoPixels |
| Display | 0.91" SSD1306 OLED (128x32, I2C) |
| Buttons | 2x momentary tactile push buttons |
| Power | USB-C breakout board (shared 5V rail) |

### Pinout

| GPIO | Function |
|------|----------|
| 5 | NeoPixel data (through 470Ω resistor) |
| 8 | OLED SDA (hardware I2C) |
| 9 | OLED SCL (hardware I2C) |
| 10 | Button 1 — Mode (internal pullup, active LOW) |
| 20 | Button 2 — Color (internal pullup, active LOW) |

### Circuit

```
USB-C 5V ──┬── [1N4007 Diode] ──→ ESP32 5V/VIN
            │
            └── [470µF Cap] ──→ NeoPixel 5V

GPIO5 ── [470Ω] ──→ NeoPixel DIN

ESP32 3.3V ──→ OLED VCC

Common GND shared by all components
```

The diode prevents 5V backfeed from the ESP32's USB port into the NeoPixel rail during programming. See `CLAUDE.md` for full power architecture details.

## Setup

### Requirements

- ESP32-C3 SuperMini with MicroPython firmware
- [`ssd1306.py`](https://github.com/micropython/micropython/blob/master/drivers/display/ssd1306.py) display driver

### Upload

Upload both files to the ESP32:

```
main.py       ← runs automatically on boot
ssd1306.py    ← OLED driver
```

The code runs without the OLED driver — it will print a warning and disable display output if `ssd1306.py` is missing.

## Usage

- **Button 1 (GPIO10):** Cycle through effects
- **Button 2 (GPIO20):** Change color (applies to single-color effects)

The OLED display shows the current mode, color, and LED status.

## Adding Effects

1. Write an `effect_xxx()` function that loops internally and calls `check_buttons()` each iteration (return immediately if it returns `True`)
2. Add the name to `effect_names[]`
3. Add an `elif` branch in the main loop

## Adding Colors

Append an `(R, G, B)` tuple to `colors[]` and the matching name to `color_names[]`.

## Parts List

| Part | Value | Notes |
|------|-------|-------|
| Diode | 1N4007 (or 1N5817 Schottky) | Anode → USB-C, Cathode → ESP32 |
| Capacitor | 470µF 16V electrolytic | Place close to NeoPixel 5V input |
| Resistor | 470Ω 1/4W | Series on NeoPixel data line |
| Buttons | Momentary tactile | Wire GPIO → button → GND |

## License

MIT
