"""Tests for core.serializable_checker.SerializabilityChecker"""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.serializable_checker import SerializabilityChecker
from core.transaction import Transaction


class TestGraphBuilding(unittest.TestCase):
    """Test precedence graph construction from transactions."""

    def test_read_write_conflict(self):
        """T1 reads key, T2 writes key → T1 → T2 edge."""
        t1 = Transaction("T1", start_ts=1)
        t2 = Transaction("T2", start_ts=2)

        t1.read_set["balance"] = 1000
        t2.write_set["balance"] = 800
        t1.commit()
        t2.commit()

        sc = SerializabilityChecker()
        sc.build_graph([t1, t2])

        self.assertIn("T2", sc.graph.get("T1", []))

    def test_write_read_conflict(self):
        """T1 writes key, T2 reads key → T1 → T2 edge."""
        t1 = Transaction("T1", start_ts=1)
        t2 = Transaction("T2", start_ts=2)

        t1.write_set["balance"] = 800
        t2.read_set["balance"] = 800
        t1.commit()
        t2.commit()

        sc = SerializabilityChecker()
        sc.build_graph([t1, t2])

        self.assertIn("T2", sc.graph.get("T1", []))

    def test_write_write_conflict(self):
        """T1 writes key, T2 writes key → T1 → T2 edge."""
        t1 = Transaction("T1", start_ts=1)
        t2 = Transaction("T2", start_ts=2)

        t1.write_set["balance"] = 800
        t2.write_set["balance"] = 600
        t1.commit()
        t2.commit()

        sc = SerializabilityChecker()
        sc.build_graph([t1, t2])

        self.assertIn("T2", sc.graph.get("T1", []))

    def test_no_conflict_different_keys(self):
        """No edge if transactions touch different keys."""
        t1 = Transaction("T1", start_ts=1)
        t2 = Transaction("T2", start_ts=2)

        t1.write_set["balance"] = 800
        t2.write_set["savings"] = 500
        t1.commit()
        t2.commit()

        sc = SerializabilityChecker()
        sc.build_graph([t1, t2])

        self.assertEqual(sc.graph.get("T1", []), [])
        self.assertEqual(sc.graph.get("T2", []), [])

    def test_aborted_writes_excluded(self):
        """Aborted transaction writes should not produce edges."""
        t1 = Transaction("T1", start_ts=1)
        t2 = Transaction("T2", start_ts=2)

        t1.write_set["balance"] = 800
        t1.rollback()  # aborted
        t2.write_set["balance"] = 600
        t2.commit()

        sc = SerializabilityChecker()
        sc.build_graph([t1, t2])

        self.assertEqual(sc.graph.get("T1", []), [])
        self.assertEqual(sc.graph.get("T2", []), [])

    def test_graph_from_steps(self):
        """Build graph from step-based execution log."""
        t1 = Transaction("T1", start_ts=1)
        t2 = Transaction("T2", start_ts=2)
        t1.commit()
        t2.commit()

        steps = [
            {"tid": "T1", "op": "READ",  "key": "balance", "status": "ok"},
            {"tid": "T2", "op": "WRITE", "key": "balance", "status": "ok"},
        ]

        sc = SerializabilityChecker()
        sc.build_graph([t1, t2], steps=steps)

        self.assertIn("T2", sc.graph.get("T1", []))


class TestCycleDetection(unittest.TestCase):
    """Test DFS cycle detection on the precedence graph."""

    def test_acyclic_graph(self):
        sc = SerializabilityChecker()
        sc.graph = {"T1": ["T2"], "T2": []}
        self.assertFalse(sc.has_cycle())

    def test_cyclic_graph(self):
        sc = SerializabilityChecker()
        sc.graph = {"T1": ["T2"], "T2": ["T1"]}
        self.assertTrue(sc.has_cycle())

    def test_three_node_cycle(self):
        sc = SerializabilityChecker()
        sc.graph = {"T1": ["T2"], "T2": ["T3"], "T3": ["T1"]}
        self.assertTrue(sc.has_cycle())

    def test_empty_graph(self):
        sc = SerializabilityChecker()
        sc.graph = {}
        self.assertFalse(sc.has_cycle())


class TestCyclePath(unittest.TestCase):
    """Test finding the actual cycle path."""

    def test_find_two_node_cycle(self):
        sc = SerializabilityChecker()
        sc.graph = {"T1": ["T2"], "T2": ["T1"]}
        path = sc.find_cycle_path()
        self.assertIsNotNone(path)
        self.assertGreater(len(path), 2)  # at least 3 nodes (cycle + closing node)

    def test_find_no_cycle(self):
        sc = SerializabilityChecker()
        sc.graph = {"T1": ["T2"], "T2": []}
        path = sc.find_cycle_path()
        self.assertIsNone(path)


class TestPrintResult(unittest.TestCase):
    """Test print_result runs without error."""

    def test_serializable_print(self):
        import io
        sc = SerializabilityChecker()
        sc.graph = {"T1": ["T2"], "T2": []}
        old_stdout = sys.stdout
        sys.stdout = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
        try:
            sc.print_result()  # should not raise
        finally:
            sys.stdout = old_stdout

    def test_non_serializable_print(self):
        import io
        sc = SerializabilityChecker()
        sc.graph = {"T1": ["T2"], "T2": ["T1"]}
        old_stdout = sys.stdout
        sys.stdout = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
        try:
            sc.print_result()  # should not raise
        finally:
            sys.stdout = old_stdout


if __name__ == "__main__":
    unittest.main()
