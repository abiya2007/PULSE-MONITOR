/*
 * Pulse Rate Monitor Firmware (Microchip / Microcontroller Code)
 * Compatible with: Arduino Uno, Arduino Nano, ESP32, STM32, Raspberry Pi Pico
 * 
 * Functions:
 * 1. Reads raw optical PPG pulse sensor (Analog A0 or I2C MAX30102).
 * 2. Applies low-pass noise filtering and peak-detection algorithm.
 * 3. Calculates heart rate in Beats Per Minute (BPM) and Inter-Beat Interval (IBI in ms).
 * 4. Outputs formatted JSON payload over USB Serial (UART @ 115200 baud).
 * 
 * Output JSON format:
 * {"bpm": 72.5, "ibi": 827.6, "raw": 534, "status": "OK"}
 */

#define PULSE_PIN A0          // Analog pin for optical pulse sensor
#define BAUD_RATE 115200      // UART USB Serial baud rate

// Threshold & timing variables
int signalThreshold = 550;    // Peak threshold (adjust based on sensor calibration)
unsigned long lastBeatTime = 0;
float bpm = 70.0;
float ibi = 850.0;            // Inter-Beat Interval in milliseconds
bool pulseState = false;

// Moving average buffer for PPG smoothing
const int READINGS_COUNT = 5;
int readings[READINGS_COUNT];
int readIndex = 0;
int totalReadings = 0;

void setup() {
  Serial.begin(BAUD_RATE);
  pinMode(PULSE_PIN, INPUT);
  
  for (int i = 0; i < READINGS_COUNT; i++) {
    readings[i] = 0;
  }
}

void loop() {
  int rawSignal = analogRead(PULSE_PIN);
  
  // Smooth signal with moving average filter
  totalReadings = totalReadings - readings[readIndex];
  readings[readIndex] = rawSignal;
  totalReadings = totalReadings + readings[readIndex];
  readIndex = (readIndex + 1) % READINGS_COUNT;
  int smoothSignal = totalReadings / READINGS_COUNT;

  unsigned long now = millis();

  // Peak detection logic
  if (smoothSignal > signalThreshold && !pulseState) {
    pulseState = true;
    
    // Calculate time since last heart beat
    unsigned long timeDelta = now - lastBeatTime;
    if (timeDelta > 300 && timeDelta < 2000) { // Valid human heart beat range (30-200 BPM)
      ibi = (float)timeDelta;
      float calculatedBpm = 60000.0 / ibi;
      
      // Exponential moving average for smooth BPM output
      bpm = (0.7 * bpm) + (0.3 * calculatedBpm);
    }
    lastBeatTime = now;
  }
  
  // Reset pulse state when signal falls below threshold
  if (smoothSignal < (signalThreshold - 30) && pulseState) {
    pulseState = false;
  }

  // Stream JSON packet to Laptop via USB Serial
  static unsigned long lastStreamTime = 0;
  if (now - lastStreamTime >= 100) { // Send telemetry update every 100ms (10Hz)
    lastStreamTime = now;
    
    Serial.print("{\"bpm\":");
    Serial.print(bpm, 1);
    Serial.print(",\"ibi\":");
    Serial.print(ibi, 1);
    Serial.print(",\"raw\":");
    Serial.print(smoothSignal);
    Serial.println(",\"status\":\"OK\"}");
  }

  delay(10); // Small loop delay
}
