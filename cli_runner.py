import os
import sys
import json
from core.transaction import Transaction
from core.data_store import MVCCDataStore
from core.lock_manager import LockManager
from core.detector import AnomalyDetector
from core.serializable_checker import SerializabilityChecker
from logger.terminal_logger import Logger

from rich.console import Console
from rich.prompt import Prompt, IntPrompt, Confirm

console = Console()

def main():
    db = MVCCDataStore()
    lm = LockManager(silent=False)
    det = AnomalyDetector()
    sc = SerializabilityChecker()
    log = Logger()

    console.print("\n┌───────────────────────────────────────────────┐", style="bold cyan")
    console.print("│    AcidProbe — Interactive Scenario Runner    │", style="bold cyan")
    console.print("└───────────────────────────────────────────────┘\n", style="bold cyan")

    # 1. Database Seeding
    if db.data:
        console.print(f"[green]Loaded seed data from seed.json: {list(db.data.keys())}[/green]")
        use_seed = Confirm.ask("Would you like to use these loaded values?", default=True)
        if not use_seed:
            db.data = {}

    if not db.data:
        console.print("[bold yellow]--- Database Seeding ---[/bold yellow]")
        console.print("Enter record keys and initial values (e.g. 'balance' = 1000).")
        while True:
            key = Prompt.ask("Enter record key (or press Enter to finish seeding)").strip()
            if not key:
                if not db.data:
                    console.print("[red]Please seed at least one record key![/red]")
                    continue
                break
            val = IntPrompt.ask(f"Enter initial integer value for '{key}'")
            db.init_data(key, val)

    # 2. Transaction Configuration
    console.print("\n[bold yellow]--- Transaction Configuration ---[/bold yellow]")
    transactions = {}
    start_ts = 1
    while True:
        tid = Prompt.ask("Enter Transaction ID (e.g. T1, T2) (or press Enter to finish transaction setup)").strip()
        if not tid:
            if not transactions:
                console.print("[red]Please configure at least one transaction![/red]")
                continue
            break
        if tid in transactions:
            console.print(f"[red]Transaction '{tid}' already exists![/red]")
            continue
        
        isolation = Prompt.ask(
            f"Select isolation level for {tid}",
            choices=["READ_UNCOMMITTED", "READ_COMMITTED", "REPEATABLE_READ", "SERIALIZABLE"],
            default="READ_COMMITTED"
        )
        
        tx = Transaction(tid, start_ts=start_ts, isolation=isolation)
        transactions[tid] = tx
        lm.register(tx)
        start_ts += 1
        console.print(f"[green]Registered {tid} with isolation {tx.isolation}[/green]\n")

    # 3. Interactive Loop
    console.print("\n[bold yellow]--- Interactive Execution Mode ---[/bold yellow]")
    console.print("Simulate transaction steps interactively. Enter actions as they occur.")
    
    step_num = 1
    read_history = {} # tracks read values to check non-repeatable reads
    steps = [] # tracks successful steps for serializability checker
    
    while True:
        console.print("\n" + "═"*70, style="blue")
        console.print(f"[bold cyan]STEP {step_num}[/bold cyan]")
        
        # Display Transaction Status
        tx_states = [f"[bold cyan]{t.tid}[/bold cyan] ({t.status})" for t in transactions.values()]
        console.print(f"Transactions: {', '.join(tx_states)}")
        
        # Display Locks
        lm.print_lock_table()
        
        # Display Wait-For Graph if anyone is waiting
        if lm.wait_for_graph:
            lm.print_wait_graph()
            
        console.print("═"*70, style="blue")
        
        action = Prompt.ask(
            "Select operation",
            choices=["read", "write", "commit", "rollback", "show_versions", "finish"],
            default="read"
        )
        
        if action == "show_versions":
            for key in db.data:
                log.print_versions(key, db.data[key])
            continue
            
        if action == "finish":
            break
            
        active_tids = [tid for tid, tx in transactions.items() if tx.status == "ACTIVE"]
        if not active_tids:
            console.print("[red]No active transactions left (all are blocked/waiting or completed). Choose 'finish' to view reports or complete other waiting transactions.[/red]")
            continue
            
        tid = Prompt.ask("Select active transaction", choices=active_tids)
        tx = transactions[tid]
        
        if action == "read":
            key = Prompt.ask("Select key to read", choices=list(db.data.keys()))
            
            # READ_UNCOMMITTED skips shared locks
            if tx.isolation == "READ_UNCOMMITTED":
                granted = True
                console.print(f"[blue]🔓 {tx.tid} reads '{key}' without S lock (READ_UNCOMMITTED)[/blue]")
            else:
                granted = lm.acquire(tx, key, "S")

            # Deadlock detected
            if isinstance(granted, tuple) and granted[0] == "DEADLOCK":
                victim = granted[1]
                restored = db.rollback_transaction(victim)
                lm.release(victim)
                console.print(f"\n[bold red]💀 DEADLOCK RESOLVED! Victim {victim.tid} rolled back and aborted.[/bold red]")
                for rkey, old_v, new_v in restored:
                    console.print(f"  [red]🔄 Undo Log: Restored '{rkey}' from {old_v} to {new_v}[/red]")
                
                # Cleanup graph
                if victim.tid in lm.wait_for_graph:
                    del lm.wait_for_graph[victim.tid]
                waiters = [w for w, h in lm.wait_for_graph.items() if h == victim.tid]
                for w in waiters:
                    del lm.wait_for_graph[w]

            elif granted:
                val = db.read(key, tx)
                
                # Under READ COMMITTED and READ UNCOMMITTED, release S-lock immediately
                if tx.isolation in ["READ_UNCOMMITTED", "READ_COMMITTED"]:
                    lm.release_shared_lock(tx, key)

                log.log_step(step_num, tid, "READ", key, val, "ok")
                steps.append({
                    "step": step_num,
                    "tid": tid,
                    "op": "READ",
                    "key": key,
                    "value": val,
                    "status": "ok"
                })
                
                # Check for dirty read anomaly immediately
                for other_tid, other_tx in transactions.items():
                    if other_tid != tid:
                        det.check_dirty_read(tx, other_tx, key, val)
                
                # Record history for non-repeatable read check
                if tid not in read_history:
                    read_history[tid] = {}
                if key not in read_history[tid]:
                    read_history[tid][key] = []
                read_history[tid][key].append(val)
            else:
                log.log_step(step_num, tid, "READ", key, None, "wait")
                log.log_blocked(tid, f"X lock held by another transaction on '{key}'")
                
        elif action == "write":
            key = Prompt.ask("Select key to write", choices=list(db.data.keys()))
            val = IntPrompt.ask(f"Enter new value to write to '{key}'")
            # Track attempted write
            tx.write_set[key] = val
            granted = lm.acquire(tx, key, "X")

            # Deadlock detected
            if isinstance(granted, tuple) and granted[0] == "DEADLOCK":
                victim = granted[1]
                restored = db.rollback_transaction(victim)
                lm.release(victim)
                console.print(f"\n[bold red]💀 DEADLOCK RESOLVED! Victim {victim.tid} rolled back and aborted.[/bold red]")
                for rkey, old_v, new_v in restored:
                    console.print(f"  [red]🔄 Undo Log: Restored '{rkey}' from {old_v} to {new_v}[/red]")
                
                # Cleanup graph
                if victim.tid in lm.wait_for_graph:
                    del lm.wait_for_graph[victim.tid]
                waiters = [w for w, h in lm.wait_for_graph.items() if h == victim.tid]
                for w in waiters:
                    del lm.wait_for_graph[w]

            elif granted:
                db.write(key, val, tx)
                log.log_step(step_num, tid, "WRITE", key, val, "ok")
                steps.append({
                    "step": step_num,
                    "tid": tid,
                    "op": "WRITE",
                    "key": key,
                    "value": val,
                    "status": "ok"
                })
            else:
                log.log_step(step_num, tid, "WRITE", key, val, "wait")
                log.log_blocked(tid, f"Lock conflict on '{key}'")
                
        elif action == "commit":
            db.commit_transaction(tx)
            lm.release(tx)
            # Clean up wait-for graph entries waiting on this transaction
            waiters_to_remove = [waiter for waiter, holder in lm.wait_for_graph.items() if holder == tid]
            for waiter in waiters_to_remove:
                del lm.wait_for_graph[waiter]
            log.log_step(step_num, tid, "COMMIT", "", None, "ok")
            log.log_commit(tid)
            console.print(f"[green]Transaction {tid} committed. Released locks. Waiters can retry now.[/green]")
            
        elif action == "rollback":
            restored = db.rollback_transaction(tx)
            lm.release(tx)
            # Clean up wait-for graph entries waiting on this transaction
            waiters_to_remove = [waiter for waiter, holder in lm.wait_for_graph.items() if holder == tid]
            for waiter in waiters_to_remove:
                del lm.wait_for_graph[waiter]
            log.log_step(step_num, tid, "ROLLBACK", "", None, "ok")
            log.log_rollback(tid)
            console.print(f"[red]Transaction {tid} aborted & rolled back. Released locks. Waiters can retry now.[/red]")
            for rkey, old_v, new_v in restored:
                console.print(f"  [red]🔄 Undo Log: Restored '{rkey}' from {old_v} to {new_v}[/red]")
            
        step_num += 1

    # 4. Final Reports
    console.print("\n[bold yellow]────────────────────────────── ANOMALY DETECTION ──────────────────────────────[/bold yellow]")
    
    # Run dynamic anomaly checks at the end of the simulation
    for key in db.data:
        # Check Lost Updates between all pairs of committed transactions
        txs_list = list(transactions.values())
        for i in range(len(txs_list)):
            for j in range(i + 1, len(txs_list)):
                det.check_lost_update(txs_list[i], txs_list[j], key, db)
                det.check_lost_update(txs_list[j], txs_list[i], key, db)
                
    # Check Non-Repeatable Reads from tracking history
    for tid, history in read_history.items():
        tx = transactions[tid]
        for key, vals in history.items():
            if len(vals) > 1:
                det.check_non_repeatable_read(tx, key, vals[0], vals[-1])

    # Print Anomaly Report Table
    detected_anomalies = [a["type"] for a in det.anomalies]
    log.print_anomaly_report(detected_anomalies)

    # Print Version Chain for each key
    for key in db.data:
        log.print_versions(key, db.data[key])

    # 5. Conflict Serializability Check
    console.print("\n[bold yellow]──────────────────────────── SERIALIZABILITY CHECK ────────────────────────────[/bold yellow]")
    sc.build_graph(list(transactions.values()), steps)
    cycle_exists = sc.has_cycle()
    cycle_path = sc.find_cycle_path()
    log.print_serializable_result(sc.graph, cycle_exists, cycle_path)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[red]Interactive runner aborted.[/red]")
        sys.exit(0)
