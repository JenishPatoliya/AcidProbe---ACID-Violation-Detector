"""Tests for core.lock_manager.LockManager"""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.lock_manager import LockManager
from core.transaction import Transaction


class TestLockAcquisition(unittest.TestCase):
    """Test basic lock acquisition."""

    def setUp(self):
        self.lm = LockManager(silent=True)

    def _make_txn(self, tid, ts=1):
        t = Transaction(tid, start_ts=ts)
        self.lm.register(t)
        return t

    def test_acquire_on_empty(self):
        t = self._make_txn("T1")
        result = self.lm.acquire(t, "balance", "S")
        self.assertTrue(result)
        self.assertIn("balance", self.lm.lock_table)

    def test_shared_shared_compatible(self):
        t1 = self._make_txn("T1", 1)
        t2 = self._make_txn("T2", 2)
        self.assertTrue(self.lm.acquire(t1, "balance", "S"))
        self.assertTrue(self.lm.acquire(t2, "balance", "S"))
        # Both should be owners
        self.assertIn("T1", self.lm.lock_table["balance"]["owners"])
        self.assertIn("T2", self.lm.lock_table["balance"]["owners"])

    def test_shared_exclusive_conflict(self):
        t1 = self._make_txn("T1", 1)
        t2 = self._make_txn("T2", 2)
        self.assertTrue(self.lm.acquire(t1, "balance", "S"))
        result = self.lm.acquire(t2, "balance", "X")
        self.assertFalse(result)
        self.assertEqual(t2.status, "WAITING")

    def test_exclusive_shared_conflict(self):
        t1 = self._make_txn("T1", 1)
        t2 = self._make_txn("T2", 2)
        self.assertTrue(self.lm.acquire(t1, "balance", "X"))
        result = self.lm.acquire(t2, "balance", "S")
        self.assertFalse(result)
        self.assertEqual(t2.status, "WAITING")

    def test_exclusive_exclusive_conflict(self):
        t1 = self._make_txn("T1", 1)
        t2 = self._make_txn("T2", 2)
        self.assertTrue(self.lm.acquire(t1, "balance", "X"))
        result = self.lm.acquire(t2, "balance", "X")
        self.assertFalse(result)
        self.assertEqual(t2.status, "WAITING")


class TestLockUpgrade(unittest.TestCase):
    """Test S → X lock upgrade."""

    def setUp(self):
        self.lm = LockManager(silent=True)

    def test_upgrade_s_to_x(self):
        t = Transaction("T1", start_ts=1)
        self.lm.register(t)
        self.lm.acquire(t, "balance", "S")
        result = self.lm.acquire(t, "balance", "X")
        self.assertTrue(result)
        self.assertEqual(self.lm.lock_table["balance"]["type"], "X")

    def test_reacquire_same_lock(self):
        t = Transaction("T1", start_ts=1)
        self.lm.register(t)
        self.lm.acquire(t, "balance", "S")
        result = self.lm.acquire(t, "balance", "S")
        self.assertTrue(result)


class TestLockRelease(unittest.TestCase):
    """Test lock release and waiter wakeup."""

    def setUp(self):
        self.lm = LockManager(silent=True)

    def test_release_removes_lock(self):
        t = Transaction("T1", start_ts=1)
        self.lm.register(t)
        self.lm.acquire(t, "balance", "X")
        self.lm.release(t)
        self.assertNotIn("balance", self.lm.lock_table)

    def test_release_wakes_waiting_txn(self):
        t1 = Transaction("T1", start_ts=1)
        t2 = Transaction("T2", start_ts=2)
        self.lm.register(t1)
        self.lm.register(t2)

        self.lm.acquire(t1, "balance", "X")
        self.lm.acquire(t2, "balance", "X")  # T2 blocked
        self.assertEqual(t2.status, "WAITING")

        self.lm.release(t1)
        self.assertEqual(t2.status, "ACTIVE")

    def test_release_shared_lock(self):
        t = Transaction("T1", start_ts=1)
        self.lm.register(t)
        self.lm.acquire(t, "balance", "S")
        self.lm.release_shared_lock(t, "balance")
        self.assertNotIn("balance", self.lm.lock_table)


class TestDeadlockDetection(unittest.TestCase):
    """Test DFS-based deadlock detection."""

    def setUp(self):
        self.lm = LockManager(silent=True)

    def test_detect_cycle(self):
        self.lm.wait_for_graph = {"T1": "T2", "T2": "T1"}
        self.assertTrue(self.lm.detect_deadlock("T1"))

    def test_no_cycle(self):
        self.lm.wait_for_graph = {"T1": "T2"}
        self.assertFalse(self.lm.detect_deadlock("T1"))

    def test_find_cycle_path(self):
        self.lm.wait_for_graph = {"T1": "T2", "T2": "T1"}
        cycle = self.lm.find_deadlock_cycle()
        self.assertIsNotNone(cycle)
        # Should contain both T1 and T2
        self.assertIn("T1", cycle)
        self.assertIn("T2", cycle)

    def test_find_no_cycle_returns_none(self):
        self.lm.wait_for_graph = {"T1": "T2"}
        cycle = self.lm.find_deadlock_cycle()
        self.assertIsNone(cycle)


class TestDeadlockResolution(unittest.TestCase):
    """Test deadlock victim selection (youngest transaction)."""

    def setUp(self):
        self.lm = LockManager(silent=True)

    def test_youngest_is_victim(self):
        t1 = Transaction("T1", start_ts=1)
        t2 = Transaction("T2", start_ts=5)
        self.lm.register(t1)
        self.lm.register(t2)

        victim = self.lm.resolve_deadlock(["T1", "T2"])
        self.assertEqual(victim.tid, "T2")
        self.assertEqual(victim.status, "ABORTED")


class TestLockTableString(unittest.TestCase):
    """Test lock table string representation."""

    def test_empty_table(self):
        lm = LockManager(silent=True)
        self.assertEqual(lm.get_lock_table_str(), "(empty)")

    def test_nonempty_table(self):
        lm = LockManager(silent=True)
        t = Transaction("T1", start_ts=1)
        lm.register(t)
        lm.acquire(t, "balance", "X")
        result = lm.get_lock_table_str()
        self.assertIn("balance", result)
        self.assertIn("X", result)
        self.assertIn("T1", result)


if __name__ == "__main__":
    unittest.main()
