# ─────────────────────────────────────
# SCENARIOS & CONSTANTS
# Extracted from streamlit_app.py for modularity
# ─────────────────────────────────────

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
