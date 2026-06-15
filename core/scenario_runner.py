from core.transaction import Transaction
from core.data_store import MVCCDataStore
from core.lock_manager import LockManager
from core.detector import AnomalyDetector
from core.serializable_checker import SerializabilityChecker
from logger.terminal_logger import Logger
from rich.console import Console

console = Console()

class ScenarioRunner:
    def __init__(self):
        self.log   = Logger()
        self.steps = []      # tracks all steps for timeline

    def run(self, config):
        self.steps = []
        self.read_history = {}

        # setup
        db  = MVCCDataStore()
        lm  = LockManager(silent=True)
        det = AnomalyDetector()
        sc  = SerializabilityChecker()

        # load initial data
        for key, value in config["initial_data"].items():
            db.init_data(key, value)

        # create transactions
        isolation = config.get("isolation_level", "READ_COMMITTED")
        transactions = {}
        for i, t in enumerate(config["transactions"]):
            txn = Transaction(t["tid"], start_ts=i+1, isolation=isolation)
            transactions[t["tid"]] = txn
            lm.register(txn)

        # Track statistics
        stats = {
            "txn_executed": len(config["transactions"]),
            "txn_aborted": 0,
            "deadlocks_detected": 0,
            "lock_conflicts": 0,
            "total_wait_time": 0
        }

        # print header
        self.log.print_header(
            config.get("scenario_name", "Custom Scenario"),
            isolation
        )

        # print initial state
        console.print()
        console.print("[bold white]Initial Data:[/bold white]")
        for key, value in config["initial_data"].items():
            self.log.print_initial_state(key, value)

        self.log.print_section("EXECUTING STEPS")

        # Track operations pointer for each transaction config (program counter pacing)
        op_pointers = {t["tid"]: 0 for t in config["transactions"]}
        step_num = 1
        
        while True:
            # Check if any transaction has operations left to execute and is active or waiting
            has_more = False
            progress_made = False  # To detect and prevent infinite block loops
            
            # Increment wait steps for WAITING transactions
            for t_config in config["transactions"]:
                tid = t_config["tid"]
                txn = transactions[tid]
                if txn.status == "WAITING":
                    stats["total_wait_time"] += 1

            for t_config in config["transactions"]:
                tid = t_config["tid"]
                txn = transactions[tid]
                ops = t_config["operations"]
                
                # WAITING transactions are skipped in the pacing round
                if txn.status in ["COMMITTED", "ABORTED", "WAITING"]:
                    if txn.status == "WAITING":
                        has_more = True
                    continue
                    
                ptr = op_pointers[tid]
                if ptr >= len(ops):
                    continue
                    
                has_more = True
                op = ops[ptr]
                
                # Try to execute
                succeeded = self._execute_op(step_num, txn, op, db, lm, stats)
                if succeeded:
                    op_pointers[tid] += 1
                    step_num += 1
                    progress_made = True
                    # Clean up wait graph for others since this succeeded/finished
                    if txn.status in ["COMMITTED", "ABORTED"]:
                        waiters = [w for w, h in lm.wait_for_graph.items() if h == tid]
                        for w in waiters:
                            del lm.wait_for_graph[w]
            
            if not has_more:
                break
                
            # If a round completes and nobody makes progress (everyone is blocked)
            if not progress_made:
                console.print("\n[red]⚠️  DEADLOCK / BLOCK LIMIT: All active transactions are blocked. Terminating schedule execution.[/red]\n")
                # Rollback remaining active/waiting transactions
                for tid, txn in list(transactions.items()):
                    if txn.status in ["ACTIVE", "WAITING"]:
                        stats["txn_aborted"] += 1
                        restored = db.rollback_transaction(txn)
                        lm.release(txn)
                        console.print(f"    [red]❌ {txn.tid} ABORTED & ROLLED BACK (simulation ended)[/red]")
                        for rkey, old_v, new_v in restored:
                            console.print(f"      [red]🔄 Undo Log: Restored '{rkey}' from {old_v} to {new_v}[/red]")
                break

        # ─────────────────────────────────
        # TIMELINE VIEW
        # ─────────────────────────────────
        self.log.print_timeline(transactions, self.steps)

        # ─────────────────────────────────
        # ANOMALY CHECKS
        # ─────────────────────────────────
        self.log.print_section("ANOMALY DETECTION")
        txn_list = list(transactions.values())

        # check between all transaction pairs for lost updates
        for i in range(len(txn_list)):
            for j in range(len(txn_list)):
                if i == j:
                    continue
                t1 = txn_list[i]
                t2 = txn_list[j]
                for key in config["initial_data"]:
                    det.check_lost_update(t1, t2, key, db)

        # check non-repeatable reads from tracking history
        for tid, history in self.read_history.items():
            txn = transactions[tid]
            for key, vals in history.items():
                if len(vals) > 1:
                    det.check_non_repeatable_read(txn, key, vals[0], vals[-1])

        # anomaly report
        detected = [a["type"] for a in det.anomalies]
        self.log.print_anomaly_report(detected)

        # ─────────────────────────────────
        # FINAL STATE
        # ─────────────────────────────────
        self.log.print_section("FINAL STATE")
        for key in config["initial_data"]:
            latest = db.get_latest(key)
            console.print(f"  [cyan]{key}[/cyan] = [green]{latest}[/green]")

        # versions
        for key in config["initial_data"]:
            self.log.print_versions(key, db.data[key])

        # ─────────────────────────────────
        # SERIALIZABILITY
        # ─────────────────────────────────
        self.log.print_section("SERIALIZABILITY CHECK")
        sc.build_graph(txn_list, self.steps)
        cycle = sc.has_cycle()
        cycle_path = sc.find_cycle_path()
        self.log.print_serializable_result(sc.graph, cycle, cycle_path)

        # ─────────────────────────────────
        # STATISTICS & WAIT-FOR GRAPH REPORT
        # ─────────────────────────────────
        lm.print_wait_graph()
        self.log.print_statistics_report(stats)

    def _execute_op(self, step_num, txn, op, db, lm, stats):
        operation = op["op"].upper()

        if operation == "READ":
            key     = op["key"]
            # READ_UNCOMMITTED reads skip acquiring shared S locks to avoid blocking
            if txn.isolation == "READ_UNCOMMITTED":
                granted = True
                lock_log = [{"message": f"🔓 {txn.tid} reads '{key}' without S lock (READ_UNCOMMITTED)", "level": "info"}]
            else:
                granted = lm.acquire(txn, key, "S")
                lock_log = lm.get_and_clear_log()

            # Handle Deadlock
            if isinstance(granted, tuple) and granted[0] == "DEADLOCK":
                victim = granted[1]
                stats["txn_aborted"] += 1
                stats["deadlocks_detected"] += 1
                restored = db.rollback_transaction(victim)
                lm.release(victim)
                
                # Log rollback & undo logs
                self.log.log_anomaly("DEADLOCK", f"Circular wait detected. Deadlock victim {victim.tid} aborted.", "Rollback and release locks.")
                for rkey, old_v, new_v in restored:
                    console.print(f"  [red]🔄 Undo Log: Restored '{rkey}' from {old_v} to {new_v}[/red]")
                
                # Clean up wait graph for victim
                if victim.tid in lm.wait_for_graph:
                    del lm.wait_for_graph[victim.tid]
                waiters = [w for w, h in lm.wait_for_graph.items() if h == victim.tid]
                for w in waiters:
                    del lm.wait_for_graph[w]
                    
                # If current transaction wasn't the victim, retry lock acquisition!
                if victim.tid != txn.tid:
                    granted = lm.acquire(txn, key, "S")
                    lock_log.extend(lm.get_and_clear_log())
                else:
                    self.steps.append({
                        "step": step_num, "tid": txn.tid,
                        "op": "READ", "key": key,
                        "value": None, "status": "deadlock"
                    })
                    return True

            if granted:
                val = db.read(key, txn)
                
                # Populate read history
                if txn.tid not in self.read_history:
                    self.read_history[txn.tid] = {}
                if key not in self.read_history[txn.tid]:
                    self.read_history[txn.tid][key] = []
                self.read_history[txn.tid][key].append(val)

                # Under READ COMMITTED and READ UNCOMMITTED, release S-lock immediately
                if txn.isolation in ["READ_UNCOMMITTED", "READ_COMMITTED"]:
                    lm.release_shared_lock(txn, key)
                    lock_log.extend(lm.get_and_clear_log())

                self.log.log_step_with_locks(
                    step_num, txn.tid, "READ", key, val, "ok",
                    lock_log, lm.get_lock_table_str()
                )
                self.steps.append({
                    "step": step_num, "tid": txn.tid,
                    "op": "READ", "key": key,
                    "value": val, "status": "ok"
                })
                return True
            else:
                stats["lock_conflicts"] += 1
                self.log.log_step_with_locks(
                    step_num, txn.tid, "READ", key, None, "wait",
                    lock_log, lm.get_lock_table_str()
                )
                self.steps.append({
                    "step": step_num, "tid": txn.tid,
                    "op": "READ", "key": key,
                    "value": None, "status": "wait",
                    "note": "blocked"
                })
                return False

        elif operation == "WRITE":
            key     = op["key"]
            value   = op["value"]
            # Track attempted write
            txn.write_set[key] = value
            granted = lm.acquire(txn, key, "X")
            lock_log = lm.get_and_clear_log()

            # Handle Deadlock
            if isinstance(granted, tuple) and granted[0] == "DEADLOCK":
                victim = granted[1]
                stats["txn_aborted"] += 1
                stats["deadlocks_detected"] += 1
                restored = db.rollback_transaction(victim)
                lm.release(victim)
                
                # Log rollback & undo logs
                self.log.log_anomaly("DEADLOCK", f"Circular wait detected. Deadlock victim {victim.tid} aborted.", "Rollback and release locks.")
                for rkey, old_v, new_v in restored:
                    console.print(f"  [red]🔄 Undo Log: Restored '{rkey}' from {old_v} to {new_v}[/red]")
                
                # Clean up wait graph for victim
                if victim.tid in lm.wait_for_graph:
                    del lm.wait_for_graph[victim.tid]
                waiters = [w for w, h in lm.wait_for_graph.items() if h == victim.tid]
                for w in waiters:
                    del lm.wait_for_graph[w]
                    
                # If current transaction wasn't the victim, retry lock acquisition!
                if victim.tid != txn.tid:
                    granted = lm.acquire(txn, key, "X")
                    lock_log.extend(lm.get_and_clear_log())
                else:
                    self.steps.append({
                        "step": step_num, "tid": txn.tid,
                        "op": "WRITE", "key": key,
                        "value": value, "status": "deadlock"
                    })
                    return True

            if granted:
                db.write(key, value, txn)
                self.log.log_step_with_locks(
                    step_num, txn.tid, "WRITE", key, value, "ok",
                    lock_log, lm.get_lock_table_str()
                )
                self.steps.append({
                    "step": step_num, "tid": txn.tid,
                    "op": "WRITE", "key": key,
                    "value": value, "status": "ok"
                })
                return True
            else:
                stats["lock_conflicts"] += 1
                self.log.log_step_with_locks(
                    step_num, txn.tid, "WRITE", key, value, "wait",
                    lock_log, lm.get_lock_table_str()
                )
                self.steps.append({
                    "step": step_num, "tid": txn.tid,
                    "op": "WRITE", "key": key,
                    "value": value, "status": "wait",
                    "note": "blocked"
                })
                return False

        elif operation == "COMMIT":
            db.commit_transaction(txn)
            lm.release(txn)
            lock_log = lm.get_and_clear_log()
            self.log.log_step_with_locks(
                step_num, txn.tid, "COMMIT", "", None, "ok",
                lock_log, lm.get_lock_table_str()
            )
            self.log.log_commit(txn.tid)
            self.steps.append({
                "step": step_num, "tid": txn.tid,
                "op": "COMMIT", "key": "",
                "value": None, "status": "ok"
            })
            return True

        elif operation == "ROLLBACK":
            db.rollback_transaction(txn)
            lm.release(txn)
            lock_log = lm.get_and_clear_log()
            self.log.log_step_with_locks(
                step_num, txn.tid, "ROLLBACK", "", None, "wait",
                lock_log, lm.get_lock_table_str()
            )
            self.log.log_rollback(txn.tid)
            self.steps.append({
                "step": step_num, "tid": txn.tid,
                "op": "ROLLBACK", "key": "",
                "value": None, "status": "wait"
            })
            return True
            
        return True
