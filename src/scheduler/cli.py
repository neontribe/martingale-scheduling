import typer
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.scheduler.core import do_task
import time
import traceback


app = typer.Typer()

@app.command()
def run(
    data_dir: str = typer.Option("data/", help="Path to your data directory"),
):
    """Run the main task."""
    do_task(data_dir)

if __name__ == "__main__":
    try:
        app()
    except Exception as e:
        print("An error occurred:")
        traceback.print_exc() 
        time.sleep(10)
