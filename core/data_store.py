import os
import json

class MVCCDataStore:
    def __init__(self):
        self.data = {}
        self.load_seeds()

    def load_seeds(self):
        # Locate seed.json in the project root (one level up from core/)
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        seed_path = os.path.join(root_dir, "seed.json")
        if os.path.exists(seed_path):
            try:
                with open(seed_path, "r") as f:
                    seeds = json.load(f)
                    for key, value in seeds.items():
                        # Set directly to populate self.data
                        self.data[key] = [{"value": value, "ts": 0, "by": "SYSTEM", "committed": True}]
            except Exception as e:
                print(f"Error loading seed.json: {e}")

    def init_data(self, key, value):
        if key in self.data:
            return
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
        if transaction.status == "ABORTED":
            raise ValueError(f"Aborted transaction {transaction.tid} cannot commit")
        # mark all versions by this transaction as committed
        for key in self.data:
            for version in self.data[key]:
                if version["by"] == transaction.tid:
                    version["committed"] = True
        transaction.commit()

    def rollback_transaction(self, transaction):
        restored = []
        for key in self.data:
            for v in self.data[key]:
                if v["by"] == transaction.tid and not v.get("committed", True):
                    # Find previous committed version of this key
                    committed_versions = [x for x in self.data[key] if x.get("committed", True) and x["by"] != transaction.tid]
                    prev_val = max(committed_versions, key=lambda x: x["ts"])["value"] if committed_versions else "None"
                    restored.append((key, v["value"], prev_val))

        # remove all uncommitted versions by this transaction
        for key in self.data:
            self.data[key] = [
                v for v in self.data[key]
                if not (v["by"] == transaction.tid and not v.get("committed", True))
            ]
        transaction.rollback()
        return restored

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