import sys
import json
from rich.console import Console
from rich.panel import Panel

console = Console()

def show_menu():
    console.print()
    console.print(Panel.fit(
        "[bold cyan]🔬 AcidProbe — ACID Violation Detector[/bold cyan]\n"
        "[white]Choose a scenario to simulate[/white]",
        border_style="cyan"
    ))
    console.print()
    console.print("  [cyan]1[/cyan]  →  UPI Payment (Lost Update Check)")
    console.print("  [cyan]2[/cyan]  →  Bank Transfer Race (Opposite-Order Deadlock Check)")
    console.print("  [cyan]3[/cyan]  →  Ticket Booking (Overbooking Check)")
    console.print("  [cyan]4[/cyan]  →  Inventory Overselling (Concurrent Checkout Check)")
    console.print("  [cyan]5[/cyan]  →  Deadlock Demo (Graph Resolution Demo)")
    console.print("  [cyan]6[/cyan]  →  Isolation Level Switcher (Side-by-Side Comparison)")
    console.print("  [cyan]7[/cyan]  →  Load config.json (Custom File)")
    console.print("  [cyan]0[/cyan]  →  Exit")
    console.print()

def main():
    if len(sys.argv) > 1:
        if "--config" in sys.argv:
            try:
                idx = sys.argv.index("--config")
                config_path = sys.argv[idx + 1]
                with open(config_path) as f:
                    config = json.load(f)
                from core.scenario_runner import ScenarioRunner
                ScenarioRunner().run(config)
                return
            except Exception as e:
                console.print(f"[red]Error loading config: {e}[/red]")
                return

    while True:
        show_menu()
        choice = input("  Choose option: ").strip()

        if choice == "0":
            console.print("\n[cyan]Goodbye! 👋[/cyan]\n")
            break

        elif choice == "1":
            config = {
                "scenario_name": "UPI Payment Concurrent Withdrawals",
                "isolation_level": "READ_COMMITTED",
                "initial_data": {"account_balance": 500},
                "transactions": [
                    {"tid": "T1", "operations": [
                        {"op": "READ",  "key": "account_balance"},
                        {"op": "WRITE", "key": "account_balance", "value": 200},
                        {"op": "COMMIT"}
                    ]},
                    {"tid": "T2", "operations": [
                        {"op": "READ",  "key": "account_balance"},
                        {"op": "WRITE", "key": "account_balance", "value": 200},
                        {"op": "COMMIT"}
                    ]}
                ]
            }
            from core.scenario_runner import ScenarioRunner
            ScenarioRunner().run(config)

        elif choice == "2":
            config = {
                "scenario_name": "Bank Transfer Race Condition",
                "isolation_level": "READ_COMMITTED",
                "initial_data": {"accA": 1000, "accB": 1000},
                "transactions": [
                    {"tid": "T1", "operations": [
                        {"op": "READ",  "key": "accA"},
                        {"op": "WRITE", "key": "accA", "value": 800},
                        {"op": "READ",  "key": "accB"},
                        {"op": "WRITE", "key": "accB", "value": 1200},
                        {"op": "COMMIT"}
                    ]},
                    {"tid": "T2", "operations": [
                        {"op": "READ",  "key": "accB"},
                        {"op": "WRITE", "key": "accB", "value": 900},
                        {"op": "READ",  "key": "accA"},
                        {"op": "WRITE", "key": "accA", "value": 1100},
                        {"op": "COMMIT"}
                    ]}
                ]
            }
            from core.scenario_runner import ScenarioRunner
            ScenarioRunner().run(config)

        elif choice == "3":
            config = {
                "scenario_name": "Ticket Booking Concurrency",
                "isolation_level": "READ_COMMITTED",
                "initial_data": {"seat_1A": 100},  # 100 means AVAILABLE
                "transactions": [
                    {"tid": "T1", "operations": [
                        {"op": "READ",  "key": "seat_1A"},
                        {"op": "WRITE", "key": "seat_1A", "value": 1},  # 1 means BOOKED_T1
                        {"op": "COMMIT"}
                    ]},
                    {"tid": "T2", "operations": [
                        {"op": "READ",  "key": "seat_1A"},
                        {"op": "WRITE", "key": "seat_1A", "value": 2},  # 2 means BOOKED_T2
                        {"op": "COMMIT"}
                    ]}
                ]
            }
            from core.scenario_runner import ScenarioRunner
            ScenarioRunner().run(config)

        elif choice == "4":
            config = {
                "scenario_name": "Inventory Overselling Stress Test",
                "isolation_level": "READ_COMMITTED",
                "initial_data": {"stock": 10},
                "transactions": [
                    {"tid": "T1", "operations": [
                        {"op": "READ",  "key": "stock"},
                        {"op": "WRITE", "key": "stock", "value": 2},
                        {"op": "COMMIT"}
                    ]},
                    {"tid": "T2", "operations": [
                        {"op": "READ",  "key": "stock"},
                        {"op": "WRITE", "key": "stock", "value": 5},
                        {"op": "COMMIT"}
                    ]}
                ]
            }
            from core.scenario_runner import ScenarioRunner
            ScenarioRunner().run(config)

        elif choice == "5":
            from scenarios.deadlock_demo import run
            run()

        elif choice == "6":
            from scenarios.isolation_switcher import run
            run()

        elif choice == "7":
            try:
                with open("config.json") as f:
                    config = json.load(f)
                from core.scenario_runner import ScenarioRunner
                ScenarioRunner().run(config)
            except FileNotFoundError:
                console.print("[red]config.json not found![/red]")

        else:
            console.print("[red]Invalid option — try again[/red]")

        input("\n  Press Enter to return to menu...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[cyan]Goodbye! 👋[/cyan]\n")
