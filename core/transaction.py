class Transaction:
    ISOLATION_LEVELS = {
        "READ_UNCOMMITTED": 0,
        "READ_COMMITTED":   1,
        "REPEATABLE_READ":  2,
        "SERIALIZABLE":     3
    }

    def __init__(self, tid, start_ts, isolation="READ_COMMITTED"):
        self.tid        = tid
        self.start_ts   = start_ts
        self.isolation  = isolation
        self.status     = "ACTIVE"
        self.read_set   = {}
        self.write_set  = {}

    def isolation_level(self):
        return self.ISOLATION_LEVELS.get(self.isolation, 1)

    def allows_dirty_read(self):
        return self.isolation_level() < 1

    def allows_non_repeatable_read(self):
        return self.isolation_level() < 2

    def allows_phantom_read(self):
        return self.isolation_level() < 3

    def commit(self):
        self.status = "COMMITTED"

    def rollback(self):
        self.status = "ABORTED"
        self.write_set = {}

    def __str__(self):
        return f"Transaction({self.tid}, {self.status})"