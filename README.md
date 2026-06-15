# 🧪 ACIDProbe — Database Concurrency Simulator & ACID Detector

AcidProbe is an educational, interactive database concurrency simulator designed to visualize and analyze transactional isolation and conflict serializability. It demonstrates core database concepts such as **Multi-Version Concurrency Control (MVCC)**, **Two-Phase Locking (2PL)**, **Deadlock Detection/Resolution**, and **Conflict Serializability**.

The project features a premium, responsive Streamlit dashboard with step-by-step execution traces, concurrent timeline lanes, anomaly detection audits, Graphviz-based precedence and wait-for graphs, and MVCC version history logs.

---

## 🚀 Key Features

*   **Custom MVCC Engine**: A Multi-Version Concurrency Control data store managing version chains and implementing snapshot visibility rules for different isolation levels.
*   **Pessimistic Locking (2PL)**: A lock manager supporting Shared (`S`) and Exclusive (`X`) lock types, lock compatibility checks, lock upgrading, and active lock state logging.
*   **Deadlock Manager**: Automatically tracks transaction dependencies via a Wait-For Graph, detects cycles using Depth-First Search (DFS), and resolves deadlocks by aborting the youngest transaction.
*   **Anomaly Detection**: Monitors operations in real-time to identify database anomalies like *Dirty Reads*, *Non-Repeatable Reads*, and *Lost Updates*.
*   **Serializability Checker**: Builds a Precedence (Conflict) Graph based on data conflicts and checks if the concurrent schedule is conflict-serializable.
*   **Visual Web Dashboard**: Interactive Streamlit UI containing step-by-step trace views, dynamic timeline lane visualizations, live anomaly report metrics, Graphviz precedence/wait-for graphs, and MVCC version table outputs.

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
├── config.json                  # Workspace custom transaction scenario config
├── streamlit_app.py             # Streamlit application UI and visual runner
├── .gitignore                   # Ignores pycache and virtual environments
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

2. Install dependencies (uses the `streamlit`, `pandas`, and `plotly` libraries):
   ```bash
   pip install streamlit pandas plotly
   ```

---

## 💻 Running the Simulator UI

Start the Streamlit dashboard by running the following command in the project root:

```bash
streamlit run streamlit_app.py
```

This launches the web interface (by default at `http://localhost:8501`), where you can:
1. **Choose scenarios** from the sidebar dropdown (UPI Payment conflicts, deadlock race conditions, ticket overbooking, inventory checkout overselling, or side-by-side isolation level comparisons).
2. **Define custom scenarios** by editing the local `config.json` file in your workspace, or by pasting custom JSON directly into the sidebar text area.
3. Inspect step execution logs, interactive transaction swim lanes, serializability cycle paths, lock wait-for graphs, and MVCC versions dynamically.

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

| Isolation Level | Dirty Read | Non-Repeatable Read | Lost Update |
| :--- | :---: | :---: | :---: |
| **READ UNCOMMITTED** | ❌ Allowed | ❌ Allowed | ❌ Allowed |
| **READ COMMITTED** | ✅ Prevented | ❌ Allowed | ❌ Allowed |
| **REPEATABLE READ** | ✅ Prevented | ✅ Prevented | ❌ Allowed |
| **SERIALIZABLE** | ✅ Prevented | ✅ Prevented | ✅ Prevented |

---

### 3. Conflict Serializability (Precedence Graph)
Determined in [core/serializable_checker.py](./core/serializable_checker.py). It detects conflicts between any two transactions $T_i$ and $T_j$ accessing the same resource $Q$:
*   $T_i$ reads $Q$, $T_j$ writes $Q$ (Read-Write conflict)
*   $T_i$ writes $Q$, $T_j$ reads $Q$ (Write-Read conflict)
*   $T_i$ writes $Q$, $T_j$ writes $Q$ (Write-Write conflict)

If a cycle exists in the precedence graph, the schedule is **not serializable**.
