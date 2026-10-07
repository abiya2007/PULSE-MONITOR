"""
Pulse Rate Health & Symptom Analysis Engine with Timeline Logging.
Provides clinical reference evaluation of pulse rate metrics, symptom mapping,
and SQLite session persistence ("when & how", timeline, min/max/avg BPM).
"""

import sqlite3
import math
import os
import time
from typing import Dict, Any, List, Optional
from datetime import datetime


class HealthAnalyzer:
    """Clinical reference analyzer for pulse rate data."""

    @staticmethod
    def analyze_pulse(
        bpm: float,
        ibi_ms: Optional[float] = None,
        recent_ibis: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Analyzes heart rate (BPM) and Inter-Beat Interval (IBI in ms).
        Returns classification, status, symptoms, disease reference, and advice.
        """
        bpm = round(float(bpm), 1)
        ibi = round(float(ibi_ms), 1) if ibi_ms is not None else round(60000.0 / max(bpm, 1), 1)

        # Assess HRV / Irregularity if recent IBIs provided
        is_irregular = False
        hrv_sdnn = 0.0
        if recent_ibis and len(recent_ibis) >= 5:
            avg_ibi = sum(recent_ibis) / len(recent_ibis)
            variance = sum((x - avg_ibi) ** 2 for x in recent_ibis) / len(recent_ibis)
            hrv_sdnn = round(math.sqrt(variance), 1)
            if hrv_sdnn > 120.0:  # High beat-to-beat variability threshold
                is_irregular = True

        # Classification logic based on precise user specified BPM zones
        if is_irregular:
            category = "IRREGULAR"
            status_title = "Irregular Rhythm / Arrhythmia"
            emoji = "⚡ ⚠️"
            dialogue = "Whoa! Felt a slight flutter or irregular beat interval. Taking a moment to pause, breathe, and rest."
            severity = "danger"
            summary = "Irregular pulse interval detected (Arrhythmia pattern)."
            symptoms = [
                "Palpitations or flutter in chest",
                "Transient lightheadedness or dizziness",
                "Shortness of breath",
                "Fatigue or sudden weakness"
            ]
            diseases = [
                "Atrial Fibrillation (AFib)",
                "Premature Ventricular Contractions (PVCs)",
                "Sinus Arrhythmia",
                "Electrolyte imbalance (Potassium/Magnesium)"
            ]
            advice = (
                "An irregular rhythm was detected in beat timing variance. "
                "If accompanied by chest tightness or severe dizziness, seek prompt medical evaluation."
            )

        elif bpm < 50:
            category = "DEEP_REST_BRADYCARDIA"
            status_title = "Bradycardia / Deep Rest"
            emoji = "😴"
            dialogue = "Zzz... Body is in deep restful recovery mode. Muscle repair and energy conservation are active."
            severity = "info"
            summary = "Sleeping / Very low heart rate."
            symptoms = [
                "Dizziness or lightheadedness (if awake)",
                "Extreme fatigue or lethargy",
                "Deep sleep state / Athletic resting baseline"
            ]
            diseases = [
                "Physiological sleep state",
                "High vagal tone / Athletic bradycardia",
                "Sick Sinus Syndrome or Heart Block (if symptomatic)"
            ]
            advice = "Heart rate is under 50 BPM. Common during deep sleep or in trained endurance athletes."

        elif 50 <= bpm <= 65:
            category = "RESTING_RELAXED"
            status_title = "Resting / Relaxed"
            emoji = "🧘 😌"
            dialogue = "Feeling super calm, composed, and peaceful. Mind is steady and breathing is smooth."
            severity = "success"
            summary = "Calm, relaxed state."
            symptoms = [
                "No abnormal symptoms",
                "Calm and relaxed physical state"
            ]
            diseases = [
                "Optimal resting cardiovascular state",
                "Normal sinus rhythm"
            ]
            advice = "Heart rate is 50-65 BPM, indicating an optimal calm and relaxed state."

        elif 66 <= bpm <= 85:
            category = "NORMAL_RESTING"
            status_title = "Normal Resting"
            emoji = "😊 💙"
            dialogue = "Feeling great! Baseline energy is stable, healthy, and perfectly balanced."
            severity = "success"
            summary = "Normal healthy baseline pulse."
            symptoms = [
                "No abnormal symptoms",
                "Normal energy levels"
            ]
            diseases = [
                "Standard resting baseline heart rate",
                "Normal healthy cardiovascular state"
            ]
            advice = "Your pulse rate is between 66-85 BPM, representing a healthy baseline resting pulse."

        elif 86 <= bpm <= 110:
            category = "LIGHT_ACTIVITY"
            status_title = "Light Activity / Excited"
            emoji = "🤩 💓"
            dialogue = "Woohoo! Feeling energized, active, or slightly thrilled. Blood is pumping smoothly!"
            severity = "warning"
            summary = "Mild movement, light stress, or excitement."
            symptoms = [
                "Slightly increased pulse awareness",
                "Mild warmth or excitement"
            ]
            diseases = [
                "Light walking or daily physical movement",
                "Mild emotional excitement or caffeine intake",
                "Elevated resting baseline"
            ]
            advice = "Heart rate is 86-110 BPM. Typical during light activity, walking, or mild stress."

        elif 111 <= bpm <= 130:
            category = "MODERATE_WORKOUT"
            status_title = "Moderate Workout (Fat Burn)"
            emoji = "🏃 ⚡"
            dialogue = "In the zone! Burning fat, breathing actively, and powering through a great workout!"
            severity = "warning"
            summary = "Aerobic activity, active exercise."
            symptoms = [
                "Increased breathing rate",
                "Active muscle engagement & sweating"
            ]
            diseases = [
                "Aerobic exercise / Fat burn training zone",
                "Moderate physical exertion"
            ]
            advice = "Heart rate is 111-130 BPM. You are in the moderate aerobic/fat burn workout zone."

        elif 131 <= bpm <= 160:
            category = "INTENSE_EXERCISE"
            status_title = "Intense Exercise (Cardio)"
            emoji = "🏋️ 💦"
            dialogue = "Pushing hard! Heart is pumping fast, muscles are working, and sweat is flowing!"
            severity = "alert"
            summary = "Heavy breathing, sweating."
            symptoms = [
                "Heavy breathing and shortness of breath",
                "Profuse sweating and muscular fatigue",
                "Pounding heart beat"
            ]
            diseases = [
                "Cardiovascular endurance training zone",
                "High physical exertion / Intense exercise"
            ]
            advice = "Heart rate is 131-160 BPM. Intense cardio exercise zone. Ensure adequate hydration."

        else:  # bpm > 160
            category = "MAXIMUM_EFFORT"
            status_title = "Maximum Effort / Extreme"
            emoji = "🥵 💥"
            dialogue = "Maximum exertion! Pushing to peak capacity—breathing heavy and giving it everything!"
            severity = "danger"
            summary = "High intensity / Danger zone warning."
            symptoms = [
                "Extreme shortness of breath",
                "Heavy exhaustion or dizziness risk",
                "Chest pounding / Tightness"
            ]
            diseases = [
                "Maximum heart rate training capacity",
                "Extreme physical exertion",
                "Severe Tachycardia (if occurring at rest)"
            ]
            advice = "CRITICAL: Heart rate exceeds 160 BPM! If you are not performing peak maximum effort exercise, stop and rest immediately."

        status_display = f"{status_title} {emoji}"

        return {
            "bpm": bpm,
            "ibi_ms": ibi,
            "hrv_sdnn": hrv_sdnn,
            "category": category,
            "status": status_display,
            "status_title": status_title,
            "emoji": emoji,
            "dialogue": dialogue,
            "severity": severity,
            "summary": summary,
            "symptoms": symptoms,
            "potential_diseases": diseases,
            "advice": advice,
            "timestamp": datetime.now().isoformat(),
            "disclaimer": "This analysis is for educational and experimental monitoring only. Not a formal medical diagnostic tool."
        }


class SessionDatabase:
    """SQLite Database manager for tracking pulse rate timeline sessions."""

    def __init__(self, db_path: str = "pulse_sessions.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    total_readings INTEGER DEFAULT 0,
                    min_bpm REAL,
                    max_bpm REAL,
                    avg_bpm REAL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS readings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    bpm REAL NOT NULL,
                    ibi_ms REAL,
                    category TEXT,
                    status TEXT,
                    raw_signal INTEGER,
                    FOREIGN KEY (session_id) REFERENCES sessions (id)
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def start_session(self, name: str = "Pulse Monitor Session") -> int:
        now = datetime.now().isoformat()
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO sessions (name, start_time) VALUES (?, ?)",
                (name, now)
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def log_reading(self, session_id: int, analysis: Dict[str, Any], raw_signal: int = 0):
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO readings (session_id, timestamp, bpm, ibi_ms, category, status, raw_signal)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                analysis["timestamp"],
                analysis["bpm"],
                analysis["ibi_ms"],
                analysis["category"],
                analysis["status"],
                raw_signal
            ))
            conn.commit()
        finally:
            conn.close()

    def end_session(self, session_id: int) -> Dict[str, Any]:
        now = datetime.now().isoformat()
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT bpm FROM readings WHERE session_id = ?", (session_id,)
            )
            rows = cursor.fetchall()
            if rows:
                bpms = [r[0] for r in rows]
                min_bpm = round(min(bpms), 1)
                max_bpm = round(max(bpms), 1)
                avg_bpm = round(sum(bpms) / len(bpms), 1)
                total = len(bpms)
            else:
                min_bpm = max_bpm = avg_bpm = 0.0
                total = 0

            cursor.execute("""
                UPDATE sessions
                SET end_time = ?, total_readings = ?, min_bpm = ?, max_bpm = ?, avg_bpm = ?
                WHERE id = ?
            """, (now, total, min_bpm, max_bpm, avg_bpm, session_id))
            conn.commit()

            return {
                "session_id": session_id,
                "end_time": now,
                "total_readings": total,
                "min_bpm": min_bpm,
                "max_bpm": max_bpm,
                "avg_bpm": avg_bpm
            }
        finally:
            conn.close()

    def get_session_summary(self, session_id: int) -> Optional[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
            session = cursor.fetchone()
            if not session:
                return None

            cursor.execute(
                "SELECT timestamp, bpm, ibi_ms, category, status FROM readings WHERE session_id = ? ORDER BY id ASC",
                (session_id,)
            )
            readings = [dict(r) for r in cursor.fetchall()]

            events = []
            for r in readings:
                if r["category"] not in ["NORMAL"]:
                    events.append({
                        "time": r["timestamp"],
                        "bpm": r["bpm"],
                        "status": r["status"],
                        "category": r["category"]
                    })

            return {
                "session_info": dict(session),
                "events_timeline": events,
                "readings": readings
            }
        finally:
            conn.close()

    def get_all_sessions(self) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions ORDER BY id DESC LIMIT 20")
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
