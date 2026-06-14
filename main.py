from core.transaction import Transaction
from core.data_store import MVCCDataStore
from core.lock_manager import LockManager
from core.detector import AnomalyDetector
from core.serializable_checker import SerializabilityChecker
from logger.terminal_logger import Logger

# setup
db   = MVCCDataStore()
lm   = LockManager(silent=True)
det  = AnomalyDetector()
sc   = SerializabilityChecker()
log  = Logger()
db.init_data("balance", 1000)

# create two transactions
T1 = Transaction("T1", start_ts=1)
T2 = Transaction("T2", start_ts=2)

# ─────────────────────────────────────
# HEADER
# ─────────────────────────────────────
log.print_header("Banking — Concurrent Withdrawal", "READ COMMITTED")
log.print_initial_state("acc_101.balance", 1000)
log.print_section("EXECUTING STEPS")

# STEP 1: T1 reads balance
lm.acquire(T1, "balance", "S")
val = db.read("balance", T1)
log.log_step(1, "T1", "READ", "balance", val, "ok")

# STEP 2: T2 reads balance
lm.acquire(T2, "balance", "S")
val = db.read("balance", T2)
log.log_step(2, "T2", "READ", "balance", val, "ok")

# STEP 3: T2 wants to write (blocked)
granted = lm.acquire(T2, "balance", "X")
if granted:
    db.write("balance", 800, T2)
    log.log_step(3, "T2", "WRITE", "balance", 800, "ok")
else:
    log.log_step(3, "T2", "WRITE", "balance", 800, "wait")
    log.log_blocked("T2", "T1 holds S lock")

# STEP 4: T1 commits
T1.write_set["balance"] = 700
T1.commit()
lm.release(T1)
log.log_step(4, "T1", "COMMIT", "", None, "ok")
log.log_commit("T1")

# STEP 5: T2 retries write
granted = lm.acquire(T2, "balance", "X")
if granted:
    db.write("balance", 800, T2)
    log.log_step(5, "T2", "WRITE", "balance", 800, "ok")

# STEP 6: T2 commits
T2.commit()
lm.release(T2)
log.log_step(6, "T2", "COMMIT", "", None, "ok")
log.log_commit("T2")

# ─────────────────────────────────────
# ANOMALY CHECKS
# ─────────────────────────────────────
log.print_section("ANOMALY DETECTION")

lost = det.check_lost_update(T1, T2, "balance", db)
if lost:
    log.log_anomaly(
        "LOST UPDATE",
        f"Both T1 and T2 read balance=1000\n"
        f"T1 wrote 700 and committed\n"
        f"T2 wrote 800 and committed\n"
        f"T1's withdrawal of 300 is LOST",
        "Use REPEATABLE READ isolation level"
    )

old_val = T1.read_set.get("balance")
new_val = db.get_latest("balance")
nrr = det.check_non_repeatable_read(T1, "balance", old_val, new_val)
if nrr:
    log.log_anomaly(
        "NON-REPEATABLE READ",
        f"T1 read balance=1000 at STEP 1\n"
        f"T1 reads balance={new_val} now\n"
        f"Same query, different result",
        "Use REPEATABLE READ isolation level"
    )

# final state
log.print_final_state(
    actual=db.get_latest("balance"),
    expected=500,
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
sc.build_graph([T1, T2])
cycle_exists = sc.has_cycle()
cycle_path   = sc.find_cycle_path()
log.print_serializable_result(sc.graph, cycle_exists, cycle_path)