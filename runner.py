# ─────────────────────────────────────
# SIMULATION RUNNER
# Extracted from streamlit_app.py for modularity
# ─────────────────────────────────────

from core.transaction import Transaction
from core.data_store import MVCCDataStore
from core.lock_manager import LockManager
from core.detector import AnomalyDetector
from core.serializable_checker import SerializabilityChecker


# ─────────────────────────────────────
# CORE RUNNER
# ─────────────────────────────────────
def run_scenario(config):
    db  = MVCCDataStore()
    lm  = LockManager(silent=True)
    det = AnomalyDetector()
    sc  = SerializabilityChecker()

    for key, value in config["initial_data"].items():
        db.init_data(key, value)

    isolation = config.get("isolation_level", "READ_COMMITTED")
    transactions = {}
    for i, t in enumerate(config["transactions"]):
        txn = Transaction(t["tid"], start_ts=i+1, isolation=isolation)
        transactions[t["tid"]] = txn
        lm.register(txn)

    steps = []
    step_num = 1
    deadlocks = []
    
    op_pointers = {t["tid"]: 0 for t in config["transactions"]}
    read_history = {}
    cumulative_wait_for = {}

    def add_step(step_data):
        step_data["wait_for_graph"] = lm.wait_for_graph.copy()
        for waiter, holder in lm.wait_for_graph.items():
            if waiter not in cumulative_wait_for:
                cumulative_wait_for[waiter] = set()
            cumulative_wait_for[waiter].add(holder)
        steps.append(step_data)

    while True:
        has_more = False
        progress_made = False
        
        for t_config in config["transactions"]:
            tid = t_config["tid"]
            txn = transactions[tid]
            ops = t_config["operations"]
            
            if txn.status in ["COMMITTED", "ABORTED", "WAITING"]:
                if txn.status == "WAITING":
                    has_more = True
                continue
                
            ptr = op_pointers[tid]
            if ptr >= len(ops):
                continue
                
            has_more = True
            op = ops[ptr]
            operation = op["op"].upper()
            lm.lock_log = []
            
            succeeded = False
            
            if operation == "READ":
                key = op["key"]
                if txn.isolation == "READ_UNCOMMITTED":
                    granted = True
                    ll = [{"message": f"🔓 {txn.tid} reads '{key}' without S lock (READ_UNCOMMITTED)", "level": "info"}]
                else:
                    granted = lm.acquire(txn, key, "S")
                    ll = lm.get_and_clear_log()
                    
                if isinstance(granted, tuple) and granted[0] == "DEADLOCK":
                    victim = granted[1]
                    cycle = lm.find_deadlock_cycle()
                    deadlocks.append({
                        "step": step_num,
                        "victim": victim.tid,
                        "cycle": cycle
                    })
                    db.rollback_transaction(victim)
                    lm.release(victim)
                    
                    if victim.tid != txn.tid:
                        granted = lm.acquire(txn, key, "S")
                        ll.extend(lm.get_and_clear_log())
                    else:
                        add_step({"step": step_num, "tid": txn.tid, "op": "READ", "key": key, "value": None, "status": "deadlock", "lock_table": lm.get_lock_table_str(), "lock_log": [e["message"] for e in ll]})
                        succeeded = True
                        op_pointers[tid] += 1
                        step_num += 1
                        progress_made = True
                        continue
                
                if granted:
                    val = db.read(key, txn)
                    if txn.tid not in read_history:
                        read_history[txn.tid] = {}
                    if key not in read_history[txn.tid]:
                        read_history[txn.tid][key] = []
                    read_history[txn.tid][key].append(val)
                    
                    if txn.isolation in ["READ_UNCOMMITTED", "READ_COMMITTED"]:
                        lm.release_shared_lock(txn, key)
                        ll.extend(lm.get_and_clear_log())
                        
                    add_step({"step": step_num, "tid": tid, "op": "READ", "key": key, "value": val, "status": "ok", "lock_table": lm.get_lock_table_str(), "lock_log": [e["message"] for e in ll]})
                    succeeded = True
                else:
                    add_step({"step": step_num, "tid": tid, "op": "READ", "key": key, "value": None, "status": "wait", "lock_table": lm.get_lock_table_str(), "note": "Blocked — another transaction holds a lock", "lock_log": [e["message"] for e in ll]})
                    succeeded = False
                    
            elif operation == "WRITE":
                key = op["key"]
                value = op["value"]
                txn.write_set[key] = value
                granted = lm.acquire(txn, key, "X")
                ll = lm.get_and_clear_log()
                
                if isinstance(granted, tuple) and granted[0] == "DEADLOCK":
                    victim = granted[1]
                    cycle = lm.find_deadlock_cycle()
                    deadlocks.append({
                        "step": step_num,
                        "victim": victim.tid,
                        "cycle": cycle
                    })
                    db.rollback_transaction(victim)
                    lm.release(victim)
                    
                    if victim.tid != txn.tid:
                        granted = lm.acquire(txn, key, "X")
                        ll.extend(lm.get_and_clear_log())
                    else:
                        add_step({"step": step_num, "tid": txn.tid, "op": "WRITE", "key": key, "value": value, "status": "deadlock", "lock_table": lm.get_lock_table_str(), "lock_log": [e["message"] for e in ll]})
                        succeeded = True
                        op_pointers[tid] += 1
                        step_num += 1
                        progress_made = True
                        continue
                
                if granted:
                    db.write(key, value, txn)
                    add_step({"step": step_num, "tid": tid, "op": "WRITE", "key": key, "value": value, "status": "ok", "lock_table": lm.get_lock_table_str(), "lock_log": [e["message"] for e in ll]})
                    succeeded = True
                else:
                    add_step({"step": step_num, "tid": tid, "op": "WRITE", "key": key, "value": value, "status": "wait", "lock_table": lm.get_lock_table_str(), "note": "Blocked — waiting for lock to be released", "lock_log": [e["message"] for e in ll]})
                    succeeded = False
                    
            elif operation == "COMMIT":
                db.commit_transaction(txn)
                lm.release(txn)
                ll = lm.get_and_clear_log()
                add_step({"step": step_num, "tid": tid, "op": "COMMIT", "key": "", "value": None, "status": "ok", "lock_table": lm.get_lock_table_str(), "lock_log": [e["message"] for e in ll]})
                succeeded = True
                
            elif operation == "ROLLBACK":
                db.rollback_transaction(txn)
                lm.release(txn)
                ll = lm.get_and_clear_log()
                add_step({"step": step_num, "tid": tid, "op": "ROLLBACK", "key": "", "value": None, "status": "wait", "lock_table": lm.get_lock_table_str(), "lock_log": [e["message"] for e in ll]})
                succeeded = True

            if succeeded:
                op_pointers[tid] += 1
                step_num += 1
                progress_made = True
                
        if not has_more:
            break
            
        if not progress_made:
            for tid, txn in list(transactions.items()):
                if txn.status in ["ACTIVE", "WAITING"]:
                    db.rollback_transaction(txn)
                    lm.release(txn)
                    add_step({"step": step_num, "tid": tid, "op": "ROLLBACK", "key": "", "value": None, "status": "wait", "lock_table": lm.get_lock_table_str(), "note": "Aborted — system deadlock resolution", "lock_log": []})
                    step_num += 1
            break

    txn_list = list(transactions.values())
    for i in range(len(txn_list)):
        for j in range(len(txn_list)):
            if i == j: continue
            t1, t2 = txn_list[i], txn_list[j]
            for key in config["initial_data"]:
                det.check_lost_update(t1, t2, key, db)
                
    for tid, history in read_history.items():
        txn = transactions[tid]
        for key, vals in history.items():
            if len(vals) > 1:
                det.check_non_repeatable_read(txn, key, vals[0], vals[-1])

    sc.build_graph(txn_list, steps=steps)
    cycle      = sc.has_cycle()
    cycle_path = sc.find_cycle_path()

    return {
        "steps":         steps,
        "anomalies":     det.anomalies,
        "serializable":  not cycle,
        "cycle_path":    cycle_path,
        "graph":         sc.graph,
        "deadlocks_list": deadlocks,
        "cumulative_wait_for": {w: list(h) for w, h in cumulative_wait_for.items()},
        "final_state":   {k: db.get_latest(k) for k in config["initial_data"]},
        "initial_state": config["initial_data"],
        "mvcc_versions": {k: db.data[k] for k in config["initial_data"]},
        "transactions":  list(transactions.keys()),
        "isolation":     isolation,
        "stats": {
            "total":     len(txn_list),
            "aborted":   sum(1 for t in txn_list if t.status == "ABORTED"),
            "committed": sum(1 for t in txn_list if t.status == "COMMITTED"),
            "conflicts": sum(1 for s in steps if s["status"] == "wait"),
            "deadlocks": sum(1 for s in steps if s["status"] == "deadlock"),
        }
    }


# ─────────────────────────────────────
# RUN ISOLATION SWITCHER
# ─────────────────────────────────────
def run_isolation_comparison(base_config):
    levels  = ["READ_UNCOMMITTED", "READ_COMMITTED", "REPEATABLE_READ", "SERIALIZABLE"]
    results = []

    for isolation in levels:
        db  = MVCCDataStore()
        lm  = LockManager(silent=True)
        det = AnomalyDetector()

        db.init_data("balance", 1000)
        T1 = Transaction("T1", start_ts=1, isolation=isolation)
        T2 = Transaction("T2", start_ts=5, isolation=isolation)
        lm.register(T1); lm.register(T2)

        lm.acquire(T1, "balance", "S")
        val = db.read("balance", T1)
        lm.acquire(T2, "balance", "X")
        db.write("balance", 800, T2)
        val2   = db.read("balance", T1)
        dirty  = T1.allows_dirty_read() and val2 == 800
        lm.release(T2); db.commit_transaction(T2)
        val3   = db.read("balance", T1)
        non_rep = T1.allows_non_repeatable_read() and val3 != val

        if isolation == "SERIALIZABLE":
            T1.start_ts = 10
            current = db.read("balance", T1)
            new_val = current - 300
        else:
            new_val = val - 300

        lm.acquire(T1, "balance", "X")
        db.write("balance", new_val, T1)
        T1.write_set["balance"] = new_val
        lm.release(T1); db.commit_transaction(T1)

        final = db.get_latest("balance")
        results.append({
            "isolation":     isolation,
            "dirty_read":    dirty,
            "non_repeatable": non_rep,
            "lost_update":   final != 500,
            "final_balance": final,
            "correct":       final == 500
        })

    return results
