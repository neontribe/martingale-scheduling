import typer
from .core import do_task
from .config import Settings

app = typer.Typer()

@app.command()
def run(
    data_dir: str = typer.Option("data/", help="Path to your data directory"),
):
    """Run the main task."""
    settings = Settings()
    do_task(data_dir, settings)

if __name__ == "__main__":
    app()
