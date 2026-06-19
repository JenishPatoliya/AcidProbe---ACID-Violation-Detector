"""Tests for core.data_store.MVCCDataStore"""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.data_store import MVCCDataStore
from core.transaction import Transaction


class TestInitData(unittest.TestCase):
    """Test initial data seeding."""

    def test_init_creates_version(self):
        db = MVCCDataStore()
        db.init_data("balance", 1000)
        self.assertIn("balance", db.data)
        self.assertEqual(len(db.data["balance"]), 1)
        v = db.data["balance"][0]
        self.assertEqual(v["value"], 1000)
        self.assertEqual(v["ts"], 0)
        self.assertEqual(v["by"], "SYSTEM")
        self.assertTrue(v["committed"])

    def test_init_data_idempotent(self):
        db = MVCCDataStore()
        db.init_data("balance", 1000)
        db.init_data("balance", 9999)  # should NOT overwrite
        self.assertEqual(len(db.data["balance"]), 1)
        self.assertEqual(db.data["balance"][0]["value"], 1000)


class TestReadVisibility(unittest.TestCase):
    """Test MVCC read visibility under different isolation levels."""

    def setUp(self):
        self.db = MVCCDataStore()
        self.db.init_data("balance", 1000)

    def test_read_committed_sees_only_committed(self):
        writer = Transaction("T1", start_ts=1, isolation="READ_COMMITTED")
        self.db.write("balance", 800, writer)  # uncommitted

        reader = Transaction("T2", start_ts=2, isolation="READ_COMMITTED")
        val = self.db.read("balance", reader)
        self.assertEqual(val, 1000)  # should NOT see uncommitted 800

    def test_read_uncommitted_sees_uncommitted(self):
        writer = Transaction("T1", start_ts=1, isolation="READ_UNCOMMITTED")
        self.db.write("balance", 800, writer)  # uncommitted

        reader = Transaction("T2", start_ts=2, isolation="READ_UNCOMMITTED")
        val = self.db.read("balance", reader)
        self.assertEqual(val, 800)  # should see uncommitted

    def test_repeatable_read_snapshot(self):
        """REPEATABLE_READ only sees versions with ts <= start_ts."""
        writer = Transaction("T1", start_ts=5, isolation="READ_COMMITTED")
        self.db.write("balance", 500, writer)
        self.db.commit_transaction(writer)

        # Reader started at ts=3, before T1 wrote at ts=6
        reader = Transaction("T2", start_ts=3, isolation="REPEATABLE_READ")
        val = self.db.read("balance", reader)
        self.assertEqual(val, 1000)  # snapshot sees only ts=0 SYSTEM version

    def test_read_nonexistent_key(self):
        reader = Transaction("T1", start_ts=1)
        val = self.db.read("nonexistent", reader)
        self.assertIsNone(val)


class TestWrite(unittest.TestCase):
    """Test write versioning."""

    def test_write_creates_uncommitted_version(self):
        db = MVCCDataStore()
        db.init_data("balance", 1000)
        t = Transaction("T1", start_ts=1)
        db.write("balance", 800, t)

        self.assertEqual(len(db.data["balance"]), 2)
        new_v = db.data["balance"][1]
        self.assertEqual(new_v["value"], 800)
        self.assertEqual(new_v["by"], "T1")
        self.assertFalse(new_v["committed"])

    def test_write_updates_write_set(self):
        db = MVCCDataStore()
        db.init_data("balance", 1000)
        t = Transaction("T1", start_ts=1)
        db.write("balance", 800, t)
        self.assertEqual(t.write_set["balance"], 800)

    def test_write_to_new_key(self):
        db = MVCCDataStore()
        t = Transaction("T1", start_ts=1)
        db.write("new_key", 42, t)
        self.assertIn("new_key", db.data)
        self.assertEqual(db.data["new_key"][0]["value"], 42)


class TestCommitAndRollback(unittest.TestCase):
    """Test commit and rollback on the data store."""

    def setUp(self):
        self.db = MVCCDataStore()
        self.db.init_data("balance", 1000)

    def test_commit_marks_versions_committed(self):
        t = Transaction("T1", start_ts=1)
        self.db.write("balance", 800, t)
        self.db.commit_transaction(t)

        new_v = self.db.data["balance"][1]
        self.assertTrue(new_v["committed"])
        self.assertEqual(t.status, "COMMITTED")

    def test_commit_aborted_raises(self):
        t = Transaction("T1", start_ts=1)
        self.db.write("balance", 800, t)
        t.rollback()
        with self.assertRaises(ValueError):
            self.db.commit_transaction(t)

    def test_rollback_removes_uncommitted_versions(self):
        t = Transaction("T1", start_ts=1)
        self.db.write("balance", 800, t)
        self.db.rollback_transaction(t)

        # Only the initial SYSTEM version should remain
        self.assertEqual(len(self.db.data["balance"]), 1)
        self.assertEqual(self.db.data["balance"][0]["value"], 1000)
        self.assertEqual(t.status, "ABORTED")

    def test_rollback_returns_restored_info(self):
        t = Transaction("T1", start_ts=1)
        self.db.write("balance", 800, t)
        restored = self.db.rollback_transaction(t)

        self.assertEqual(len(restored), 1)
        key, written_val, prev_val = restored[0]
        self.assertEqual(key, "balance")
        self.assertEqual(written_val, 800)
        self.assertEqual(prev_val, 1000)


class TestGetLatest(unittest.TestCase):
    """Test get_latest committed value."""

    def test_get_latest_initial(self):
        db = MVCCDataStore()
        db.init_data("balance", 1000)
        self.assertEqual(db.get_latest("balance"), 1000)

    def test_get_latest_after_commit(self):
        db = MVCCDataStore()
        db.init_data("balance", 1000)
        t = Transaction("T1", start_ts=1)
        db.write("balance", 800, t)
        db.commit_transaction(t)
        self.assertEqual(db.get_latest("balance"), 800)

    def test_get_latest_ignores_uncommitted(self):
        db = MVCCDataStore()
        db.init_data("balance", 1000)
        t = Transaction("T1", start_ts=1)
        db.write("balance", 800, t)  # not committed
        self.assertEqual(db.get_latest("balance"), 1000)

    def test_get_latest_nonexistent_key(self):
        db = MVCCDataStore()
        self.assertIsNone(db.get_latest("nope"))


if __name__ == "__main__":
    unittest.main()
