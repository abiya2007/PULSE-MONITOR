"""
Unit tests for Pulse Rate Health Analyzer and SQLite Session Database.
"""

import unittest
import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))

from health_analyzer import HealthAnalyzer, SessionDatabase
from simulator import PulseSimulator


class TestPulseHealthAnalyzer(unittest.TestCase):

    def test_deep_rest_bradycardia(self):
        res = HealthAnalyzer.analyze_pulse(45.0)
        self.assertEqual(res["category"], "DEEP_REST_BRADYCARDIA")
        self.assertEqual(res["emoji"], "😴")
        self.assertIn("Zzz", res["dialogue"])
        self.assertIn("Deep Rest", res["status"])

    def test_resting_relaxed(self):
        res = HealthAnalyzer.analyze_pulse(58.0)
        self.assertEqual(res["category"], "RESTING_RELAXED")
        self.assertEqual(res["emoji"], "🧘 😌")
        self.assertIn("calm", res["dialogue"].lower())
        self.assertIn("Calm, relaxed", res["summary"])

    def test_normal_resting(self):
        res = HealthAnalyzer.analyze_pulse(72.0)
        self.assertEqual(res["category"], "NORMAL_RESTING")
        self.assertEqual(res["emoji"], "😊 💙")
        self.assertIn("great", res["dialogue"].lower())
        self.assertIn("baseline", res["summary"])

    def test_light_activity(self):
        res = HealthAnalyzer.analyze_pulse(95.0)
        self.assertEqual(res["category"], "LIGHT_ACTIVITY")
        self.assertEqual(res["emoji"], "🤩 💓")
        self.assertIn("energized", res["dialogue"].lower())
        self.assertIn("Excited", res["status"])

    def test_moderate_workout(self):
        res = HealthAnalyzer.analyze_pulse(120.0)
        self.assertEqual(res["category"], "MODERATE_WORKOUT")
        self.assertEqual(res["emoji"], "🏃 ⚡")
        self.assertIn("zone", res["dialogue"].lower())
        self.assertIn("Fat Burn", res["status"])

    def test_intense_exercise(self):
        res = HealthAnalyzer.analyze_pulse(145.0)
        self.assertEqual(res["category"], "INTENSE_EXERCISE")
        self.assertEqual(res["emoji"], "🏋️ 💦")
        self.assertIn("hard", res["dialogue"].lower())
        self.assertIn("Cardio", res["status"])

    def test_maximum_effort(self):
        res = HealthAnalyzer.analyze_pulse(170.0)
        self.assertEqual(res["category"], "MAXIMUM_EFFORT")
        self.assertEqual(res["emoji"], "🥵 💥")
        self.assertIn("exertion", res["dialogue"].lower())
        self.assertIn("Danger zone", res["summary"])

    def test_irregular_hrv(self):
        ibis = [800.0, 500.0, 1100.0, 600.0, 1200.0, 550.0]
        res = HealthAnalyzer.analyze_pulse(75.0, 800.0, ibis)
        self.assertEqual(res["category"], "IRREGULAR")
        self.assertTrue(res["hrv_sdnn"] > 100.0)


class TestSessionDatabase(unittest.TestCase):

    def setUp(self):
        self.db_file = "test_pulse_sessions.db"
        if os.path.exists(self.db_file):
            os.remove(self.db_file)
        self.db = SessionDatabase(self.db_file)

    def tearDown(self):
        if os.path.exists(self.db_file):
            os.remove(self.db_file)

    def test_session_lifecycle(self):
        session_id = self.db.start_session("Test Session")
        self.assertIsInstance(session_id, int)

        analysis1 = HealthAnalyzer.analyze_pulse(72.0)
        analysis2 = HealthAnalyzer.analyze_pulse(120.0)

        self.db.log_reading(session_id, analysis1, 512)
        self.db.log_reading(session_id, analysis2, 600)

        summary = self.db.end_session(session_id)
        self.assertEqual(summary["total_readings"], 2)
        self.assertEqual(summary["min_bpm"], 72.0)
        self.assertEqual(summary["max_bpm"], 120.0)

        full_report = self.db.get_session_summary(session_id)
        self.assertIsNotNone(full_report)
        self.assertEqual(len(full_report["readings"]), 2)


if __name__ == "__main__":
    unittest.main()
