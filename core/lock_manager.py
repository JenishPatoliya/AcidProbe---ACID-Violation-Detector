class LockManager:
    def __init__(self, silent=False):
        self.lock_table = {}
        self.wait_for_graph = {}
        self.transactions = {}      # tracks all transactions by tid
        self.silent = silent

    def register(self, transaction):
        self.transactions[transaction.tid] = transaction

    def _log(self, message):
        if not self.silent:
            print(message)

    # ─────────────────────────────────────
    # ACQUIRE LOCK
    # ─────────────────────────────────────
    def acquire(self, transaction, key, lock_type):
        tid = transaction.tid

        if key not in self.lock_table:
            self.lock_table[key] = {
                "type": lock_type,
                "owners": [tid]
            }
            self._log(f"  [LOCK] {tid} acquired {lock_type} lock on '{key}' ✅")
            return True

        existing = self.lock_table[key]

        # same transaction only owner — allow upgrade
        if tid in existing["owners"] and len(existing["owners"]) == 1:
            if lock_type == "X" and existing["type"] == "S":
                existing["type"] = "X"
                self._log(f"  [LOCK] {tid} upgraded lock to X on '{key}' ✅")
            return True

        # S + S compatible
        if existing["type"] == "S" and lock_type == "S" and tid not in existing["owners"]:
            existing["owners"].append(tid)
            self._log(f"  [LOCK] {tid} acquired S lock on '{key}' (shared) ✅")
            return True

        # conflict — must wait
        owner = [o for o in existing["owners"] if o != tid][0]
        self.wait_for_graph[tid] = owner
        self._log(f"  [LOCK] {tid} wants {lock_type} lock on '{key}' — WAITING (held by {owner}) ⏳")

        # check deadlock
        if self.detect_deadlock(tid):
            return "DEADLOCK"

        return False

    # ─────────────────────────────────────
    # RELEASE LOCKS
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
            self._log(f"  [LOCK] {tid} released lock on '{key}' 🔓")

        if tid in self.wait_for_graph:
            del self.wait_for_graph[tid]

    # ─────────────────────────────────────
    # DEADLOCK DETECTION — DFS
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

    # ─────────────────────────────────────
    # FIND DEADLOCK CYCLE
    # ─────────────────────────────────────
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

    # ─────────────────────────────────────
    # RESOLVE DEADLOCK
    # abort youngest transaction
    # ─────────────────────────────────────
    def resolve_deadlock(self, cycle_tids):
        # youngest = highest start_ts
        youngest = max(
            cycle_tids,
            key=lambda tid: self.transactions[tid].start_ts
        )
        victim = self.transactions[youngest]
        print(f"\n  [DEADLOCK RESOLUTION]")
        print(f"  Cycle involves: {' → '.join(cycle_tids)}")
        print(f"  Aborting youngest transaction: {youngest}")
        victim.rollback()
        self.release(victim)
        return victim

    # ─────────────────────────────────────
    # PRINT LOCK TABLE
    # ─────────────────────────────────────
    def print_lock_table(self):
        print("\n  Current Lock Table:")
        if not self.lock_table:
            print("  (empty)")
        for key, info in self.lock_table.items():
            print(f"  '{key}' → {info['type']} lock, owners: {info['owners']}")

    # ─────────────────────────────────────
    # PRINT WAIT FOR GRAPH
    # ─────────────────────────────────────
    def print_wait_graph(self):
        print("\n  Wait-For Graph:")
        if not self.wait_for_graph:
            print("  (empty — no waiting)")
        for waiter, holder in self.wait_for_graph.items():
            print(f"  {waiter} ──waits──→ {holder}")
