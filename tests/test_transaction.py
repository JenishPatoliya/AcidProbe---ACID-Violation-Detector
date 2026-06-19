"""Tests for core.transaction.Transaction"""

import unittest
import sys
import os

# Ensure project root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.transaction import Transaction


class TestTransactionInit(unittest.TestCase):
    """Test Transaction construction and defaults."""

    def test_default_state(self):
        t = Transaction("T1", start_ts=1)
        self.assertEqual(t.tid, "T1")
        self.assertEqual(t.start_ts, 1)
        self.assertEqual(t.status, "ACTIVE")
        self.assertEqual(t.isolation, "READ_COMMITTED")
        self.assertEqual(t.read_set, {})
        self.assertEqual(t.write_set, {})

    def test_custom_isolation(self):
        t = Transaction("T2", start_ts=5, isolation="SERIALIZABLE")
        self.assertEqual(t.isolation, "SERIALIZABLE")


class TestIsolationHelpers(unittest.TestCase):
    """Test isolation-level convenience methods."""

    def test_read_uncommitted_allows_dirty(self):
        t = Transaction("T1", 1, isolation="READ_UNCOMMITTED")
        self.assertTrue(t.allows_dirty_read())
        self.assertTrue(t.allows_non_repeatable_read())
        self.assertTrue(t.allows_phantom_read())

    def test_read_committed_blocks_dirty(self):
        t = Transaction("T1", 1, isolation="READ_COMMITTED")
        self.assertFalse(t.allows_dirty_read())
        self.assertTrue(t.allows_non_repeatable_read())
        self.assertTrue(t.allows_phantom_read())

    def test_repeatable_read_blocks_non_repeatable(self):
        t = Transaction("T1", 1, isolation="REPEATABLE_READ")
        self.assertFalse(t.allows_dirty_read())
        self.assertFalse(t.allows_non_repeatable_read())
        self.assertTrue(t.allows_phantom_read())

    def test_serializable_blocks_all(self):
        t = Transaction("T1", 1, isolation="SERIALIZABLE")
        self.assertFalse(t.allows_dirty_read())
        self.assertFalse(t.allows_non_repeatable_read())
        self.assertFalse(t.allows_phantom_read())


class TestTransactionStateTransitions(unittest.TestCase):
    """Test commit / rollback state machine."""

    def test_commit_from_active(self):
        t = Transaction("T1", 1)
        t.commit()
        self.assertEqual(t.status, "COMMITTED")

    def test_rollback_from_active(self):
        t = Transaction("T1", 1)
        t.rollback()
        self.assertEqual(t.status, "ABORTED")

    def test_commit_after_abort_raises(self):
        t = Transaction("T1", 1)
        t.rollback()
        with self.assertRaises(ValueError):
            t.commit()

    def test_rollback_after_commit_raises(self):
        t = Transaction("T1", 1)
        t.commit()
        with self.assertRaises(ValueError):
            t.rollback()

    def test_double_commit_is_idempotent(self):
        t = Transaction("T1", 1)
        t.commit()
        t.commit()  # should not raise
        self.assertEqual(t.status, "COMMITTED")

    def test_double_rollback_is_idempotent(self):
        t = Transaction("T1", 1)
        t.rollback()
        t.rollback()  # should not raise
        self.assertEqual(t.status, "ABORTED")

    def test_commit_clears_wait_fields(self):
        t = Transaction("T1", 1)
        t.wait_key = "balance"
        t.wait_lock_type = "X"
        t.commit()
        self.assertIsNone(t.wait_key)
        self.assertIsNone(t.wait_lock_type)

    def test_rollback_clears_wait_fields(self):
        t = Transaction("T1", 1)
        t.wait_key = "balance"
        t.wait_lock_type = "S"
        t.rollback()
        self.assertIsNone(t.wait_key)
        self.assertIsNone(t.wait_lock_type)


class TestTransactionStr(unittest.TestCase):
    def test_str_representation(self):
        t = Transaction("T1", 1)
        self.assertEqual(str(t), "Transaction(T1, ACTIVE)")


if __name__ == "__main__":
    unittest.main()
