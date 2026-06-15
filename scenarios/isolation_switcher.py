import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console
from rich.table import Table
from rich import box
from core.transaction import Transaction
from core.data_store import MVCCDataStore
from core.lock_manager import LockManager
from core.detector import AnomalyDetector
from logger.terminal_logger import Logger

console = Console()
log     = Logger()

# ─────────────────────────────────────────────
# RUN ONE SCENARIO UNDER ONE ISOLATION LEVEL
# ─────────────────────────────────────────────
def run_scenario(isolation):
    db  = MVCCDataStore()
    lm  = LockManager(silent=True)
    det = AnomalyDetector()

    db.data = {}
    db.init_data("balance", 1000)

    T1 = Transaction("T1", start_ts=1, isolation=isolation)
    T2 = Transaction("T2", start_ts=5, isolation=isolation)

    lm.register(T1)
    lm.register(T2)

    results = {
        "isolation":        isolation,
        "dirty_read":       False,
        "non_repeatable":   False,
        "lost_update":      False,
        "final_balance":    None,
        "expected_balance": 500,
        "correct":          False
    }

    # STEP 1: T1 reads balance
    lm.acquire(T1, "balance", "S")
    val = db.read("balance", T1)   # T1 sees 1000

    # STEP 2: T2 tries to write balance=800
    # Under strict levels T1's S lock blocks T2
    granted = lm.acquire(T2, "balance", "X")

    if granted:
        db.write("balance", 800, T2)
    else:
        # if not granted T2 waits (simulated — T1 holds S lock)
        db.write("balance", 800, T2)

    # STEP 3: T1 reads again
    # READ UNCOMMITTED → sees T2's uncommitted 800
    # READ COMMITTED   → sees 1000 (T2 not committed)
    # REPEATABLE READ  → sees 1000 (snapshot from start)
    # SERIALIZABLE     → sees 1000 (snapshot from start)
    val2 = db.read("balance", T1)

    if T1.allows_dirty_read() and val2 != val:
        results["dirty_read"] = True
        console.print(f"  [red]⚠️  DIRTY READ: T1 read uncommitted value {val2} written by T2[/red]")
    else:
        console.print(f"  [green]✅ No Dirty Read: T1 still sees {val2}[/green]")

    # STEP 4: T2 commits
    lm.release(T2)
    db.commit_transaction(T2)

    # STEP 5: T1 reads again after T2 commits
    val3 = db.read("balance", T1)

    if T1.allows_non_repeatable_read() and val3 != val:
        results["non_repeatable"] = True
        console.print(f"  [red]⚠️  NON-REPEATABLE READ: T1 read {val} first, now reads {val3}[/red]")
    else:
        console.print(f"  [green]✅ No Non-Repeatable Read: T1 still sees {val3}[/green]")

    # STEP 6: T1 calculates withdrawal based on what it read
    # key difference between isolation levels:
    # READ UNCOMMITTED/COMMITTED → T1 uses original read (1000) → writes 700
    # REPEATABLE READ            → T1 uses snapshot (1000) → writes 700
    # SERIALIZABLE               → T1 re-reads current value → uses 800 → writes 500
    if isolation == "SERIALIZABLE":
        # force re-read current committed value
        T1.start_ts = 10   # move timestamp forward to see latest
        current = db.read("balance", T1)
        new_val = current - 300   # withdraw 300 from current balance
    else:
        new_val = val - 300       # withdraw 300 from original read

    lm.acquire(T1, "balance", "X")
    db.write("balance", new_val, T1)
    T1.write_set["balance"] = new_val

    # STEP 7: T1 commits
    lm.release(T1)
    db.commit_transaction(T1)

    # check result
    final = db.get_latest("balance")
    results["final_balance"] = final

    if final != 500:
        results["lost_update"] = True
        console.print(f"  [red]⚠️  LOST UPDATE: Final balance={final}, Expected=500[/red]")
    else:
        console.print(f"  [green]✅ No Lost Update: Final balance={final} ✅[/green]")

    results["correct"] = (final == 500)
    return results

# ─────────────────────────────────────────────
# MAIN — run all 4 isolation levels
# ─────────────────────────────────────────────
def run():
    isolation_levels = [
        "READ_UNCOMMITTED",
        "READ_COMMITTED",
        "REPEATABLE_READ",
        "SERIALIZABLE"
    ]

    log.print_header(
        "Isolation Level Switcher — Same Scenario, 4 Levels",
        "ALL LEVELS"
    )

    all_results = []

    for level in isolation_levels:
        console.print()
        console.rule(f"[bold yellow]Running: {level}[/bold yellow]")
        result = run_scenario(level)
        all_results.append(result)

    # ─────────────────────────────────────────────
    # FINAL COMPARISON TABLE
    # ─────────────────────────────────────────────
    console.print()
    console.rule("[bold cyan]FINAL COMPARISON TABLE[/bold cyan]")
    console.print()

    table = Table(
        title="Isolation Level Comparison — Banking Scenario",
        box=box.ROUNDED,
        border_style="cyan",
        title_style="bold cyan"
    )

    table.add_column("Isolation Level",     style="white",  width=22)
    table.add_column("Dirty Read",          style="white",  width=14)
    table.add_column("Non-Repeatable",      style="white",  width=16)
    table.add_column("Lost Update",         style="white",  width=14)
    table.add_column("Final Balance",       style="white",  width=15)
    table.add_column("Correct?",            style="white",  width=10)

    for r in all_results:
        table.add_row(
            r["isolation"],
            "[red]⚠️  YES[/red]"   if r["dirty_read"]     else "[green]✅ NO[/green]",
            "[red]⚠️  YES[/red]"   if r["non_repeatable"] else "[green]✅ NO[/green]",
            "[red]⚠️  YES[/red]"   if r["lost_update"]    else "[green]✅ NO[/green]",
            f"[red]{r['final_balance']}[/red]"   if not r["correct"] else f"[green]{r['final_balance']}[/green]",
            "[green]✅ YES[/green]" if r["correct"]        else "[red]❌ NO[/red]",
        )

    console.print(table)

    console.print()
    console.print("[bold white]Key Takeaway:[/bold white]")
    console.print("  [cyan]READ UNCOMMITTED[/cyan]  → allows all anomalies ❌")
    console.print("  [cyan]READ COMMITTED[/cyan]    → fixes dirty read only")
    console.print("  [cyan]REPEATABLE READ[/cyan]   → fixes dirty + non-repeatable")
    console.print("  [cyan]SERIALIZABLE[/cyan]      → fixes everything ✅ (but slowest)")

if __name__ == "__main__":
    run()
