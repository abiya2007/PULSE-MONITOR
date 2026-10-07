"""
Serial Port Reader for Microchip USB Connection.
Manages listing active COM/Serial ports, connecting, auto-reconnecting,
and parsing incoming pulse sensor telemetry over serial UART.
"""

import json
import logging
import threading
import time
from typing import Callable, List, Dict, Optional
import serial
import serial.tools.list_ports

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SerialReader")


class SerialPortReader:
    """Manages serial connection to microchip and streams parsed pulse data."""

    def __init__(self, baud_rate: int = 115200):
        self.baud_rate = baud_rate
        self.port: Optional[str] = None
        self.ser: Optional[serial.Serial] = None
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        self.data_callback: Optional[Callable[[Dict[str, Any]], None]] = None
        self.connected_port: Optional[str] = None

    @staticmethod
    def list_ports() -> List[Dict[str, str]]:
        """Returns list of available serial COM ports with hardware details."""
        ports = serial.tools.list_ports.comports()
        result = []
        for p in ports:
            result.append({
                "port": p.device,
                "description": p.description,
                "hwid": p.hwid
            })
        return result

    def start(self, port_name: str, callback: Callable[[Dict[str, Any]], None]):
        """Starts serial background reading thread on specified port."""
        self.port = port_name
        self.data_callback = callback
        self.is_running = True
        self.thread = threading.Thread(target=self._read_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """Stops reading and closes serial port."""
        self.is_running = False
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
            except Exception as e:
                logger.error(f"Error closing serial port: {e}")
        self.connected_port = None
        logger.info("Serial reader stopped.")

    def _read_loop(self):
        logger.info(f"Connecting to serial port {self.port} at {self.baud_rate} baud...")
        while self.is_running:
            try:
                if not self.ser or not self.ser.is_open:
                    self.ser = serial.Serial(self.port, self.baud_rate, timeout=1.0)
                    self.connected_port = self.port
                    logger.info(f"Connected to {self.port}")

                line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                if not line:
                    continue

                parsed = self._parse_telemetry(line)
                if parsed and self.data_callback:
                    self.data_callback(parsed)

            except serial.SerialException as e:
                logger.warning(f"Serial port disconnected or error: {e}. Retrying in 2 seconds...")
                self.connected_port = None
                if self.ser:
                    try:
                        self.ser.close()
                    except Exception:
                        pass
                time.sleep(2.0)
            except Exception as e:
                logger.error(f"Unexpected serial loop error: {e}")
                time.sleep(1.0)

    def _parse_telemetry(self, raw_line: str) -> Optional[Dict[str, Any]]:
        """
        Parses incoming serial packet.
        Supports JSON format: {"bpm": 75, "ibi": 800, "raw": 512}
        or CSV format: 75,800,512
        """
        # Attempt JSON parse
        if raw_line.startswith('{') and raw_line.endswith('}'):
            try:
                data = json.loads(raw_line)
                return {
                    "bpm": float(data.get("bpm", 0)),
                    "ibi_ms": float(data.get("ibi", 60000.0 / max(float(data.get("bpm", 60)), 1))),
                    "raw": int(data.get("raw", 512)),
                    "status": data.get("status", "OK")
                }
            except Exception:
                pass

        # Attempt CSV parse (BPM, IBI, RAW)
        parts = raw_line.split(',')
        if len(parts) >= 1:
            try:
                bpm = float(parts[0].strip())
                ibi = float(parts[1].strip()) if len(parts) > 1 else (60000.0 / max(bpm, 1))
                raw = int(parts[2].strip()) if len(parts) > 2 else 512
                return {
                    "bpm": bpm,
                    "ibi_ms": ibi,
                    "raw": raw,
                    "status": "OK"
                }
            except ValueError:
                pass

        return None
