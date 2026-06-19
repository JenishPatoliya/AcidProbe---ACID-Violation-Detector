"""Integration tests — run preset scenarios through run_scenario() and verify results."""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from runner import run_scenario, run_isolation_comparison
from scenarios import SCENARIOS


class TestUPIPaymentScenario(unittest.TestCase):
    """Test the UPI Payment — Lost Update scenario."""

    def setUp(self):
        self.config = SCENARIOS["🏦 UPI Payment — Lost Update"].copy()
        self.result = run_scenario(self.config)

    def test_all_transactions_committed(self):
        self.assertEqual(self.result["stats"]["committed"], 2)
        self.assertEqual(self.result["stats"]["aborted"], 0)

    def test_lost_update_detected(self):
        anomaly_types = [a["type"] for a in self.result["anomalies"]]
        self.assertIn("LOST UPDATE", anomaly_types)

    def test_not_serializable(self):
        self.assertFalse(self.result["serializable"])

    def test_has_cycle_path(self):
        self.assertIsNotNone(self.result["cycle_path"])

    def test_final_state_is_one_of_the_writes(self):
        final = self.result["final_state"]["balance"]
        # One of the two writes wins: either 700 or 800
        self.assertIn(final, [700, 800])


class TestDeadlockScenario(unittest.TestCase):
    """Test the Bank Transfer — Deadlock scenario."""

    def setUp(self):
        self.config = SCENARIOS["💀 Bank Transfer — Deadlock"].copy()
        self.result = run_scenario(self.config)

    def test_one_aborted(self):
        self.assertEqual(self.result["stats"]["aborted"], 1)

    def test_deadlock_detected(self):
        self.assertGreater(self.result["stats"]["deadlocks"], 0)

    def test_deadlocks_list_populated(self):
        self.assertGreater(len(self.result["deadlocks_list"]), 0)

    def test_has_steps(self):
        self.assertGreater(len(self.result["steps"]), 0)


class TestTicketBookingScenario(unittest.TestCase):
    """Test the Ticket Booking — Overbooking scenario."""

    def setUp(self):
        self.config = SCENARIOS["✈️ Ticket Booking — Overbooking"].copy()
        self.result = run_scenario(self.config)

    def test_both_committed(self):
        self.assertEqual(self.result["stats"]["committed"], 2)

    def test_lost_update_detected(self):
        anomaly_types = [a["type"] for a in self.result["anomalies"]]
        self.assertIn("LOST UPDATE", anomaly_types)

    def test_final_seats_zero(self):
        self.assertEqual(self.result["final_state"]["seats"], 0)


class TestInventoryScenario(unittest.TestCase):
    """Test the Inventory — Overselling scenario."""

    def setUp(self):
        self.config = SCENARIOS["📦 Inventory — Overselling"].copy()
        self.result = run_scenario(self.config)

    def test_both_committed(self):
        self.assertEqual(self.result["stats"]["committed"], 2)

    def test_lost_update_detected(self):
        anomaly_types = [a["type"] for a in self.result["anomalies"]]
        self.assertIn("LOST UPDATE", anomaly_types)


class TestIsolationComparison(unittest.TestCase):
    """Test the isolation level comparison runner."""

    def test_returns_four_results(self):
        config = SCENARIOS["🔄 Isolation Levels — Side by Side"].copy()
        results = run_isolation_comparison(config)
        self.assertEqual(len(results), 4)

    def test_serializable_is_correct(self):
        config = SCENARIOS["🔄 Isolation Levels — Side by Side"].copy()
        results = run_isolation_comparison(config)
        serializable = next(r for r in results if r["isolation"] == "SERIALIZABLE")
        self.assertTrue(serializable["correct"])
        self.assertEqual(serializable["final_balance"], 500)

    def test_read_uncommitted_has_anomalies(self):
        config = SCENARIOS["🔄 Isolation Levels — Side by Side"].copy()
        results = run_isolation_comparison(config)
        ru = next(r for r in results if r["isolation"] == "READ_UNCOMMITTED")
        # READ_UNCOMMITTED should allow dirty reads
        self.assertTrue(ru["dirty_read"])


class TestCustomScenario(unittest.TestCase):
    """Test running a custom scenario config."""

    def test_simple_read_write_commit(self):
        config = {
            "scenario_name": "Simple Test",
            "isolation_level": "READ_COMMITTED",
            "initial_data": {"x": 100},
            "transactions": [
                {"tid": "T1", "operations": [
                    {"op": "READ", "key": "x"},
                    {"op": "WRITE", "key": "x", "value": 50},
                    {"op": "COMMIT"}
                ]}
            ]
        }
        result = run_scenario(config)
        self.assertEqual(result["stats"]["total"], 1)
        self.assertEqual(result["stats"]["committed"], 1)
        self.assertEqual(result["final_state"]["x"], 50)
        self.assertTrue(result["serializable"])

    def test_result_keys_present(self):
        config = {
            "scenario_name": "Key Check",
            "isolation_level": "READ_COMMITTED",
            "initial_data": {"a": 10},
            "transactions": [
                {"tid": "T1", "operations": [{"op": "READ", "key": "a"}, {"op": "COMMIT"}]}
            ]
        }
        result = run_scenario(config)
        expected_keys = [
            "steps", "anomalies", "serializable", "cycle_path", "graph",
            "deadlocks_list", "cumulative_wait_for", "final_state",
            "initial_state", "mvcc_versions", "transactions", "isolation", "stats"
        ]
        for key in expected_keys:
            self.assertIn(key, result, f"Missing key: {key}")


if __name__ == "__main__":
    unittest.main()
