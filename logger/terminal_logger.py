from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

console = Console()

class Logger:

    # ─────────────────────────────────────
    # HEADER
    # ─────────────────────────────────────
    def print_header(self, scenario, isolation):
        console.print()
        console.print(Panel.fit(
            f"[bold cyan]AcidProbe — ACID Violation Detector[/bold cyan]\n"
            f"[white]Scenario  : {scenario}[/white]\n"
            f"[white]Isolation : {isolation}[/white]",
            border_style="cyan"
        ))

    # ─────────────────────────────────────
    # INITIAL STATE
    # ─────────────────────────────────────
    def print_initial_state(self, key, value):
        console.print()
        console.print(f"[bold white]Initial State:[/bold white]")
        console.print(f"  [cyan]{key}[/cyan] = [green]{value}[/green]")

    # ─────────────────────────────────────
    # SECTION HEADER
    # ─────────────────────────────────────
    def print_section(self, title):
        console.print()
        console.rule(f"[bold yellow]{title}[/bold yellow]")

    # ─────────────────────────────────────
    # STEP LOG
    # ─────────────────────────────────────
    def log_step(self, step_num, tid, operation, key, value=None, status="ok"):
        step  = f"[bold white][STEP {step_num}][/bold white]"
        txn   = f"[bold cyan]{tid}[/bold cyan]"
        op    = f"[bold]{operation}[/bold]"
        k     = f"[yellow]{key}[/yellow]"

        if status == "ok":
            icon = "[green]✅[/green]"
        elif status == "wait":
            icon = "[yellow]⏳[/yellow]"
        elif status == "anomaly":
            icon = "[red]⚠️ [/red]"
        else:
            icon = ""

        if value is not None:
            console.print(f"  {step} {txn}  {op}  {k}  →  [green]{value}[/green]  {icon}")
        else:
            console.print(f"  {step} {txn}  {op}  {k}  {icon}")

    # ─────────────────────────────────────
    # LOCK LOG
    # ─────────────────────────────────────
    def log_lock(self, message, status="ok"):
        if status == "ok":
            console.print(f"    [green]🔒 {message}[/green]")
        elif status == "wait":
            console.print(f"    [yellow]⏳ {message}[/yellow]")
        elif status == "release":
            console.print(f"    [blue]🔓 {message}[/blue]")
        elif status == "deadlock":
            console.print(f"    [red]💀 {message}[/red]")

    # ─────────────────────────────────────
    # COMMIT / ROLLBACK
    # ─────────────────────────────────────
    def log_commit(self, tid):
        console.print(f"    [green]✅ {tid} COMMITTED[/green]")

    def log_rollback(self, tid):
        console.print(f"    [red]❌ {tid} ROLLED BACK[/red]")

    def log_blocked(self, tid, reason):
        console.print(f"    [yellow]⏳ {tid} BLOCKED — {reason}[/yellow]")

    # ─────────────────────────────────────
    # ANOMALY BOX
    # ─────────────────────────────────────
    def log_anomaly(self, anomaly_type, description, fix):
        content = (
            f"[red bold]{anomaly_type} DETECTED[/red bold]\n\n"
            f"[white]{description}[/white]\n\n"
            f"[green]💡 Fix: {fix}[/green]"
        )
        console.print()
        console.print(Panel(
            content,
            border_style="red",
            title="[red]⚠️  ANOMALY[/red]",
            title_align="left"
        ))

    # ─────────────────────────────────────
    # FINAL STATE
    # ─────────────────────────────────────
    def print_final_state(self, actual, expected, key="balance"):
        console.print()
        console.print(f"[bold white]Final State:[/bold white]")
        console.print(f"  {key} in DB   = [red]{actual}[/red]  ❌")
        console.print(f"  Expected      = [green]{expected}[/green]")
        console.print(f"  Lost          = [red]{actual - expected}[/red]")

    # ─────────────────────────────────────
    # ANOMALY REPORT TABLE
    # ─────────────────────────────────────
    def print_anomaly_report(self, detected_types):
        console.print()
        table = Table(
            title="Anomaly Detection Report",
            box=box.ROUNDED,
            border_style="cyan",
            title_style="bold cyan"
        )
        table.add_column("Anomaly",   style="white",  width=25)
        table.add_column("Status",    style="white",  width=20)
        table.add_column("Fix",       style="green",  width=30)

        all_anomalies = {
            "DIRTY READ":           "Use READ COMMITTED",
            "NON-REPEATABLE READ":  "Use REPEATABLE READ",
            "PHANTOM READ":         "Use SERIALIZABLE",
            "LOST UPDATE":          "Use REPEATABLE READ",
        }

        for name, fix in all_anomalies.items():
            if name in detected_types:
                table.add_row(name, "[red]⚠️  DETECTED[/red]", fix)
            else:
                table.add_row(name, "[green]✅ NOT DETECTED[/green]", "-")

        console.print(table)

    # ─────────────────────────────────────
    # SERIALIZABILITY RESULT
    # ─────────────────────────────────────
    def print_serializable_result(self, graph, cycle, cycle_path=None):
        console.print()

        # print graph
        console.print("[bold white]Precedence Graph:[/bold white]")
        for node, neighbors in graph.items():
            for n in neighbors:
                console.print(f"  [cyan]{node}[/cyan] ──→ [cyan]{n}[/cyan]")

        console.print()

        if cycle:
            path_str = " → ".join(cycle_path) if cycle_path else "cycle"
            console.print(Panel(
                f"[red bold]Schedule is NOT SERIALIZABLE[/red bold]\n\n"
                f"[white]Cycle found : [yellow]{path_str}[/yellow][/white]\n\n"
                f"[white]Concurrent execution produced a result[/white]\n"
                f"[white]no serial order could reproduce.[/white]\n\n"
                f"[green]💡 Fix: Use SERIALIZABLE isolation level[/green]",
                border_style="red",
                title="[red]⚠️  SERIALIZABILITY CHECK[/red]",
                title_align="left"
            ))
        else:
            console.print(Panel(
                f"[green bold]Schedule is SERIALIZABLE ✅[/green bold]\n\n"
                f"[white]No cycle found in precedence graph.[/white]\n"
                f"[white]Concurrent execution is safe.[/white]",
                border_style="green",
                title="[green]✅ SERIALIZABILITY CHECK[/green]",
                title_align="left"
            ))

    # ─────────────────────────────────────
    # VERSIONS TABLE
    # ─────────────────────────────────────
    def print_versions(self, key, versions):
        console.print()
        table = Table(
            title=f"MVCC Versions of '{key}'",
            box=box.SIMPLE,
            border_style="blue"
        )
        table.add_column("Value",       style="green")
        table.add_column("Timestamp",   style="cyan")
        table.add_column("Created By",  style="yellow")

        for v in versions:
            table.add_row(str(v["value"]), str(v["ts"]), v["by"])

        console.print(table)
