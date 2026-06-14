class SerializabilityChecker:
    def __init__(self):
        # precedence graph
        # {"T1": ["T2"], "T2": ["T1"]}
        self.graph = {}

    # ─────────────────────────────────────────────
    # BUILD PRECEDENCE GRAPH
    # rules:
    #   T1 → T2 if T1 READ key before T2 WROTE key
    #   T1 → T2 if T1 WROTE key before T2 READ key
    #   T1 → T2 if T1 WROTE key before T2 WROTE key
    # ─────────────────────────────────────────────
    def build_graph(self, transactions):
        print("\n  Building Precedence Graph...")

        for i in range(len(transactions)):
            for j in range(len(transactions)):
                if i == j:
                    continue

                t1 = transactions[i]
                t2 = transactions[j]

                # find common keys both transactions touched
                t1_keys = set(list(t1.read_set.keys()) + list(t1.write_set.keys()))
                t2_keys = set(list(t2.read_set.keys()) + list(t2.write_set.keys()))
                common_keys = t1_keys & t2_keys

                for key in common_keys:
                    edge_added = False

                    # T1 read, T2 wrote same key
                    if key in t1.read_set and key in t2.write_set:
                        self._add_edge(t1.tid, t2.tid)
                        print(f"  {t1.tid} READ '{key}' before {t2.tid} WROTE it  →  {t1.tid} → {t2.tid}")
                        edge_added = True

                    # T1 wrote, T2 read same key
                    if key in t1.write_set and key in t2.read_set and not edge_added:
                        self._add_edge(t1.tid, t2.tid)
                        print(f"  {t1.tid} WROTE '{key}' before {t2.tid} READ it  →  {t1.tid} → {t2.tid}")
                        edge_added = True

                    # T1 wrote, T2 wrote same key
                    if key in t1.write_set and key in t2.write_set and not edge_added:
                        self._add_edge(t1.tid, t2.tid)
                        print(f"  {t1.tid} WROTE '{key}' before {t2.tid} WROTE it →  {t1.tid} → {t2.tid}")

        print(f"\n  Final Graph: {self.graph}")

    def _add_edge(self, from_tid, to_tid):
        if from_tid not in self.graph:
            self.graph[from_tid] = []
        if to_tid not in self.graph[from_tid]:
            self.graph[from_tid].append(to_tid)

    # ─────────────────────────────────────────────
    # DFS CYCLE DETECTION
    # your 10 line DFS
    # ─────────────────────────────────────────────
    def has_cycle(self):
        def dfs(node, path):
            if node in path:
                return True        # cycle found!
            path.add(node)
            for neighbor in self.graph.get(node, []):
                if dfs(neighbor, path):
                    return True
            path.remove(node)
            return False

        return any(dfs(node, set()) for node in self.graph)

    # ─────────────────────────────────────────────
    # FIND CYCLE PATH (to show T1 → T2 → T1)
    # ─────────────────────────────────────────────
    def find_cycle_path(self):
        def dfs(node, path, visited):
            if node in path:
                # extract just the cycle part
                cycle_start = path.index(node)
                return path[cycle_start:] + [node]
            if node in visited:
                return None
            path.append(node)
            visited.add(node)
            for neighbor in self.graph.get(node, []):
                result = dfs(neighbor, path, visited)
                if result:
                    return result
            path.pop()
            return None

        for node in self.graph:
            result = dfs(node, [], set())
            if result:
                return result
        return None

    # ─────────────────────────────────────────────
    # PRINT RESULT
    # ─────────────────────────────────────────────
    def print_result(self):
        print("\n" + "─"*55)
        print(" SERIALIZABILITY CHECK")
        print("─"*55)

        print(f"\n  Precedence Graph:")
        if not self.graph:
            print("  (empty — no conflicts)")
        for node, neighbors in self.graph.items():
            for n in neighbors:
                print(f"  {node} ──→ {n}")

        if self.has_cycle():
            cycle = self.find_cycle_path()
            cycle_str = " → ".join(cycle)
            print(f"\n  Cycle found : {cycle_str}")
            print(f"\n  ⚠️  Schedule is NOT SERIALIZABLE")
            print(f"  This means concurrent execution gave")
            print(f"  a result no serial order could give")
            print(f"\n  💡 Fix: Use SERIALIZABLE isolation level")
        else:
            print(f"\n  No cycle found")
            print(f"\n  ✅ Schedule is SERIALIZABLE")
            print(f"  Concurrent execution is safe —")
            print(f"  equivalent to some serial order")

        print("─"*55)
