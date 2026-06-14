class MVCCDataStore:
    def __init__(self):
        self.data = {}

    def init_data(self, key, value):
        self.data[key] = [{"value": value, "ts": 0, "by": "SYSTEM", "committed": True}]

    def read(self, key, transaction):
        versions = self.data.get(key, [])

        if transaction.allows_dirty_read():
            # READ UNCOMMITTED — see everything including uncommitted
            valid = versions
        else:
            # READ COMMITTED and above — only see committed versions
            valid = [v for v in versions if v.get("committed", True)]

        if transaction.isolation in ["REPEATABLE_READ", "SERIALIZABLE"]:
            # see only versions that existed when transaction started
            valid = [v for v in valid if v["ts"] <= transaction.start_ts]

        if valid:
            result = max(valid, key=lambda v: v["ts"])
            transaction.read_set[key] = result["value"]
            return result["value"]
        return None

    def write(self, key, value, transaction):
        if key not in self.data:
            self.data[key] = []
        self.data[key].append({
            "value":     value,
            "ts":        transaction.start_ts + 1,
            "by":        transaction.tid,
            "committed": False      # not committed yet!
        })
        transaction.write_set[key] = value

    def commit_transaction(self, transaction):
        # mark all versions by this transaction as committed
        for key in self.data:
            for version in self.data[key]:
                if version["by"] == transaction.tid:
                    version["committed"] = True
        transaction.commit()

    def rollback_transaction(self, transaction):
        # remove all uncommitted versions by this transaction
        for key in self.data:
            self.data[key] = [
                v for v in self.data[key]
                if not (v["by"] == transaction.tid and not v.get("committed", True))
            ]
        transaction.rollback()

    def get_latest(self, key):
        versions = self.data.get(key, [])
        committed = [v for v in versions if v.get("committed", True)]
        if committed:
            return max(committed, key=lambda v: v["ts"])["value"]
        return None

    def print_versions(self, key):
        print(f"\nAll versions of '{key}':")
        for v in self.data.get(key, []):
            status = "committed" if v.get("committed") else "uncommitted"
            print(f"  value={v['value']}, ts={v['ts']}, by={v['by']}, {status}")