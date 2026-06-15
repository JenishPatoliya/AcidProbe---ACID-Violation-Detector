class LockManager:
    def __init__(self, silent=False):
        self.lock_table      = {}
        self.wait_for_graph  = {}
        self.transactions    = {}
        self.silent          = silent
        self.lock_log        = []   # stores lock events per step

    def register(self, transaction):
        self.transactions[transaction.tid] = transaction

    def _log(self, message, level="info"):
        self.lock_log.append({"message": message, "level": level})
        if not self.silent:
            print(message)

    def get_and_clear_log(self):
        log = self.lock_log.copy()
        self.lock_log = []
        return log

    def get_lock_table_str(self):
        if not self.lock_table:
            return "(empty)"
        parts = []
        for key, info in self.lock_table.items():
            owners = ", ".join(info["owners"])
            parts.append(f"{key} → {info['type']} → [{owners}]")
        return " | ".join(parts)

    # ─────────────────────────────────────
    # ACQUIRE
    # ─────────────────────────────────────
    def acquire(self, transaction, key, lock_type):
        tid = transaction.tid

        if key not in self.lock_table:
            self.lock_table[key] = {"type": lock_type, "owners": [tid]}
            self._log(f"🔒 {tid} acquired {lock_type} lock on '{key}'", "ok")
            return True

        existing = self.lock_table[key]

        if tid in existing["owners"] and len(existing["owners"]) == 1:
            if lock_type == "X" and existing["type"] == "S":
                existing["type"] = "X"
                self._log(f"🔒 {tid} upgraded S→X lock on '{key}'", "ok")
            return True

        if existing["type"] == "S" and lock_type == "S" and tid not in existing["owners"]:
            existing["owners"].append(tid)
            self._log(f"🔒 {tid} acquired S lock on '{key}' (shared)", "ok")
            return True

        owner = [o for o in existing["owners"] if o != tid][0]
        self.wait_for_graph[tid] = owner
        self._log(f"🔒 {tid} wants {lock_type} lock on '{key}' — CONFLICT ({owner} holds {existing['type']})", "wait")
        self._log(f"⏳ {tid} waiting for {owner} to release...", "wait")

        if self.detect_deadlock(tid):
            self._log(f"💀 DEADLOCK — cycle detected", "deadlock")
            cycle = self.find_deadlock_cycle()
            cycle_tids = [t for t in cycle if t in self.transactions] if cycle else [tid]
            victim = self.resolve_deadlock(cycle_tids)
            return "DEADLOCK", victim

        # Mark transaction as WAITING
        transaction.status = "WAITING"
        transaction.wait_key = key
        transaction.wait_lock_type = lock_type
        return False

    # ─────────────────────────────────────
    # RELEASE
    # ─────────────────────────────────────
    def release(self, transaction):
        tid = transaction.tid
        keys_to_release = []

        for key, lock_info in self.lock_table.items():
            if tid in lock_info["owners"]:
                lock_info["owners"].remove(tid)
                if not lock_info["owners"]:
                    keys_to_release.append(key)

        for key in keys_to_release:
            del self.lock_table[key]
            self._log(f"🔓 {tid} released lock on '{key}'", "release")
            self.wakeup_waiters(key)

        if tid in self.wait_for_graph:
            del self.wait_for_graph[tid]

    def release_shared_lock(self, transaction, key):
        tid = transaction.tid
        if key in self.lock_table:
            lock_info = self.lock_table[key]
            if tid in lock_info["owners"] and lock_info["type"] == "S":
                lock_info["owners"].remove(tid)
                if not lock_info["owners"]:
                    del self.lock_table[key]
                    self._log(f"🔓 {tid} released S lock on '{key}' (short-duration)", "release")
                    self.wakeup_waiters(key)

    def wakeup_waiters(self, key):
        woken = []
        for txn in list(self.transactions.values()):
            if txn.status == "WAITING" and txn.wait_key == key:
                txn.status = "ACTIVE"
                txn.wait_key = None
                txn.wait_lock_type = None
                if txn.tid in self.wait_for_graph:
                    del self.wait_for_graph[txn.tid]
                self._log(f"🔔 Woke up waiting transaction {txn.tid} (now ACTIVE)", "release")
                woken.append(txn.tid)
        return woken

    # ─────────────────────────────────────
    # DEADLOCK DETECTION
    # ─────────────────────────────────────
    def detect_deadlock(self, start):
        def dfs(node, path):
            if node in path:
                return True
            path.add(node)
            neighbor = self.wait_for_graph.get(node)
            if neighbor and dfs(neighbor, path):
                return True
            path.remove(node)
            return False
        return dfs(start, set())

    def find_deadlock_cycle(self):
        def dfs(node, path):
            if node in path:
                idx = path.index(node)
                return path[idx:] + [node]
            path.append(node)
            neighbor = self.wait_for_graph.get(node)
            if neighbor:
                result = dfs(neighbor, path)
                if result:
                    return result
            path.pop()
            return None
        for node in self.wait_for_graph:
            result = dfs(node, [])
            if result:
                return result
        return None

    def resolve_deadlock(self, cycle_tids):
        youngest = max(
            cycle_tids,
            key=lambda tid: self.transactions[tid].start_ts
        )
        victim = self.transactions[youngest]
        self._log(f"💀 Aborting youngest transaction: {youngest}", "deadlock")
        victim.rollback()
        self.release(victim)
        return victim

    def print_wait_graph(self):
        print("\n  Wait-For Graph:")
        if not self.wait_for_graph:
            print("  (empty)")
        for waiter, holder in self.wait_for_graph.items():
            print(f"  {waiter} ──waits──→ {holder}")

    def print_lock_table(self):
        print(f"  Lock Table: {self.get_lock_table_str()}")
