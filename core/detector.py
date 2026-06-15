class AnomalyDetector:
    def __init__(self):
        self.anomalies = []   # stores all detected anomalies

    # ─────────────────────────────────────────────
    # CHECK 1 — DIRTY READ
    # T1 reads data written by T2 (not yet committed)
    # ─────────────────────────────────────────────
    def check_dirty_read(self, reader, writer, key, value):
        if writer.status == "ACTIVE" and key in writer.write_set:
            if writer.write_set[key] == value:
                anomaly = {
                    "type": "DIRTY READ",
                    "description": (
                        f"{reader.tid} read '{key}={value}' "
                        f"written by {writer.tid} which is NOT yet committed"
                    ),
                    "fix": "Use READ COMMITTED isolation level"
                }
                self.anomalies.append(anomaly)
                self._print_anomaly(anomaly)
                return True
        return False

    # ─────────────────────────────────────────────
    # CHECK 2 — NON REPEATABLE READ
    # T1 reads same key twice and gets different values
    # ─────────────────────────────────────────────
    def check_non_repeatable_read(self, transaction, key, old_value, new_value):
        if old_value is not None and old_value != new_value:
            anomaly = {
                "type": "NON-REPEATABLE READ",
                "description": (
                    f"{transaction.tid} read '{key}' twice — "
                    f"first got {old_value}, now got {new_value}"
                ),
                "fix": "Use REPEATABLE READ isolation level"
            }
            self.anomalies.append(anomaly)
            self._print_anomaly(anomaly)
            return True
        return False

    # ─────────────────────────────────────────────
    # CHECK 3 — LOST UPDATE
    # T1 and T2 both read same value
    # T1 writes, T2 writes — T1's write is lost
    # ─────────────────────────────────────────────
    def check_lost_update(self, t1, t2, key, db):
        # both must have read the same key
        if key not in t1.read_set or key not in t2.read_set:
            return False

        # both must have written the same key
        if key not in t1.write_set or key not in t2.write_set:
            return False

        # both read same original value
        if t1.read_set[key] != t2.read_set[key]:
            return False

        # t1 committed but t2 overwrote it
        status_info = ""
        if t1.status != "COMMITTED" or t2.status != "COMMITTED":
            status_info = " (POTENTIAL CONFLICT due to aborted/active transaction status)"

        anomaly = {
            "type": "LOST UPDATE",
            "description": (
                f"Both {t1.tid} and {t2.tid} read '{key}={t1.read_set[key]}'\n"
                f"  {t1.tid} wrote/attempted to write {t1.write_set[key]} (status: {t1.status})\n"
                f"  {t2.tid} wrote/attempted to write {t2.write_set[key]} (status: {t2.status})\n"
                f"  Lost update conflict{status_info} detected on '{key}'"
            ),
            "fix": "Use REPEATABLE READ isolation level"
        }
        self.anomalies.append(anomaly)
        self._print_anomaly(anomaly)
        return True

    # ─────────────────────────────────────────────
    # PRINT ANOMALY (formatted)
    # ─────────────────────────────────────────────
    def _print_anomaly(self, anomaly):
        pass    # logger handles printing now

    # ─────────────────────────────────────────────
    # FINAL REPORT
    # ─────────────────────────────────────
    def print_report(self):
        print("\n" + "─"*55)
        print(" ANOMALY DETECTION REPORT")
        print("─"*55)

        all_types = [
            "DIRTY READ",
            "NON-REPEATABLE READ",
            "LOST UPDATE"
        ]

        detected_types = [a["type"] for a in self.anomalies]

        for t in all_types:
            if t in detected_types:
                print(f"  {t:25} →  ⚠️  DETECTED")
            else:
                print(f"  {t:25} →  ✅ NOT DETECTED")

        print("─"*55)

        if self.anomalies:
            print(f"\n  Total anomalies found: {len(self.anomalies)}")
            for a in self.anomalies:
                print(f"  💡 Fix for {a['type']}: {a['fix']}")
        else:
            print("\n  ✅ No anomalies detected!")

        print("─"*55)
