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
        self.status     = "ACTIVE"  # ACTIVE, WAITING, COMMITTED, ABORTED
        self.read_set   = {}
        self.write_set  = {}
        self.wait_key   = None      # key we are waiting on
        self.wait_lock_type = None  # S or X lock type

    def isolation_level(self):
        return self.ISOLATION_LEVELS.get(self.isolation, 1)

    def allows_dirty_read(self):
        return self.isolation_level() < 1

    def allows_non_repeatable_read(self):
        return self.isolation_level() < 2

    def allows_phantom_read(self):
        return self.isolation_level() < 3

    def commit(self):
        if self.status == "ABORTED":
            raise ValueError(f"Cannot commit aborted transaction {self.tid}")
        if self.status == "COMMITTED":
            return
        self.status = "COMMITTED"
        self.wait_key = None
        self.wait_lock_type = None

    def rollback(self):
        if self.status == "COMMITTED":
            raise ValueError(f"Cannot abort committed transaction {self.tid}")
        if self.status == "ABORTED":
            return
        self.status = "ABORTED"
        self.wait_key = None
        self.wait_lock_type = None

    def __str__(self):
        return f"Transaction({self.tid}, {self.status})"