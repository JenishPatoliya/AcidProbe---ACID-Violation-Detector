from core.transaction import Transaction
from core.data_store import MVCCDataStore
from core.lock_manager import LockManager
from core.detector import AnomalyDetector
from core.serializable_checker import SerializabilityChecker
from logger.terminal_logger import Logger

def run():
    # setup
    db   = MVCCDataStore()
    lm   = LockManager(silent=True)
    det  = AnomalyDetector()
    sc   = SerializabilityChecker()
    log  = Logger()
    
    # We clear seed.json loaded values to force standard banking scenario defaults for Option 1
    # since we want Option 1 to run the hardcoded banking demo.
    db.data = {}
    db.init_data("balance", 1000)

    init_bal = db.get_latest("balance")
    t1_write_val = init_bal - 300
    t2_write_val = init_bal - 200
    expected_val = init_bal - 500

    # create two transactions
    T1 = Transaction("T1", start_ts=1)
    T2 = Transaction("T2", start_ts=2)

    # ─────────────────────────────────────
    # HEADER
    # ─────────────────────────────────────
    log.print_header("Banking — Concurrent Withdrawal", "READ COMMITTED")
    log.print_initial_state("acc_101.balance", init_bal)
    log.print_section("EXECUTING STEPS")

    steps = []

    # STEP 1: T1 reads balance
    lm.acquire(T1, "balance", "S")
    val = db.read("balance", T1)
    # Release S-lock immediately for READ COMMITTED
    lm.release_shared_lock(T1, "balance")
    log.log_step(1, "T1", "READ", "balance", val, "ok")
    steps.append({"step": 1, "tid": "T1", "op": "READ", "key": "balance", "value": val, "status": "ok"})

    # STEP 2: T2 reads balance
    lm.acquire(T2, "balance", "S")
    val = db.read("balance", T2)
    # Release S-lock immediately for READ COMMITTED
    lm.release_shared_lock(T2, "balance")
    log.log_step(2, "T2", "READ", "balance", val, "ok")
    steps.append({"step": 2, "tid": "T2", "op": "READ", "key": "balance", "value": val, "status": "ok"})

    # STEP 3: T2 wants to write
    granted = lm.acquire(T2, "balance", "X")
    if granted:
        db.write("balance", t2_write_val, T2)
        log.log_step(3, "T2", "WRITE", "balance", t2_write_val, "ok")
        steps.append({"step": 3, "tid": "T2", "op": "WRITE", "key": "balance", "value": t2_write_val, "status": "ok"})
    else:
        log.log_step(3, "T2", "WRITE", "balance", t2_write_val, "wait")
        log.log_blocked("T2", "T1 holds S lock")
        steps.append({"step": 3, "tid": "T2", "op": "WRITE", "key": "balance", "value": t2_write_val, "status": "wait"})

    # STEP 4: T1 commits (with its write intent)
    T1.write_set["balance"] = t1_write_val
    T1.commit()
    lm.release(T1)
    log.log_step(4, "T1", "COMMIT", "", None, "ok")
    log.log_commit("T1")
    steps.append({"step": 4, "tid": "T1", "op": "COMMIT", "key": "", "value": None, "status": "ok"})
    steps.append({"step": 4, "tid": "T1", "op": "WRITE", "key": "balance", "value": t1_write_val, "status": "ok"})

    # STEP 5: T2 retries/executes write (if it was blocked, otherwise redundant but safe)
    granted = lm.acquire(T2, "balance", "X")
    if granted:
        db.write("balance", t2_write_val, T2)
        log.log_step(5, "T2", "WRITE", "balance", t2_write_val, "ok")
        steps.append({"step": 5, "tid": "T2", "op": "WRITE", "key": "balance", "value": t2_write_val, "status": "ok"})

    # STEP 6: T2 commits
    T2.commit()
    lm.release(T2)
    log.log_step(6, "T2", "COMMIT", "", None, "ok")
    log.log_commit("T2")
    steps.append({"step": 6, "tid": "T2", "op": "COMMIT", "key": "", "value": None, "status": "ok"})

    # ─────────────────────────────────────
    # ANOMALY CHECKS
    # ─────────────────────────────────────
    log.print_section("ANOMALY DETECTION")

    lost = det.check_lost_update(T1, T2, "balance", db)
    if lost:
        log.log_anomaly(
            "LOST UPDATE",
            f"Both T1 and T2 read balance={init_bal}\n"
            f"T1 wrote {t1_write_val} and committed\n"
            f"T2 wrote {t2_write_val} and committed\n"
            f"T1's withdrawal of 300 is LOST",
            "Use REPEATABLE READ isolation level"
        )

    # T1 only read "balance" once in this schedule, so no non-repeatable read occurred
    nrr = False

    # final state
    log.print_final_state(
        actual=db.get_latest("balance"),
        expected=expected_val,
        key="acc_101.balance"
    )

    # anomaly report table
    detected = [a["type"] for a in det.anomalies]
    log.print_anomaly_report(detected)

    # versions table
    log.print_versions("balance", db.data["balance"])

    # ─────────────────────────────────────
    # SERIALIZABILITY
    # ─────────────────────────────────────
    log.print_section("SERIALIZABILITY CHECK")
    sc.build_graph([T1, T2], steps)
    cycle_exists = sc.has_cycle()
    cycle_path   = sc.find_cycle_path()
    log.print_serializable_result(sc.graph, cycle_exists, cycle_path)

if __name__ == "__main__":
    run()
