import unittest
from pathlib import Path

from app.tools.coros.fit_parser import parse_fit_activity


SAMPLE_FIT = Path("var/coros_real_sync/exports/477263761401479169/477263761401479169.fit")


@unittest.skipUnless(SAMPLE_FIT.exists(), "real COROS FIT sample is not present")
class CorosFitParserTestCase(unittest.TestCase):
    def test_parse_real_fit_sample_includes_gps_laps_and_session_summary(self) -> None:
        detail = parse_fit_activity(SAMPLE_FIT.read_bytes())

        self.assertEqual(4092, len(detail.samples))
        self.assertEqual(11, len(detail.laps))
        gps_sample = next(sample for sample in detail.samples if sample.latitude and sample.longitude)
        self.assertAlmostEqual(40.0537002, gps_sample.latitude, places=5)
        self.assertAlmostEqual(116.3391551, gps_sample.longitude, places=5)
        self.assertAlmostEqual(10011.72, float(detail.session["total_distance"]), places=2)
        self.assertAlmostEqual(4091.76, float(detail.session["total_timer_time"]), places=2)
        self.assertEqual(154, detail.session["avg_heart_rate"])
        self.assertEqual(193, detail.session["max_heart_rate"])
        self.assertEqual(11, len([lap for lap in detail.laps if lap.distance_m]))


if __name__ == "__main__":
    unittest.main()
