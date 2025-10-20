from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Optional

import typer

import tomllib

from scheduler.paths import resource_path, ensure_dir, runtime_path
from scheduler.core import do_task


app = typer.Typer(add_completion=False, help="Martingale Scheduler CLI")

# -------------------------
# Helpers
# -------------------------

def deep_merge(base: dict, overrides: dict) -> dict:
    out = dict(base)
    for k, v in overrides.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out

def parse_kv_list(items: List[str]) -> Dict[str, object]:
    """
    Parse repeated --override key=value pairs, supporting dot-keys for nesting.
    Example: --override server.port=8080 --override log.level=INFO
    """
    out: Dict[str, object] = {}
    for item in items:
        if "=" not in item:
            raise typer.BadParameter(f"Expected key=value, got: {item}")
        key, val = item.split("=", 1)

        # simple coercion: bool, int, float, else str
        if val.lower() in {"true", "false"}:
            coerced: object = val.lower() == "true"
        else:
            try:
                coerced = int(val)
            except ValueError:
                try:
                    coerced = float(val)
                except ValueError:
                    coerced = val

        # nest by dot-keys
        cursor = out
        parts = key.split(".")
        for p in parts[:-1]:
            nxt = cursor.get(p)
            if not isinstance(nxt, dict):
                nxt = {}
                cursor[p] = nxt
            cursor = nxt
        cursor[parts[-1]] = coerced
    return out

def load_config(config_path: Optional[Path]) -> dict:
    """
    Load a TOML config. If not provided, load bundled default at scheduler.toml.
    """
    if config_path is None:
        config_path = resource_path("scheduler.toml")

    with open(config_path, "rb") as f:
        return tomllib.load(f)

# -------------------------
# CLI
# -------------------------
@app.callback()
def main(
    ctx: typer.Context,
    config: Optional[Path] = typer.Option(
        None, "--config", "-c", exists=True, readable=True,
        help="Path to a config file (defaults to bundled scheduler.toml).",
    ),
    override: List[str] = typer.Option(
        [], "--override", "-o",
        help="Override config via key=value (repeatable)",
    ),
    debug: bool = typer.Option(
        False, "--debug", help="Enable debug logging",
        envvar="SCHEDULER_DEBUG",
    ),
):
    """
    Parse global config early and store the merged result in ctx.obj.
    Commands can then read ctx.obj for settings.
    """
    cfg = load_config(config)
    ov = parse_kv_list(override)
    if debug:
        ov = deep_merge(ov, {"log": {"level": "DEBUG"}})
    cfg = deep_merge(cfg, ov)
    ctx.obj = cfg

@app.command()
def run(ctx: typer.Context):
    cfg: dict = ctx.obj
    data_dir = cfg["general"]["data_dir"]
    output_dir = cfg["general"]["output_dir"]
    ensure_dir(runtime_path(data_dir))
    ensure_dir(runtime_path(output_dir))

    """
    Run the main task.
    """
    print(f"Running from {data_dir} outputting to {output_dir}")
    do_task(cfg)

# Optional explicit entrypoint for `python -m scheduler.cli`
def main_entry() -> None:
    app()

if __name__ == "__main__":
    app()
