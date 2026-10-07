"""
Hardware Pulse & PPG Waveform Simulator.
Synthesizes realistic human pulse telemetry (BPM, IBI, and optical PPG waveform)
for testing the laptop application without physical hardware.
"""

import math
import random
import time
import threading
from typing import Callable, Dict, Any, Optional


class PulseSimulator:
    """Generates synthetic pulse sensor readings and PPG waveforms."""

    MODES = {
        "SLEEPING": {"base_bpm": 45.0, "noise": 2.0, "arrhythmia_chance": 0.0},
        "RESTING": {"base_bpm": 58.0, "noise": 2.0, "arrhythmia_chance": 0.0},
        "NORMAL": {"base_bpm": 75.0, "noise": 3.0, "arrhythmia_chance": 0.0},
        "LIGHT_ACTIVITY": {"base_bpm": 98.0, "noise": 4.0, "arrhythmia_chance": 0.0},
        "FAT_BURN": {"base_bpm": 122.0, "noise": 5.0, "arrhythmia_chance": 0.0},
        "CARDIO": {"base_bpm": 145.0, "noise": 6.0, "arrhythmia_chance": 0.0},
        "EXTREME": {"base_bpm": 172.0, "noise": 8.0, "arrhythmia_chance": 0.0},
        "ARRHYTHMIA": {"base_bpm": 80.0, "noise": 15.0, "arrhythmia_chance": 0.25}
    }

    def __init__(self):
        self.mode = "RESTING"
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        self.callback: Optional[Callable[[Dict[str, Any]], None]] = None
        self._sample_index = 0

    def set_mode(self, mode_name: str):
        if mode_name in self.MODES:
            self.mode = mode_name

    def start(self, callback: Callable[[Dict[str, Any]], None]):
        self.callback = callback
        self.is_running = True
        self.thread = threading.Thread(target=self._generate_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.is_running = False

    def _generate_loop(self):
        """Generates pulse updates at 10Hz sample rate for smooth waveform visualization."""
        phase = 0.0
        while self.is_running:
            params = self.MODES.get(self.mode, self.MODES["RESTING"])
            base_bpm = params["base_bpm"]
            noise = params["noise"]

            # Occasional rhythm variation / arrhythmia spike
            if random.random() < params["arrhythmia_chance"]:
                current_bpm = base_bpm + random.choice([-25.0, 35.0])
            else:
                current_bpm = base_bpm + random.uniform(-noise, noise)

            current_bpm = max(35.0, min(current_bpm, 210.0))
            ibi_ms = round(60000.0 / current_bpm, 1)

            # Generate realistic PPG pulse wave shape (Systolic peak + Dicrotic notch)
            frequency = current_bpm / 60.0  # Hz
            phase += 0.1 * frequency * 2 * math.pi
            if phase > 2 * math.pi:
                phase -= 2 * math.pi

            # Dual Gaussian approximation for PPG pulse wave
            systolic = math.exp(-((phase - 1.5) ** 2) / 0.2)
            dicrotic = 0.3 * math.exp(-((phase - 2.8) ** 2) / 0.15)
            baseline = 512 + int(random.uniform(-5, 5))
            raw_ppg = int(baseline + 300 * (systolic + dicrotic))

            payload = {
                "bpm": round(current_bpm, 1),
                "ibi_ms": ibi_ms,
                "raw": raw_ppg,
                "mode": self.mode,
                "status": "SIMULATED"
            }

            if self.callback:
                self.callback(payload)

            time.sleep(0.08)  # ~12.5 updates per second
