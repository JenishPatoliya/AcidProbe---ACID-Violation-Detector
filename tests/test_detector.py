"""Tests for core.detector.AnomalyDetector"""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.detector import AnomalyDetector
from core.transaction import Transaction
from core.data_store import MVCCDataStore


class TestDirtyReadDetection(unittest.TestCase):
    """Test dirty read anomaly detection."""

    def setUp(self):
        self.det = AnomalyDetector()

    def test_detects_dirty_read(self):
        writer = Transaction("T1", start_ts=1)
        writer.write_set["balance"] = 800  # T1 wrote but not committed

        reader = Transaction("T2", start_ts=2)
        result = self.det.check_dirty_read(reader, writer, "balance", 800)
        self.assertTrue(result)
        self.assertEqual(len(self.det.anomalies), 1)
        self.assertEqual(self.det.anomalies[0]["type"], "DIRTY READ")

    def test_no_dirty_read_if_committed(self):
        writer = Transaction("T1", start_ts=1)
        writer.write_set["balance"] = 800
        writer.commit()

        reader = Transaction("T2", start_ts=2)
        result = self.det.check_dirty_read(reader, writer, "balance", 800)
        self.assertFalse(result)
        self.assertEqual(len(self.det.anomalies), 0)

    def test_no_dirty_read_if_different_value(self):
        writer = Transaction("T1", start_ts=1)
        writer.write_set["balance"] = 800

        reader = Transaction("T2", start_ts=2)
        result = self.det.check_dirty_read(reader, writer, "balance", 1000)
        self.assertFalse(result)

    def test_no_dirty_read_if_key_not_in_write_set(self):
        writer = Transaction("T1", start_ts=1)
        reader = Transaction("T2", start_ts=2)
        result = self.det.check_dirty_read(reader, writer, "balance", 1000)
        self.assertFalse(result)


class TestNonRepeatableReadDetection(unittest.TestCase):
    """Test non-repeatable read anomaly detection."""

    def setUp(self):
        self.det = AnomalyDetector()

    def test_detects_non_repeatable_read(self):
        t = Transaction("T1", start_ts=1)
        result = self.det.check_non_repeatable_read(t, "balance", 1000, 800)
        self.assertTrue(result)
        self.assertEqual(len(self.det.anomalies), 1)
        self.assertEqual(self.det.anomalies[0]["type"], "NON-REPEATABLE READ")

    def test_no_anomaly_if_same_value(self):
        t = Transaction("T1", start_ts=1)
        result = self.det.check_non_repeatable_read(t, "balance", 1000, 1000)
        self.assertFalse(result)
        self.assertEqual(len(self.det.anomalies), 0)

    def test_no_anomaly_if_old_value_none(self):
        t = Transaction("T1", start_ts=1)
        result = self.det.check_non_repeatable_read(t, "balance", None, 1000)
        self.assertFalse(result)


class TestLostUpdateDetection(unittest.TestCase):
    """Test lost update anomaly detection."""

    def setUp(self):
        self.det = AnomalyDetector()
        self.db = MVCCDataStore()
        self.db.init_data("balance", 1000)

    def test_detects_lost_update(self):
        t1 = Transaction("T1", start_ts=1)
        t2 = Transaction("T2", start_ts=2)

        # Both read the same value
        t1.read_set["balance"] = 1000
        t2.read_set["balance"] = 1000

        # Both write different values
        t1.write_set["balance"] = 700
        t2.write_set["balance"] = 800

        t1.commit()
        t2.commit()

        result = self.det.check_lost_update(t1, t2, "balance", self.db)
        self.assertTrue(result)
        self.assertEqual(self.det.anomalies[0]["type"], "LOST UPDATE")

    def test_no_lost_update_if_only_one_writes(self):
        t1 = Transaction("T1", start_ts=1)
        t2 = Transaction("T2", start_ts=2)

        t1.read_set["balance"] = 1000
        t2.read_set["balance"] = 1000

        t1.write_set["balance"] = 700
        # T2 does NOT write

        t1.commit()
        t2.commit()

        result = self.det.check_lost_update(t1, t2, "balance", self.db)
        self.assertFalse(result)

    def test_no_lost_update_if_different_reads(self):
        t1 = Transaction("T1", start_ts=1)
        t2 = Transaction("T2", start_ts=2)

        t1.read_set["balance"] = 1000
        t2.read_set["balance"] = 800  # different read

        t1.write_set["balance"] = 700
        t2.write_set["balance"] = 600

        t1.commit()
        t2.commit()

        result = self.det.check_lost_update(t1, t2, "balance", self.db)
        self.assertFalse(result)

    def test_no_lost_update_if_key_not_read(self):
        t1 = Transaction("T1", start_ts=1)
        t2 = Transaction("T2", start_ts=2)

        t1.write_set["balance"] = 700
        t2.write_set["balance"] = 800

        result = self.det.check_lost_update(t1, t2, "balance", self.db)
        self.assertFalse(result)


class TestAnomalyReport(unittest.TestCase):
    """Test the report method runs without error."""

    def test_report_with_anomalies(self):
        import io
        det = AnomalyDetector()
        det.anomalies = [{"type": "DIRTY READ", "description": "test", "fix": "fix"}]
        old_stdout = sys.stdout
        sys.stdout = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
        try:
            det.print_report()  # should not raise
        finally:
            sys.stdout = old_stdout

    def test_report_without_anomalies(self):
        import io
        det = AnomalyDetector()
        old_stdout = sys.stdout
        sys.stdout = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
        try:
            det.print_report()  # should not raise
        finally:
            sys.stdout = old_stdout


if __name__ == "__main__":
    unittest.main()
