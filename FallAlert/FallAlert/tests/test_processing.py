import unittest

from shared.processing import SensorSample, extract_features


class ProcessingTests(unittest.TestCase):
    def test_stationary_phone(self):
        samples = [SensorSample(i * 0.5, (0, 0, 9.81), (0, 0, 0)) for i in range(5)]
        result = extract_features(samples)
        self.assertAlmostEqual(result.motion_rms, 0, places=3)
        self.assertAlmostEqual(result.rotation_rad, 0, places=3)

    def test_movement_increases_features(self):
        samples = [SensorSample(i * 0.5, (0, 0, 12), (0.5, 0, 0)) for i in range(5)]
        result = extract_features(samples)
        self.assertGreater(result.motion_rms, 2)
        self.assertGreater(result.rotation_rad, 0.9)

    def test_freefall_and_impact_magnitudes(self):
        samples = [SensorSample(i * 0.1, (0, 0, z), (0, 0, 0)) for i, z in enumerate([9.8, 0.8, 0.8, 28, 9.8])]
        result = extract_features(samples)
        self.assertLess(result.min_magnitude, 1)
        self.assertGreater(result.peak_magnitude, 27)
        self.assertTrue(result.min_before_peak)

    def test_impact_before_low_acceleration(self):
        samples = [SensorSample(i * 0.1, (0, 0, z), (0, 0, 0)) for i, z in enumerate([9.8, 28, 0.8])]
        self.assertFalse(extract_features(samples).min_before_peak)

    def test_non_finite_sensor_is_rejected(self):
        samples = [SensorSample(0, (0, 0, 9.81), (0, 0, 0)), SensorSample(1, (0, 0, float("nan")), (0, 0, 0))]
        with self.assertRaises(ValueError):
            extract_features(samples)

    def test_need_multiple_samples(self):
        with self.assertRaises(ValueError):
            extract_features([SensorSample(0, (0, 0, 9.81), (0, 0, 0))])


if __name__ == "__main__":
    unittest.main()
