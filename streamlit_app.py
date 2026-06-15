import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import json
import time

# ─────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────
st.set_page_config(
    page_title="AcidProbe",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────
# DESIGN TOKENS
# Colors: electric blue, vivid purple, emerald, amber, coral
# Type: Space Grotesk display, Inter body, JetBrains Mono data
# Signature: animated transaction "swim lanes" with color-coded T1/T2
# ─────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    color: #f1f5f9;
}

.stApp { background: #070b14; }

/* ── SIDEBAR ── */
section[data-testid="stSidebar"] {
    background: #0d1526;
    border-right: 1px solid #1e293b;
}

section[data-testid="stSidebar"] * { color: #cbd5e1 !important; }

/* ── HEADER ── */
.acid-header {
    background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%);
    border: 1px solid #312e81;
    border-radius: 20px;
    padding: 40px 32px 32px;
    margin-bottom: 32px;
    text-align: center;
    position: relative;
    overflow: hidden;
}

.acid-header::before {
    content: '';
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: radial-gradient(ellipse at center, rgba(99,102,241,0.08) 0%, transparent 60%);
    pointer-events: none;
}

.acid-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 2.8rem;
    font-weight: 700;
    letter-spacing: -1.5px;
    background: linear-gradient(90deg, #818cf8, #c084fc, #f472b6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0 0 8px;
}

.acid-tagline {
    color: #64748b;
    font-size: 1rem;
    font-weight: 400;
    letter-spacing: 0.3px;
}

/* ── CONCEPT PILL ── */
.concept-pill {
    display: inline-block;
    background: rgba(99,102,241,0.12);
    border: 1px solid rgba(99,102,241,0.3);
    border-radius: 20px;
    padding: 4px 14px;
    font-size: 0.75rem;
    font-weight: 600;
    color: #a5b4fc;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    margin: 4px 3px;
}

/* ── STAT CARDS ── */
.stat-row { display: flex; gap: 12px; margin: 24px 0; }

.stat-card {
    flex: 1;
    border-radius: 14px;
    padding: 20px 16px;
    text-align: center;
    border: 1px solid;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.stat-card:hover {
    transform: translateY(-3px);
}

.stat-card.blue  { background: #1e3a5f22; border-color: #3b82f655; }
.stat-card.green { background: #06402822; border-color: #10b98155; }
.stat-card.red   { background: #45101022; border-color: #ef444455; }
.stat-card.amber { background: #45350022; border-color: #f59e0b55; }
.stat-card.pink  { background: #45104022; border-color: #ec489955; }

.stat-num  { font-family: 'Space Grotesk', sans-serif; font-size: 2.4rem; font-weight: 700; margin: 4px 0; line-height: 1; }
.stat-lbl  { font-size: 0.72rem; font-weight: 600; text-transform: uppercase; letter-spacing: 1.2px; color: #64748b; }
.stat-icon { font-size: 1.4rem; margin-bottom: 6px; }

.blue  .stat-num { color: #60a5fa; }
.green .stat-num { color: #34d399; }
.red   .stat-num { color: #f87171; }
.amber .stat-num { color: #fbbf24; }
.pink  .stat-num { color: #f472b6; }

/* ── SECTION HEADER ── */
.section-head {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.1rem;
    font-weight: 600;
    color: #e2e8f0;
    margin: 28px 0 14px;
    padding-bottom: 10px;
    border-bottom: 1px solid #1e293b;
    display: flex;
    align-items: center;
    gap: 8px;
}

/* ── WHAT IS THIS BOX ── */
.explain-box {
    background: #0d1526;
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 18px 20px;
    margin: 10px 0 18px;
    font-size: 0.9rem;
    color: #94a3b8;
    line-height: 1.7;
}

.explain-box strong { color: #c7d2fe; }

/* ── STEP CARDS ── */
.step-wrap { margin: 6px 0; }

.step-card {
    border-radius: 10px;
    padding: 12px 16px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    border: 1px solid;
    transition: transform 0.15s ease;
}

.step-card:hover { transform: translateX(3px); }

.step-ok {
    background: #052e1c;
    border-color: #10b98133;
}

.step-wait {
    background: #2d1a00;
    border-color: #f59e0b33;
}

.step-deadlock {
    background: #2d0808;
    border-color: #ef444433;
}

.step-meta { font-size: 11px; color: #475569; margin-top: 6px; }
.step-lock { font-size: 11px; color: #3b82f6; margin-top: 3px; }

/* ── TIMELINE TABLE ── */
.tl-table { width: 100%; border-collapse: collapse; font-family: 'JetBrains Mono', monospace; font-size: 12.5px; }
.tl-table th { background: #0d1526; color: #64748b; padding: 10px 14px; text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; border-bottom: 1px solid #1e293b; }
.tl-table td { padding: 9px 14px; border-bottom: 1px solid #0d1526; }
.tl-table tr:hover td { background: #0d152699; }

.cell-t1   { color: #60a5fa; font-weight: 600; }
.cell-t2   { color: #c084fc; font-weight: 600; }
.cell-t3   { color: #34d399; font-weight: 600; }
.cell-t4   { color: #fbbf24; font-weight: 600; }
.cell-pipe { color: #1e293b; }
.cell-wait { color: #f59e0b; }
.cell-dead { color: #ef4444; }

/* ── ANOMALY CARDS ── */
.anomaly-detected {
    background: #1a0a0a;
    border: 1px solid #ef444444;
    border-left: 4px solid #ef4444;
    border-radius: 10px;
    padding: 16px 18px;
    margin: 8px 0;
}

.anomaly-clean {
    background: #0a1a0e;
    border: 1px solid #10b98144;
    border-left: 4px solid #10b981;
    border-radius: 10px;
    padding: 16px 18px;
    margin: 8px 0;
}

.anomaly-title { font-family: 'Space Grotesk', sans-serif; font-weight: 600; font-size: 0.95rem; margin-bottom: 4px; }
.anomaly-desc  { font-size: 0.82rem; color: #94a3b8; line-height: 1.6; }
.anomaly-fix   { font-size: 0.78rem; color: #60a5fa; margin-top: 8px; }

/* ── SERIALIZABLE ── */
.serial-ok {
    background: #0a1a0e;
    border: 1px solid #10b981;
    border-radius: 12px;
    padding: 20px;
    text-align: center;
}

.serial-fail {
    background: #1a0a0a;
    border: 1px solid #ef4444;
    border-radius: 12px;
    padding: 20px;
    text-align: center;
}

.serial-title { font-family: 'Space Grotesk', sans-serif; font-size: 1.1rem; font-weight: 600; margin-bottom: 6px; }
.serial-desc  { font-size: 0.85rem; color: #94a3b8; line-height: 1.6; }
.serial-cycle { font-family: 'JetBrains Mono', monospace; font-size: 0.9rem; color: #ef4444; margin: 8px 0; }

/* ── MVCC TABLE ── */
.mvcc-key { font-family: 'Space Grotesk', sans-serif; font-size: 1rem; font-weight: 600; color: #c7d2fe; margin: 14px 0 8px; }
.mvcc-table { width: 100%; border-collapse: collapse; font-family: 'JetBrains Mono', monospace; font-size: 12.5px; margin-bottom: 16px; }
.mvcc-table th { background: #0d1526; color: #64748b; padding: 8px 14px; text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; }
.mvcc-table td { padding: 8px 14px; border-bottom: 1px solid #0d1526; }
.mvcc-committed { color: #34d399; }
.mvcc-uncommitted { color: #f59e0b; }

/* ── FINAL STATE ── */
.final-state-card {
    background: #0d1526;
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin: 8px 0;
}

.final-key { font-family: 'Space Grotesk', sans-serif; font-weight: 600; color: #94a3b8; }
.final-val { font-family: 'Space Grotesk', sans-serif; font-size: 2rem; font-weight: 700; color: #34d399; }

/* ── ISOLATION COMPARISON ── */
.iso-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.iso-table th { background: #0d1526; color: #64748b; padding: 10px 14px; text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; border-bottom: 2px solid #1e293b; }
.iso-table td { padding: 12px 14px; border-bottom: 1px solid #0f172a; font-family: 'JetBrains Mono', monospace; }
.iso-table tr:hover td { background: #0d152644; }
.iso-yes { color: #f87171; }
.iso-no  { color: #34d399; }
.iso-level { color: #a5b4fc; font-weight: 600; }
.iso-correct { color: #34d399; font-weight: 700; }
.iso-wrong   { color: #f87171; }

/* ── TABS ── */
.stTabs [data-baseweb="tab-list"] { background: #0d1526; border-radius: 10px; padding: 4px; gap: 4px; }
.stTabs [data-baseweb="tab"] { background: transparent; color: #64748b; border-radius: 8px; padding: 8px 18px; font-family: 'Inter', sans-serif; font-size: 0.85rem; font-weight: 500; }
.stTabs [aria-selected="true"] { background: #1e293b !important; color: #e2e8f0 !important; }

/* ── SIDEBAR BUTTON ── */
.stButton > button {
    background: linear-gradient(135deg, #4f46e5, #7c3aed);
    color: white;
    border: none;
    border-radius: 10px;
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 600;
    font-size: 0.95rem;
    padding: 12px;
    width: 100%;
    transition: opacity 0.2s;
    cursor: pointer;
}

.stButton > button:hover { opacity: 0.88; }

/* ── DIVIDER ── */
hr { border-color: #1e293b; margin: 24px 0; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────
# TRANSACTION COLOR MAP
# ─────────────────────────────────────
TXN_COLORS = {
    "T1": ("cell-t1", "#60a5fa"),
    "T2": ("cell-t2", "#c084fc"),
    "T3": ("cell-t3", "#34d399"),
    "T4": ("cell-t4", "#fbbf24"),
}

def txn_color(tid):
    return TXN_COLORS.get(tid, ("cell-t1", "#60a5fa"))

# ─────────────────────────────────────
# ANOMALY META
# ─────────────────────────────────────
ANOMALY_META = {
    "DIRTY READ": {
        "icon": "💧",
        "what": "A transaction reads data written by another transaction that hasn't committed yet. If that transaction rolls back, the data read never existed.",
        "example": "T1 reads balance=800 that T2 wrote. T2 rolls back. T1 made decisions on data that never existed.",
        "fix": "Use READ COMMITTED isolation — only read committed data."
    },
    "NON-REPEATABLE READ": {
        "icon": "🔁",
        "what": "A transaction reads the same row twice and gets different values because another transaction modified it in between.",
        "example": "T1 reads balance=1000, then T2 changes it to 800 and commits. T1 reads again and gets 800.",
        "fix": "Use REPEATABLE READ isolation — lock rows you've already read."
    },
    "LOST UPDATE": {
        "icon": "🗑️",
        "what": "Two transactions read the same value, both calculate updates, and both write back. The second write overwrites the first, so the first update is permanently lost.",
        "example": "T1 reads 1000, writes 700. T2 reads 1000 (stale), writes 800. T1's -300 withdrawal is gone.",
        "fix": "Use REPEATABLE READ isolation — hold read lock until commit."
    },
    "PHANTOM READ": {
        "icon": "👻",
        "what": "A transaction runs the same range query twice and gets different rows because another transaction inserted or deleted rows in between.",
        "example": "T1 counts seats=3. T2 adds a new seat. T1 counts again and gets 4.",
        "fix": "Use SERIALIZABLE isolation — lock the entire range."
    }
}

# ─────────────────────────────────────
# CORE RUNNER
# ─────────────────────────────────────
def run_scenario(config):
    from core.transaction import Transaction
    from core.data_store import MVCCDataStore
    from core.lock_manager import LockManager
    from core.detector import AnomalyDetector
    from core.serializable_checker import SerializabilityChecker

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
    from core.transaction import Transaction
    from core.data_store import MVCCDataStore
    from core.lock_manager import LockManager
    from core.detector import AnomalyDetector

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

# ─────────────────────────────────────
# PREDEFINED SCENARIOS
# ─────────────────────────────────────
SCENARIOS = {
    "🏦 UPI Payment — Lost Update": {
        "scenario_name": "UPI Payment Conflict",
        "what_is_this": "Rahul and Priya both send money from the same account at the same time. Rahul sends ₹300 (expects ₹700 left), Priya sends ₹200 (expects ₹800 left). Because they both read the original ₹1000 before either commits, one update overwrites the other — money is lost.",
        "concepts": ["Lost Update", "Non-Repeatable Read", "S Lock", "X Lock", "Lock Conflict"],
        "isolation_level": "READ_COMMITTED",
        "initial_data": {"balance": 1000},
        "transactions": [
            {"tid": "T1", "operations": [
                {"op": "READ",  "key": "balance"},
                {"op": "WRITE", "key": "balance", "value": 700},
                {"op": "COMMIT"}
            ]},
            {"tid": "T2", "operations": [
                {"op": "READ",  "key": "balance"},
                {"op": "WRITE", "key": "balance", "value": 800},
                {"op": "COMMIT"}
            ]}
        ]
    },
    "💀 Bank Transfer — Deadlock": {
        "scenario_name": "Bank Transfer Deadlock",
        "what_is_this": "T1 locks 'balance' and needs 'savings'. T2 locks 'savings' and needs 'balance'. Neither can proceed. They wait for each other forever — this is a deadlock. The system detects the cycle and automatically aborts the younger transaction.",
        "concepts": ["Deadlock", "Wait-For Graph", "DFS Cycle Detection", "Auto Resolution", "X Lock"],
        "isolation_level": "READ_COMMITTED",
        "initial_data": {"balance": 1000, "savings": 500},
        "transactions": [
            {"tid": "T1", "operations": [
                {"op": "READ",  "key": "balance"},
                {"op": "WRITE", "key": "balance", "value": 800},
                {"op": "READ",  "key": "savings"},
                {"op": "COMMIT"}
            ]},
            {"tid": "T2", "operations": [
                {"op": "READ",  "key": "savings"},
                {"op": "WRITE", "key": "savings", "value": 300},
                {"op": "READ",  "key": "balance"},
                {"op": "COMMIT"}
            ]}
        ]
    },
    "✈️ Ticket Booking — Overbooking": {
        "scenario_name": "Flight Ticket Overbooking",
        "what_is_this": "Only 1 seat left. Two booking agents check simultaneously — both see 1 seat available. Both confirm the booking. Both write 'seats = 0'. The airline has now sold the same seat twice — classic overbooking due to a race condition.",
        "concepts": ["Lost Update", "Race Condition", "Phantom Read", "S Lock", "X Lock"],
        "isolation_level": "READ_COMMITTED",
        "initial_data": {"seats": 1},
        "transactions": [
            {"tid": "T1", "operations": [
                {"op": "READ",  "key": "seats"},
                {"op": "WRITE", "key": "seats", "value": 0},
                {"op": "COMMIT"}
            ]},
            {"tid": "T2", "operations": [
                {"op": "READ",  "key": "seats"},
                {"op": "WRITE", "key": "seats", "value": 0},
                {"op": "COMMIT"}
            ]}
        ]
    },
    "📦 Inventory — Overselling": {
        "scenario_name": "Inventory Concurrent Checkout",
        "what_is_this": "5 items in stock. Two customers checkout simultaneously. Customer 1 buys 2 items (expects stock=3). Customer 2 buys 3 items (expects stock=2). But they both read 5 before either commits — final stock becomes 2, not 0. 3 items were oversold.",
        "concepts": ["Lost Update", "Non-Repeatable Read", "MVCC", "Concurrency"],
        "isolation_level": "READ_COMMITTED",
        "initial_data": {"stock": 5},
        "transactions": [
            {"tid": "T1", "operations": [
                {"op": "READ",  "key": "stock"},
                {"op": "WRITE", "key": "stock", "value": 3},
                {"op": "COMMIT"}
            ]},
            {"tid": "T2", "operations": [
                {"op": "READ",  "key": "stock"},
                {"op": "WRITE", "key": "stock", "value": 2},
                {"op": "COMMIT"}
            ]}
        ]
    },
    "🔄 Isolation Levels — Side by Side": {
        "scenario_name": "Isolation Level Comparison",
        "what_is_this": "The same banking scenario runs under all 4 isolation levels. Watch how each level prevents different anomalies — from READ UNCOMMITTED (allows everything) to SERIALIZABLE (prevents everything). The final balance tells you which level is correct.",
        "concepts": ["READ UNCOMMITTED", "READ COMMITTED", "REPEATABLE READ", "SERIALIZABLE", "Isolation"],
        "isolation_level": "ALL",
        "initial_data": {"balance": 1000},
        "transactions": []
    }
}

# ─────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────
with st.sidebar:
    st.markdown("## 🔬 AcidProbe")
    st.markdown("<p style='color:#475569; font-size:0.8rem;'>ACID Violation Detector</p>", unsafe_allow_html=True)
    st.markdown("---")

    mode = st.radio("Input Mode", ["Preset Scenario", "Custom JSON"], index=0, label_visibility="collapsed")

    st.markdown("---")

    config = None
    is_isolation = False

    if mode == "Preset Scenario":
        scenario_key = st.selectbox("Choose Scenario", list(SCENARIOS.keys()), label_visibility="visible")
        scenario     = SCENARIOS[scenario_key]
        config       = scenario.copy()

        if scenario["isolation_level"] != "ALL":
            isolation = st.selectbox(
                "Isolation Level",
                ["READ_UNCOMMITTED", "READ_COMMITTED", "REPEATABLE_READ", "SERIALIZABLE"],
                index=["READ_UNCOMMITTED","READ_COMMITTED","REPEATABLE_READ","SERIALIZABLE"].index(scenario["isolation_level"])
            )
            config["isolation_level"] = isolation
        else:
            is_isolation = True
            st.info("Runs all 4 isolation levels automatically")

    else:
        import os
        default_json = ""
        if os.path.exists("config.json"):
            try:
                with open("config.json", "r") as f:
                    default_json = f.read()
            except:
                pass
        if not default_json:
            default_json = json.dumps({
                "scenario_name": "My Custom Test",
                "isolation_level": "READ_COMMITTED",
                "initial_data": {"balance": 1000},
                "transactions": [
                    {"tid": "T1", "operations": [
                        {"op": "READ",  "key": "balance"},
                        {"op": "WRITE", "key": "balance", "value": 700},
                        {"op": "COMMIT"}
                    ]},
                    {"tid": "T2", "operations": [
                        {"op": "READ",  "key": "balance"},
                        {"op": "WRITE", "key": "balance", "value": 800},
                        {"op": "COMMIT"}
                    ]}
                ]
            }, indent=2)

        raw = st.text_area("Paste config.json", height=280, value=default_json)
        try:
            config = json.loads(raw)
            config["what_is_this"] = f"Custom scenario: **{config.get('scenario_name', 'Unnamed')}**"
            config["concepts"] = []
        except:
            st.error("Invalid JSON")
            config = None

    st.markdown("---")
    run_btn = st.button("▶  Run Simulation", type="primary", use_container_width=True)

# ─────────────────────────────────────
# HEADER
# ─────────────────────────────────────
st.markdown("""
<div class="acid-header">
    <div class="acid-title">🔬 AcidProbe</div>
    <div class="acid-tagline">See exactly what happens inside a database when two users touch the same data</div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────
# MAIN OUTPUT
# ─────────────────────────────────────
if run_btn and config:

    # ── ISOLATION SWITCHER ──
    if is_isolation:
        st.markdown('<div class="section-head">🔄 Isolation Level Comparison</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="explain-box">{config["what_is_this"]}</div>', unsafe_allow_html=True)

        iso_results = run_isolation_comparison(config)

        rows_html = ""
        for r in iso_results:
            dr  = "<span class='iso-yes'>⚠️ YES</span>" if r["dirty_read"]     else "<span class='iso-no'>✅ NO</span>"
            nr  = "<span class='iso-yes'>⚠️ YES</span>" if r["non_repeatable"] else "<span class='iso-no'>✅ NO</span>"
            lu  = "<span class='iso-yes'>⚠️ YES</span>" if r["lost_update"]    else "<span class='iso-no'>✅ NO</span>"
            bal = f"<span class='{'iso-correct' if r['correct'] else 'iso-wrong'}'>₹{r['final_balance']}</span>"
            ok  = "<span class='iso-correct'>✅ CORRECT</span>" if r["correct"] else "<span class='iso-wrong'>❌ WRONG</span>"
            rows_html += f"<tr><td class='iso-level'>{r['isolation']}</td><td>{dr}</td><td>{nr}</td><td>{lu}</td><td>{bal}</td><td>{ok}</td></tr>"

        st.markdown(f"""
        <table class="iso-table">
            <thead>
                <tr>
                    <th>Isolation Level</th>
                    <th>Dirty Read</th>
                    <th>Non-Repeatable</th>
                    <th>Lost Update</th>
                    <th>Final Balance</th>
                    <th>Correct?</th>
                </tr>
            </thead>
            <tbody>{rows_html}</tbody>
        </table>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="explain-box" style="margin-top:20px;">
            <strong>How to read this table:</strong><br>
            Each row is the same banking scenario — Rahul withdraws ₹300, Priya withdraws ₹200 from ₹1000 balance.<br>
            Expected final balance = <strong style="color:#34d399">₹500</strong>.<br>
            <strong>READ UNCOMMITTED</strong> → worst. Allows all anomalies.<br>
            <strong>READ COMMITTED</strong> → fixes dirty reads. Still allows lost updates.<br>
            <strong>REPEATABLE READ</strong> → fixes dirty + non-repeatable. Still allows lost updates in some cases.<br>
            <strong>SERIALIZABLE</strong> → fixes everything. Final balance is correct ₹500 ✅
        </div>
        """, unsafe_allow_html=True)

        st.stop()

    # ── NORMAL SCENARIO ──
    result = run_scenario(config)

    # SCENARIO INTRO
    what   = config.get("what_is_this", "")
    pills  = config.get("concepts", [])

    if what:
        st.markdown(f'<div class="explain-box"><strong>What is this scenario?</strong><br>{what}</div>', unsafe_allow_html=True)

    if pills:
        pills_html = "".join([f'<span class="concept-pill">{p}</span>' for p in pills])
        st.markdown(f"<div style='margin-bottom:20px;'>{pills_html}</div>", unsafe_allow_html=True)

    # STATS
    s = result["stats"]
    st.markdown(f"""
    <div class="stat-row">
        <div class="stat-card blue">
            <div class="stat-icon">🔄</div>
            <div class="stat-num">{s['total']}</div>
            <div class="stat-lbl">Transactions</div>
        </div>
        <div class="stat-card green">
            <div class="stat-icon">✅</div>
            <div class="stat-num">{s['committed']}</div>
            <div class="stat-lbl">Committed</div>
        </div>
        <div class="stat-card red">
            <div class="stat-icon">🛑</div>
            <div class="stat-num">{s['aborted']}</div>
            <div class="stat-lbl">Aborted</div>
        </div>
        <div class="stat-card amber">
            <div class="stat-icon">⏳</div>
            <div class="stat-num">{s['conflicts']}</div>
            <div class="stat-lbl">Lock Conflicts</div>
        </div>
        <div class="stat-card pink">
            <div class="stat-icon">💀</div>
            <div class="stat-num">{s['deadlocks']}</div>
            <div class="stat-lbl">Deadlocks</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # TABS
    tab1, tab2, tab3, tab4 = st.tabs([
        "⚡ Step Execution",
        "📅 Timeline View",
        "⚠️ Anomaly Report",
        "🗃️ Storage & State"
    ])

    # ─────────────────────────────────
    # TAB 1 — STEP EXECUTION
    # ─────────────────────────────────
    with tab1:
        col_steps, col_explain = st.columns([1.1, 0.9])

        with col_steps:
            st.markdown('<div class="section-head">⚡ Step-by-Step Execution</div>', unsafe_allow_html=True)
            st.markdown('<div class="explain-box">Each step is one database operation. <strong style="color:#34d399">Green</strong> = succeeded. <strong style="color:#fbbf24">Yellow</strong> = waiting for a lock. <strong style="color:#f87171">Red</strong> = deadlock detected.</div>', unsafe_allow_html=True)

            for s in result["steps"]:
                status = s["status"]
                op     = s["op"]
                key    = s.get("key", "")
                val    = s.get("value")
                note   = s.get("note", "")
                lt     = s.get("lock_table", "")
                ll     = s.get("lock_log", [])
                css, color = txn_color(s["tid"])

                icon    = "✅" if status == "ok" else ("⏳" if status == "wait" else "💀")
                val_str = f" → {val}" if val is not None and val != "" else ""
                key_str = f" {key}" if key else ""

                lock_info = ""
                if ll:
                    lock_info = f"<div class='step-lock'>{'  |  '.join(ll[:2])}</div>"

                lt_info = ""
                if lt and lt != "(empty)":
                    lt_info = f"<div class='step-meta'>🔒 Lock Table: {lt}</div>"

                wf_info = ""
                wf = s.get("wait_for_graph", {})
                if wf:
                    wf_str = ", ".join([f"{waiter} ➔ {holder}" for waiter, holder in sorted(wf.items())])
                    wf_info = f"<div class='step-meta' style='color:#fbbf24;'>⏳ Active Wait-For: {wf_str}</div>"

                note_info = ""
                if note:
                    note_info = f"<div class='step-meta' style='color:#f87171;'>⚠ {note}</div>"

                st.markdown(f"""
                <div class="step-card step-{status}">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                        <div>
                            <span style="color:#475569; font-size:11px;">[STEP {s['step']}]</span>
                            <span style="color:{color}; font-weight:600; margin-left:8px;">{s['tid']}</span>
                            <span style="color:#c084fc; font-weight:600; margin-left:6px;">{op}</span>
                            <span style="color:#fbbf24;">{key_str}</span>
                            <span style="color:#34d399;">{val_str}</span>
                        </div>
                        <span>{icon}</span>
                    </div>
                    {lock_info}{lt_info}{wf_info}{note_info}
                </div>
                """, unsafe_allow_html=True)

        with col_explain:
            st.markdown('<div class="section-head">🔒 Lock Breakdown</div>', unsafe_allow_html=True)
            st.markdown("""
            <div class="explain-box">
                <strong>S Lock (Shared)</strong> — given for READ operations.<br>
                Multiple transactions can hold S locks together.<br><br>
                <strong>X Lock (Exclusive)</strong> — given for WRITE operations.<br>
                Only one transaction can hold an X lock. All others must wait.<br><br>
                <strong>Compatibility:</strong><br>
                S + S = ✅ Both can read together<br>
                S + X = ⏳ Writer must wait for readers<br>
                X + X = ⏳ Second writer must wait<br>
                X + S = ⏳ Reader must wait for writer
            </div>
            """, unsafe_allow_html=True)

            # Lock pie chart
            ok_s  = sum(1 for s in result["steps"] if s["status"] == "ok")
            wt_s  = sum(1 for s in result["steps"] if s["status"] == "wait")
            dl_s  = sum(1 for s in result["steps"] if s["status"] == "deadlock")

            fig = go.Figure(data=[go.Pie(
                labels=["Succeeded", "Waiting", "Deadlock"],
                values=[ok_s, wt_s, dl_s],
                hole=0.5,
                marker_colors=["#10b981", "#f59e0b", "#ef4444"],
                textfont_size=12,
            )])
            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="#94a3b8",
                height=240,
                margin=dict(l=0, r=0, t=20, b=0),
                showlegend=True,
                legend=dict(font=dict(color="#94a3b8", size=11))
            )
            st.plotly_chart(fig, use_container_width=True)

    # ─────────────────────────────────
    # TAB 2 — TIMELINE
    # ─────────────────────────────────
    with tab2:
        st.markdown('<div class="section-head">📅 Concurrent Execution Timeline</div>', unsafe_allow_html=True)
        st.markdown('<div class="explain-box">Each column is one transaction. Read left to right — each row is one moment in time. <strong style="color:#fbbf24">⏳ WAITING</strong> means that transaction was blocked by a lock held by another.</div>', unsafe_allow_html=True)

        tids  = result["transactions"]
        steps = result["steps"]

        # build header
        color_map = {tid: TXN_COLORS.get(tid, ("cell-t1","#60a5fa"))[1] for tid in tids}
        th_html = "<th>Step</th>" + "".join([f"<th style='color:{color_map[t]}'>{t}</th>" for t in tids])

        rows_html = ""
        for s in steps:
            op  = s["op"]
            key = s.get("key", "")
            val = s.get("value")

            td_cells = []
            for tid in tids:
                if s["tid"] == tid:
                    c, color = txn_color(tid)
                    if s["status"] == "ok":
                        if val is not None and val != "":
                            cell = f"<span style='color:{color}'>{op} {key}={val} ✅</span>"
                        else:
                            cell = f"<span style='color:{color}'>{op} ✅</span>"
                    elif s["status"] == "wait":
                        wf = s.get("wait_for_graph", {})
                        holder = wf.get(tid)
                        if holder:
                            cell = f"<span class='cell-wait'>⏳ {op} {key} (blocked by {holder})</span>"
                        else:
                            cell = f"<span class='cell-wait'>⏳ {op} {key} WAITING</span>"
                    else:
                        cell = f"<span class='cell-dead'>💀 DEADLOCK</span>"
                else:
                    cell = "<span class='cell-pipe'>│</span>"
                td_cells.append(f"<td>{cell}</td>")

            rows_html += f"<tr><td style='color:#475569; font-size:11px;'>STEP {s['step']}</td>{''.join(td_cells)}</tr>"

        st.markdown(f"""
        <table class="tl-table">
            <thead><tr>{th_html}</tr></thead>
            <tbody>{rows_html}</tbody>
        </table>
        """, unsafe_allow_html=True)

        # highlight anomaly steps
        wait_steps = [s for s in steps if s["status"] in ["wait","deadlock"]]
        if wait_steps:
            st.markdown("<br>", unsafe_allow_html=True)
            for s in wait_steps:
                if s["status"] == "wait":
                    wf = s.get("wait_for_graph", {})
                    holder = wf.get(s["tid"], "?")
                    st.markdown(f"<div style='color:#f59e0b; font-size:0.85rem;'>⚠ STEP {s['step']} — {s['tid']} was blocked by {holder}. This is where a potential anomaly can occur.</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div style='color:#ef4444; font-size:0.85rem;'>💀 STEP {s['step']} — DEADLOCK detected. System automatically resolved it.</div>", unsafe_allow_html=True)

    # ─────────────────────────────────
    # TAB 3 — ANOMALY REPORT
    # ─────────────────────────────────
    with tab3:
        detected = [a["type"] for a in result["anomalies"]]

        st.markdown('<div class="section-head">⚠️ Anomaly Detection Report</div>', unsafe_allow_html=True)
        st.markdown('<div class="explain-box">AcidProbe automatically checks for all 4 types of concurrency anomalies after execution. Each anomaly is explained in plain English so you understand what went wrong and how to fix it.</div>', unsafe_allow_html=True)

        for atype, meta in ANOMALY_META.items():
            if atype in detected:
                # find description from anomalies list
                desc = next((a["description"] for a in result["anomalies"] if a["type"] == atype), "")
                st.markdown(f"""
                <div class="anomaly-detected">
                    <div class="anomaly-title" style="color:#f87171;">{meta['icon']} {atype} — DETECTED</div>
                    <div class="anomaly-desc"><strong>What is this?</strong> {meta['what']}</div>
                    <div class="anomaly-desc" style="margin-top:6px;"><strong>What happened here:</strong> {meta['example']}</div>
                    <div class="anomaly-fix">💡 Fix: {meta['fix']}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="anomaly-clean">
                    <div class="anomaly-title" style="color:#34d399;">{meta['icon']} {atype} — NOT DETECTED ✅</div>
                    <div class="anomaly-desc">{meta['what']}</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("---")

        # Serializability
        st.markdown('<div class="section-head">🔄 Serializability Check</div>', unsafe_allow_html=True)
        st.markdown('<div class="explain-box">A schedule is <strong>serializable</strong> if its result is identical to running the transactions one after another (serially). We check this by building a precedence graph and looking for cycles.</div>', unsafe_allow_html=True)

        if result["serializable"]:
            st.markdown("""
            <div class="serial-ok">
                <div class="serial-title" style="color:#34d399;">✅ Schedule is SERIALIZABLE</div>
                <div class="serial-desc">No cycle found in the precedence graph. The concurrent execution produced the same result as some serial order. This means the schedule is safe.</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            cycle_str = " → ".join(result["cycle_path"] or [])
            st.markdown(f"""
            <div class="serial-fail">
                <div class="serial-title" style="color:#f87171;">⚠️ Schedule is NOT SERIALIZABLE</div>
                <div class="serial-cycle">Cycle: {cycle_str}</div>
                <div class="serial-desc">A cycle was found in the precedence graph. This means the concurrent execution produced a result that no serial ordering of these transactions could produce. The database is in an inconsistent state.</div>
                <div class="anomaly-fix" style="margin-top:8px;">💡 Fix: Use SERIALIZABLE isolation level.</div>
            </div>
            """, unsafe_allow_html=True)

        # precedence graph
        if result["graph"]:
            st.markdown('<div class="section-head" style="margin-top:20px;">Precedence Graph (Serializability)</div>', unsafe_allow_html=True)
            st.markdown("""
            <div class="explain-box">
                This graph shows conflicts between <strong>committed</strong> transactions. 
                Aborted transactions (like those aborted during deadlocks) are rolled back entirely, 
                meaning their operations have no final effect on database consistency and are excluded from this graph.
            </div>
            """, unsafe_allow_html=True)
            
            cycle_edges = set()
            cp = result["cycle_path"] or []
            for i in range(len(cp)-1):
                cycle_edges.add((cp[i], cp[i+1]))

            # Enforce consistent left-to-right alignment of transaction nodes
            sorted_nodes = sorted(result["graph"].keys(), key=lambda x: int(x[1:]) if x[1:].isdigit() else x)

            dot = "digraph G {\n  bgcolor=\"transparent\";\n  rankdir=LR;\n"
            dot += '  nodesep=0.25;\n  ranksep=0.35;\n'
            dot += '  node [style="filled", shape="circle", fontname="Inter", penwidth=1.5, width=0.35, height=0.35, fontsize=8, fixedsize=true];\n'
            dot += '  edge [penwidth=1.5, arrowsize=0.5];\n'
            
            if len(sorted_nodes) > 1:
                invis_path = " -> ".join([f'"{n}"' for n in sorted_nodes])
                dot += f"  {invis_path} [style=invis];\n"
                
            for node in sorted_nodes:
                color = "#ef4444" if node in cp else "#3b82f6"
                fc    = "#2d0808" if node in cp else "#1e3a5f"
                dot  += f'  "{node}" [fillcolor="{fc}", color="{color}", fontcolor="white"];\n'
            for node, neighbors in sorted(result["graph"].items()):
                for nb in sorted(neighbors):
                    ec = "#ef4444" if (node, nb) in cycle_edges else "#475569"
                    dot += f'  "{node}" -> "{nb}" [color="{ec}", constraint=false];\n'
            dot += "}"
            
            # Constrain the width using smaller columns (25% graph, 75% spacer)
            col_graph_render, _ = st.columns([1, 3])
            with col_graph_render:
                st.graphviz_chart(dot, use_container_width=True)

        # Lock Wait-For Graph
        st.markdown('<div class="section-head" style="margin-top:20px;">Lock Wait-For Graph</div>', unsafe_allow_html=True)
        cwf = result.get("cumulative_wait_for", {})
        if cwf:
            st.markdown("""
            <div class="explain-box">
                This graph shows the lock waiting dependencies that occurred during the simulation. 
                An arrow <strong>T1 ➔ T2</strong> means T1 was blocked waiting for a lock held by T2.
                This is different from the Precedence Graph, which shows conflicts between committed transactions to check serializability.
            </div>
            """, unsafe_allow_html=True)
            
            all_nodes = set(cwf.keys())
            for holders in cwf.values():
                all_nodes.update(holders)
                
            sorted_nodes = sorted(list(all_nodes), key=lambda x: int(x[1:]) if x[1:].isdigit() else x)
            
            dot_cwf = "digraph WF {\n  bgcolor=\"transparent\";\n  rankdir=LR;\n"
            dot_cwf += '  nodesep=0.25;\n  ranksep=0.35;\n'
            dot_cwf += '  node [style="filled", shape="circle", fontname="Inter", penwidth=1.5, width=0.35, height=0.35, fontsize=8, fixedsize=true];\n'
            dot_cwf += '  edge [penwidth=1.5, arrowsize=0.5, color="#fbbf24"];\n'
            
            if len(sorted_nodes) > 1:
                invis_path = " -> ".join([f'"{n}"' for n in sorted_nodes])
                dot_cwf += f"  {invis_path} [style=invis];\n"
                
            for node in sorted_nodes:
                dot_cwf += f'  "{node}" [fillcolor="#2d1a00", color="#fbbf24", fontcolor="white"];\n'
                
            for waiter, holders in sorted(cwf.items()):
                for holder in sorted(holders):
                    dot_cwf += f'  "{waiter}" -> "{holder}" [constraint=false];\n'
            dot_cwf += "}"
            
            col_cwf_render, _ = st.columns([1, 3])
            with col_cwf_render:
                st.graphviz_chart(dot_cwf, use_container_width=True)
        else:
            st.markdown("""
            <div class="explain-box">
                No lock conflicts occurred during this execution. All transactions acquired their locks instantly without waiting.
            </div>
            """, unsafe_allow_html=True)

        # deadlock wait-for graphs
        if result.get("deadlocks_list"):
            st.markdown('<div class="section-head" style="margin-top:20px;">💀 Deadlock Wait-For Graph (Circular Locking)</div>', unsafe_allow_html=True)
            st.markdown("""
            <div class="explain-box">
                This graph shows the circular lock dependencies (circular wait) at the exact moment a deadlock occurred, 
                prior to the system aborting the youngest transaction as a victim to resolve the block.
            </div>
            """, unsafe_allow_html=True)
            
            for dl in result["deadlocks_list"]:
                cycle_str = " ➔ ".join(dl["cycle"] or [])
                st.markdown(f"""
                <div class="anomaly-detected" style="margin-top: 8px; padding: 12px 16px;">
                    <div class="anomaly-title" style="color:#f87171;">💀 Deadlock Detected at Step {dl["step"]}</div>
                    <div class="anomaly-desc">
                        Lock Cycle: <code style="color: #f87171; background: rgba(239, 68, 68, 0.2); padding: 2px 6px; border-radius: 4px; font-family: monospace;">{cycle_str}</code><br>
                        Victim Aborted & Rolled Back: <b style="color: #f87171;">{dl["victim"]}</b>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                if dl["cycle"]:
                    dot_wf = "digraph WF {\n  bgcolor=\"transparent\";\n  rankdir=LR;\n"
                    dot_wf += '  nodesep=0.25;\n  ranksep=0.35;\n'
                    dot_wf += '  node [style="filled", shape="circle", fontname="Inter", penwidth=1.5, width=0.35, height=0.35, fontsize=8, fixedsize=true];\n'
                    dot_wf += '  edge [penwidth=1.5, arrowsize=0.5, color="#ef4444"];\n'
                    
                    # Track nodes sorted consistently
                    sorted_dl_nodes = sorted(list(set(dl["cycle"])), key=lambda x: int(x[1:]) if x[1:].isdigit() else x)
                    for node in sorted_dl_nodes:
                        fc = "#2d0808" if node == dl["victim"] else "#1e3a5f"
                        color = "#ef4444" if node == dl["victim"] else "#3b82f6"
                        label = f"{node}\\n(victim)" if node == dl["victim"] else node
                        dot_wf += f'  "{node}" [fillcolor="{fc}", color="{color}", fontcolor="white", label="{label}"];\n'
                        
                    for i in range(len(dl["cycle"]) - 1):
                        dot_wf += f'  "{dl["cycle"][i]}" -> "{dl["cycle"][i+1]}";\n'
                    dot_wf += "}"
                    
                    col_wf_render, _ = st.columns([1, 3])
                    with col_wf_render:
                        st.graphviz_chart(dot_wf, use_container_width=True)

    # ─────────────────────────────────
    # TAB 4 — STORAGE & STATE
    # ─────────────────────────────────
    with tab4:
        col_fs, col_mv = st.columns([0.8, 1.2])

        with col_fs:
            st.markdown('<div class="section-head">🏁 Final Database State</div>', unsafe_allow_html=True)
            st.markdown('<div class="explain-box">These are the actual values committed to the database after all transactions finished.</div>', unsafe_allow_html=True)

            for key, val in result["final_state"].items():
                init_val = result["initial_state"].get(key, "?")
                changed  = val != init_val
                arrow    = f"<span style='color:#64748b; font-size:0.85rem;'>{init_val} → </span>" if changed else ""
                color    = "#34d399" if not changed else ("#f87171" if val != init_val else "#34d399")
                st.markdown(f"""
                <div class="final-state-card">
                    <div class="final-key">{key}</div>
                    <div class="final-val" style="color:{color};">{arrow}{val}</div>
                </div>
                """, unsafe_allow_html=True)

        with col_mv:
            st.markdown('<div class="section-head">🗃️ MVCC Version History</div>', unsafe_allow_html=True)
            st.markdown('<div class="explain-box"><strong>MVCC</strong> = Multi Version Concurrency Control. Instead of overwriting data, the database keeps every version ever written. Each transaction reads the version that existed when it started — no blocking needed for reads.</div>', unsafe_allow_html=True)

            for key, versions in result["mvcc_versions"].items():
                st.markdown(f'<div class="mvcc-key">Key: {key}</div>', unsafe_allow_html=True)
                rows = ""
                for v in versions:
                    status = "<span class='mvcc-committed'>Committed ✅</span>" if v.get("committed") else "<span class='mvcc-uncommitted'>Uncommitted ⏳</span>"
                    rows  += f"<tr><td>{v['value']}</td><td>{v['ts']}</td><td>{v['by']}</td><td>{status}</td></tr>"
                st.markdown(f"""
                <table class="mvcc-table">
                    <thead><tr><th>Value</th><th>Timestamp</th><th>Written By</th><th>Status</th></tr></thead>
                    <tbody>{rows}</tbody>
                </table>
                """, unsafe_allow_html=True)

else:
    st.markdown("""
    <div style="text-align:center; padding:16px 40px 40px;">
        <div style="font-size:4rem; margin-bottom:20px;">🔬</div>
        <h2 style="font-family:'Space Grotesk',sans-serif; color:#e2e8f0; font-size:1.8rem; margin-bottom:12px;">
            Pick a scenario from the sidebar
        </h2>
        <p style="color:#64748b; font-size:1rem; max-width:480px; margin:0 auto; line-height:1.8;">
            Each scenario demonstrates a real-world database concurrency problem.<br>
            Select a preset and click <strong style="color:#818cf8">▶ Run Simulation</strong> to watch it run step by step.
        </p>
        <div style="margin-top:32px; display:flex; justify-content:center; gap:12px; flex-wrap:wrap;">
            <span class="concept-pill">🏦 UPI Payment</span>
            <span class="concept-pill">💀 Deadlock</span>
            <span class="concept-pill">✈️ Overbooking</span>
            <span class="concept-pill">📦 Overselling</span>
            <span class="concept-pill">🔄 Isolation Levels</span>
        </div>
    </div>
    """, unsafe_allow_html=True)