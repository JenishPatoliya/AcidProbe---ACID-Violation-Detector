# 🧪 AcidProbe — ACID Violation Detector & Concurrency Simulator

AcidProbe is a lightweight, educational Python-based simulator designed to model, detect, and resolve concurrency issues in database systems. It demonstrates core transactional concepts such as **Multi-Version Concurrency Control (MVCC)**, **Two-Phase Locking (2PL)**, **Deadlock Detection/Resolution**, and **Conflict Serializability**.

The project features rich terminal visualizations for execution steps, transaction states, lock allocations, wait-for dependency graphs, and anomaly reports.

---

## 🚀 Key Features

*   **Custom MVCC Engine**: A Multi-Version Concurrency Control data store that manages version chains and implements snapshot visibility rules for different isolation levels.
*   **Pessimistic Locking (2PL)**: A lock manager that supports Shared (`S`) and Exclusive (`X`) lock types, lock compatibility checks, and lock upgrading.
*   **Deadlock Manager**: Automatically tracks transaction dependencies via a Wait-For Graph, detects cycles using Depth-First Search (DFS), and resolves deadlocks by aborting the youngest transaction.
*   **Anomaly Detection**: Monitors operations in real-time to identify database anomalies:
    *   *Dirty Reads*
    *   *Non-Repeatable Reads*
    *   *Lost Updates*
    *   *Phantom Reads*
*   **Serializability Checker**: Builds a Precedence (Conflict) Graph based on data conflicts and checks if the concurrent schedule is equivalent to a serial schedule.

---

## 📂 Project Structure

```bash
AcidProb/
├── core/
│   ├── data_store.py            # MVCC engine and version control
│   ├── detector.py              # Anomaly detection checks
│   ├── lock_manager.py          # Lock table, Wait-For Graph, DFS Deadlock checker
│   ├── serializable_checker.py  # Conflict serializability graph and cycle checker
│   └── transaction.py           # Transaction models and isolation properties
├── logger/
│   └── terminal_logger.py       # Rich terminal printing utilities
├── scenarios/
│   ├── deadlock_demo.py         # Simulates and resolves a deadlock scenario
│   └── isolation_switcher.py    # Runs the same banking withdrawal under all 4 isolation levels
├── main.py                      # Default Banking Withdrawal simulation entry point
├── .gitignore                   # Ignores pycache and environments
└── README.md                    # Project documentation
```

---

## 🛠️ Getting Started

### Prerequisites

*   Python 3.12+
*   `pip` package manager

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/JenishPatoliya/AcidProbe---ACID-Violation-Detector.git
   cd AcidProbe---ACID-Violation-Detector
   ```

2. Install dependencies (uses the `rich` library for terminal formatting):
   ```bash
   pip install rich
   ```

---

## 💻 Running the Simulations

### 1. Default Banking Scenario (Lost Update check under READ COMMITTED)
Runs the simulation where two transactions withdraw from the same balance concurrently under the `READ COMMITTED` isolation level, demonstrating a **Lost Update** and a **Non-Repeatable Read**.

```bash
python main.py
```

### 2. Isolation Switcher Scenario
Executes the concurrent withdrawal scenario under all four ANSI SQL isolation levels (`READ UNCOMMITTED`, `READ COMMITTED`, `REPEATABLE READ`, and `SERIALIZABLE`) and outputs a side-by-side comparison table showing which anomalies are prevented.

```bash
python scenarios/isolation_switcher.py
```

### 3. Deadlock Demo
Simulates a classic deadlock scenario where:
*   `T1` holds a lock on `balance` and waits for `account`.
*   `T2` holds a lock on `account` and waits for `balance`.

It displays the deadlock detection, visualizes the Wait-For Graph, selects the youngest transaction (`T2`) to abort, releases its locks, and allows `T1` to complete.

```bash
python scenarios/deadlock_demo.py
```

---

## 📚 Core Database Concepts Simulated

### 1. Concurrency Control Mechanisms

#### Multi-Version Concurrency Control (MVCC)
In [core/data_store.py](./core/data_store.py), database records are stored as lists of versions:
```python
{"value": value, "ts": timestamp, "by": tx_id, "committed": bool}
```
Depending on the active isolation level, the transaction reads either uncommitted values, the latest committed value, or snapshot values tied to its starting timestamp (`start_ts`).

#### Two-Phase Locking (2PL)
In [core/lock_manager.py](./core/lock_manager.py), transactions request `S` or `X` locks before reading or writing data. An `S` lock is compatible with other `S` locks, but an `X` lock blocks all other readers and writers.

---

### 2. Transaction Isolation Levels

| Isolation Level | Dirty Read | Non-Repeatable Read | Lost Update | Phantom Read |
| :--- | :---: | :---: | :---: | :---: |
| **READ UNCOMMITTED** | ❌ Allowed | ❌ Allowed | ❌ Allowed | ❌ Allowed |
| **READ COMMITTED** | ✅ Prevented | ❌ Allowed | ❌ Allowed | ❌ Allowed |
| **REPEATABLE READ** | ✅ Prevented | ✅ Prevented | ❌ Allowed | ❌ Allowed |
| **SERIALIZABLE** | ✅ Prevented | ✅ Prevented | ✅ Prevented | ✅ Prevented |

---

### 3. Conflict Serializability (Precedence Graph)
Determined in [core/serializable_checker.py](./core/serializable_checker.py). It detects conflicts between any two transactions $T_i$ and $T_j$ accessing the same resource $Q$:
*   $T_i$ reads $Q$, $T_j$ writes $Q$ (Read-Write conflict)
*   $T_i$ writes $Q$, $T_j$ reads $Q$ (Write-Read conflict)
*   $T_i$ writes $Q$, $T_j$ writes $Q$ (Write-Write conflict)

If a cycle exists in the precedence graph, the schedule is **not serializable**.
