import json
import unittest

from shared.messages import Telemetry
from nodes.detector_service.rules import FallDetector

NOW_MS = 1_790_000_000_000


def sample(device, seq, motion=0.0, rotation=0.0, mn=9.81, peak=9.81, t=0, urutan=True):
    return Telemetry(device, "boot-1", seq, NOW_MS + t, motion, rotation, mn, peak, urutan)


class DetectorTests(unittest.TestCase):
    def setUp(self):
        self.d = FallDetector()
        self.d.accept(sample("edge2", 0), now_ms=NOW_MS)

    def feed(self, seq, t, **kw):
        return self.d.accept(sample("edge1", seq, t=t, **kw), now_ms=NOW_MS + t)

    def test_full_fall_sequence_alerts(self):
        self.assertEqual(self.feed(0, 500, motion=3, rotation=2, mn=1.0, peak=12).status, "NORMAL")
        self.assertEqual(self.feed(1, 1000, motion=9, rotation=3, mn=2.0, peak=28).status, "POSSIBLE_FALL")
        self.assertEqual(self.feed(2, 1500).status, "POSSIBLE_FALL")
        self.assertEqual(self.feed(3, 2000).status, "ALERT")

    def test_impact_without_freefall_is_normal(self):
        self.assertEqual(self.feed(0, 500, motion=9, peak=30).status, "NORMAL")

    def test_person_gets_up_no_alert(self):
        self.feed(0, 500, mn=1.0, peak=28, motion=9)
        self.assertEqual(self.feed(1, 1000, motion=3, rotation=1).status, "POSSIBLE_FALL")
        self.assertEqual(self.feed(2, 20_000, motion=3, rotation=1).status, "NORMAL")

    def test_family_phone_moving_does_not_cancel_fall(self):
        self.d.accept(sample("edge2", 1, motion=2.0), now_ms=NOW_MS)
        self.assertEqual(self.feed(0, 500, mn=1.0, peak=28, motion=9).status, "POSSIBLE_FALL")

    def test_alarm_stays_active_until_reset(self):
        self.feed(0, 500, mn=1, peak=28, motion=9)
        self.feed(1, 1000)
        self.assertEqual(self.feed(2, 1500).status, "ALERT")
        self.assertEqual(self.feed(3, 2000).status, "ALERT_ACTIVE")
        self.d.set_armed(True)
        self.assertEqual(self.feed(4, 2500).status, "NORMAL")

    def test_detection_does_not_depend_on_family_telemetry(self):
        self.d = FallDetector()
        self.feed(0, 500, mn=1, peak=28, motion=9)
        self.feed(1, 1000)
        self.assertEqual(self.feed(2, 1500).status, "ALERT")

    def test_impact_before_freefall_in_same_window_is_not_a_fall(self):
        self.assertEqual(self.feed(0, 500, mn=1, peak=28, motion=9, urutan=False).status, "NORMAL")

    def test_restart_does_not_join_two_events(self):
        self.feed(0, 500, mn=1, peak=9.81)
        bacaan = Telemetry("edge1", "boot-baru", 0, NOW_MS + 1000, 9, 0, 9.81, 28, False)
        self.assertEqual(self.d.accept(bacaan, now_ms=NOW_MS + 1000).status, "NORMAL")

    def test_older_timestamp_with_new_sequence_is_rejected(self):
        self.feed(0, 1000)
        self.assertEqual(self.feed(1, 500).status, "REJECTED_STALE")

    def test_replay_rejected(self):
        reading = sample("edge1", 3)
        self.d.accept(reading, now_ms=NOW_MS)
        self.assertEqual(self.d.accept(reading, now_ms=NOW_MS).status, "REJECTED_REPLAY")

    def test_stale_timestamp_rejected(self):
        r = sample("edge1", 5, t=-31_000)
        self.assertEqual(self.d.accept(r, now_ms=NOW_MS).status, "REJECTED_STALE")

    def test_disarm(self):
        self.d.set_armed(False)
        self.assertEqual(self.feed(0, 0, mn=1, peak=30).status, "DISARMED")

    def test_wrong_data_type_rejected(self):
        body = json.dumps({"device_id": "edge1", "boot_id": "abc", "sequence": 2, "sent_at_ms": NOW_MS,
                           "motion_rms": "infinite", "rotation_rad": 0.0})
        with self.assertRaises(ValueError):
            Telemetry.from_json(body)

    def test_payload_without_required_fall_features_is_rejected(self):
        body = json.dumps({"device_id": "edge1", "boot_id": "abc", "sequence": 2, "sent_at_ms": NOW_MS,
                           "motion_rms": 0.1, "rotation_rad": 0.0})
        with self.assertRaises(ValueError):
            Telemetry.from_json(body)


if __name__ == "__main__":
    unittest.main()
