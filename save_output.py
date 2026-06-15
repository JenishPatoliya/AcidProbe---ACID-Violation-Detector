import os
import re
import subprocess
import io
from rich.console import Console
from rich.ansi import AnsiDecoder

# Make sure outputs directory exists
os.makedirs("outputs", exist_ok=True)

scenarios = {
    "banking":   "1",
    "deadlock":  "5",
    "isolation": "6",
}

print("Saving outputs...")

# Regular expression to strip ANSI escape codes for clean text files
ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

for name, option in scenarios.items():
    print(f"Saving {name}...")

    # Force terminal colors when capturing redirected output
    env = os.environ.copy()
    env["FORCE_COLOR"] = "1"

    # Run scenario and capture output
    result = subprocess.run(
        ["python", "-X", "utf8", "acidprobe.py"],
        input=f"{option}\n\n0\n",
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env
    )

    # 1. Save raw text output with ANSI colors stripped
    plain_text = ANSI_ESCAPE.sub('', result.stdout)
    with open(f"outputs/{name}.txt", "w", encoding="utf-8") as f:
        f.write(plain_text)
    print(f"   ✅ Saved outputs/{name}.txt")

    # 2. Save beautiful colorized HTML output
    # We use a dummy file stream so Console printing doesn't pollute the terminal
    dummy_stream = io.StringIO()
    html_console = Console(record=True, width=120, file=dummy_stream, force_terminal=True)
    
    decoder = AnsiDecoder()
    for line in decoder.decode(result.stdout):
        html_console.print(line)
        
    html_console.save_html(f"outputs/{name}.html")
    print(f"   ✅ Saved outputs/{name}.html")

print("\nAll outputs saved in outputs/ folder!")
print("Open any .html or .txt file to see saved output.")
