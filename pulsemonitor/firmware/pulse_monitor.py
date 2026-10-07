"""
MicroPython Pulse Rate Monitor Firmware.
For ESP32, Raspberry Pi Pico, or STM32 microchips running MicroPython.

Reads analog PPG pulse sensor on ADC pin, computes BPM and IBI,
and streams JSON serial data over USB UART to the laptop.
"""

import machine
import time
import json

# Setup ADC Pin (e.g. Pin 34 on ESP32 or Pin 26 on Raspberry Pi Pico)
adc = machine.ADC(machine.Pin(34))
try:
    adc.atten(machine.ADC.ATTN_11DB) # 0-3.6V range for ESP32
except AttributeError:
    pass

THRESHOLD = 2000  # Adjust for 12-bit ADC (0-4095)
last_beat_time = time.ticks_ms()
bpm = 70.0
ibi = 850.0
pulse_state = False

print("MicroPython Pulse Sensor Firmware Started...")

while True:
    raw_val = adc.read()
    now = time.ticks_ms()

    # Peak detection logic
    if raw_val > THRESHOLD and not pulse_state:
        pulse_state = True
        delta = time.ticks_diff(now, last_beat_time)
        if 300 < delta < 2000:  # Valid beat interval (30 to 200 BPM)
            ibi = float(delta)
            calc_bpm = 60000.0 / ibi
            bpm = (0.7 * bpm) + (0.3 * calc_bpm)
        last_beat_time = now

    if raw_val < (THRESHOLD - 100) and pulse_state:
        pulse_state = False

    # Send JSON packet over USB Serial
    packet = {
        "bpm": round(bpm, 1),
        "ibi": round(ibi, 1),
        "raw": raw_val,
        "status": "OK"
    }
    print(json.dumps(packet))

    time.sleep_ms(100)
