# Hardware Setup & Pinout Guide - Pulse Rate Monitor

This guide explains how to connect your pulse sensor module to your microchip (microcontroller) and flash the firmware so it streams data to your laptop over USB Serial.

---

## Hardware Components Required

1. **Microchip / Microcontroller**:
   - Arduino Uno / Nano / Pro Mini
   - ESP32 or ESP8266
   - Raspberry Pi Pico (RP2040)
   - STM32 Blue Pill
2. **Pulse Sensor**:
   - **Optical PPG Pulse Sensor** (e.g. 3-pin analog pulse sensor module with LED + photodiode), OR
   - **MAX30102 / MAX30100** I2C Pulse Oximeter sensor.
3. **USB Cable**: Standard USB cable connecting microchip to laptop.
4. **Jumper Wires & Breadboard**.

---

## Wiring Diagram (Pinout)

### 3-Pin Analog Optical Pulse Sensor -> Arduino / ESP32

| Pulse Sensor Pin | Signal | Arduino Pin | ESP32 Pin | RP2040 Pin |
| :--- | :--- | :--- | :--- | :--- |
| **VCC / +** | 3.3V - 5V Power | 5V or 3.3V | 3.3V | 3.3V |
| **GND / -** | Ground | GND | GND | GND |
| **S / Signal** | Analog Out | A0 | GPIO 34 (ADC1) | GPIO 26 (ADC0) |

---

## Flashing Instructions

### Method A: Arduino IDE (For Arduino / ESP32 / STM32)

1. Open **Arduino IDE** on your laptop.
2. Open `firmware/pulse_monitor.ino`.
3. Select your microchip board under `Tools -> Board`.
4. Connect your microchip to the laptop via USB and select the corresponding COM port (`Tools -> Port`).
5. Click **Upload** (Ctrl + U).
6. Verify output: Open `Tools -> Serial Monitor` and set baud rate to **115200**. You should see JSON packets being printed:
   ```json
   {"bpm":72.5,"ibi":827.6,"raw":534,"status":"OK"}
   ```

### Method B: MicroPython (For ESP32 / Raspberry Pi Pico)

1. Flash MicroPython firmware onto your microcontroller using Thonny IDE or esptool.
2. Upload `firmware/pulse_monitor.py` to the device as `main.py`.
3. Reset the device. It will automatically begin outputting JSON telemetry to the USB serial interface.

---

## Laptop Connection

Once programmed, simply plug the USB cable into your laptop.
In the Pulse Monitor Dashboard on your laptop (`http://localhost:8000`), click **Connect Hardware Serial**, select your COM port, and the laptop will begin receiving live heart rate data instantly!
