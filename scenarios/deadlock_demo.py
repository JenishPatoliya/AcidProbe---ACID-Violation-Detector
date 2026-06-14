import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.transaction import Transaction
from core.data_store import MVCCDataStore
from core.lock_manager import LockManager
from core.detector import AnomalyDetector
from logger.terminal_logger import Logger

# ─────────────────────────────────────
# SETUP
# ─────────────────────────────────────
db  = MVCCDataStore()
lm  = LockManager()
det = AnomalyDetector()
log = Logger()

db.init_data("balance", 1000)
db.init_data("account", 500)

# two transactions
T1 = Transaction("T1", start_ts=1)
T2 = Transaction("T2", start_ts=2)

# register with lock manager for deadlock resolution
lm.register(T1)
lm.register(T2)

# ─────────────────────────────────────
# HEADER
# ─────────────────────────────────────
log.print_header(
    "Deadlock — T1 and T2 waiting for each other",
    "READ COMMITTED"
)

log.print_initial_state("balance", 1000)
log.print_initial_state("account", 500)
log.print_section("EXECUTING STEPS")

# ─────────────────────────────────────
# STEP 1: T1 locks 'balance'
# ─────────────────────────────────────
print("\n[STEP 1] T1 acquires lock on 'balance'")
lm.acquire(T1, "balance", "X")
val = db.read("balance", T1)
log.log_step(1, "T1", "READ", "balance", val, "ok")
lm.print_lock_table()

# ─────────────────────────────────────
# STEP 2: T2 locks 'account'
# ─────────────────────────────────────
print("\n[STEP 2] T2 acquires lock on 'account'")
lm.acquire(T2, "account", "X")
val = db.read("account", T2)
log.log_step(2, "T2", "READ", "account", val, "ok")
lm.print_lock_table()

# ─────────────────────────────────────
# STEP 3: T1 wants 'account' — BLOCKED by T2
# ─────────────────────────────────────
print("\n[STEP 3] T1 wants lock on 'account' (held by T2)")
result = lm.acquire(T1, "account", "X")
log.log_step(3, "T1", "READ", "account", None, "wait")
log.log_blocked("T1", "T2 holds X lock on 'account'")
lm.print_wait_graph()

# ─────────────────────────────────────
# STEP 4: T2 wants 'balance' — BLOCKED by T1 = DEADLOCK
# ─────────────────────────────────────
print("\n[STEP 4] T2 wants lock on 'balance' (held by T1)")
result = lm.acquire(T2, "balance", "X")

if result == "DEADLOCK":
    print("\n" + "💀"*25)
    print("  D E A D L O C K   D E T E C T E D")
    print("💀"*25)

    # show wait for graph
    lm.print_wait_graph()

    # find cycle
    cycle = lm.find_deadlock_cycle()
    cycle_str = " → ".join(cycle) if cycle else "unknown"

    log.log_anomaly(
        "DEADLOCK",
        f"Circular wait detected!\n"
        f"Cycle: {cycle_str}\n\n"
        f"T1 holds 'balance', waiting for 'account'\n"
        f"T2 holds 'account', waiting for 'balance'\n"
        f"Neither can proceed — system must intervene",
        "Abort youngest transaction (T2) and retry"
    )

    # ─────────────────────────────────
    # RESOLVE — abort youngest (T2)
    # ─────────────────────────────────
    log.print_section("DEADLOCK RESOLUTION")

    cycle_tids = [t for t in cycle if t in ["T1", "T2"]]
    victim = lm.resolve_deadlock(cycle_tids)

    print(f"\n  Victim     : {victim.tid} (youngest, started last)")
    print(f"  Action     : ROLLBACK all of {victim.tid}'s changes")
    print(f"  Status     : {victim.tid} → ABORTED ❌")
    log.log_rollback(victim.tid)
    lm.print_lock_table()

    # ─────────────────────────────────
    # T1 PROCEEDS after T2 aborted
    # ─────────────────────────────────
    log.print_section("AFTER RESOLUTION — T1 PROCEEDS")

    print("\n[STEP 5] T1 retries lock on 'account' (T2 released it)")
    result = lm.acquire(T1, "account", "X")
    if result == True:
        val = db.read("account", T1)
        log.log_step(5, "T1", "READ", "account", val, "ok")

    print("\n[STEP 6] T1 writes balance = 1200")
    db.write("balance", 1200, T1)
    log.log_step(6, "T1", "WRITE", "balance", 1200, "ok")

    print("\n[STEP 7] T1 writes account = 300")
    db.write("account", 300, T1)
    log.log_step(7, "T1", "WRITE", "account", 300, "ok")

    print("\n[STEP 8] T1 COMMITS")
    T1.commit()
    lm.release(T1)
    log.log_commit("T1")
    lm.print_lock_table()

# ─────────────────────────────────────
# FINAL STATE
# ─────────────────────────────────────
log.print_section("FINAL STATE")

print(f"\n  balance = {db.get_latest('balance')}")
print(f"  account = {db.get_latest('account')}")
print(f"\n  T1 status : {T1.status} ✅")
print(f"  T2 status : {T2.status} ❌ (aborted — will retry separately)")

log.print_versions("balance", db.data["balance"])
log.print_versions("account", db.data["account"])
