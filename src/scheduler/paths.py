# this file involves relative paths.
from __future__ import annotations
from pathlib import Path
import sys
import shutil

# ---------- RESOURCES (read-only, bundled with the app) ----------
def resource_path(*rel: str | Path) -> Path:
    """
    Resolve a path to a *bundled* resource (works in dev and PyInstaller).
    Use for reading defaults/templates shipped with the app.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)  # PyInstaller extraction dir
    else:
        base = Path(__file__).resolve().parent  # folder of this file (package)
    return (base.joinpath(*map(Path, rel))).resolve()

# ---------- RUNTIME (read/write, user’s current directory) ----------
def runtime_path(*rel: str | Path) -> Path:
    """
    Resolve a path relative to the *current working directory* (CWD).
    Use for anything you *write* (outputs, caches, logs) or user-provided inputs.
    """
    return (Path.cwd().joinpath(*map(Path, rel))).resolve()

def ensure_dir(p: str | Path) -> Path:
    """Create a directory if missing and return it."""
    p = Path(p)
    p.mkdir(parents=True, exist_ok=True)
    return p

# ---------- Optional: seed a runtime folder from bundled templates ----------
def seed_dir_from_resource(resource_subdir: str | Path, runtime_subdir: str | Path) -> Path:
    """
    Copy contents from a bundled resource folder into a runtime folder *iff* the
    runtime folder is empty. Safe to call multiple times.
    """
    src = resource_path(resource_subdir)
    dst = ensure_dir(runtime_path(runtime_subdir))
    if src.exists() and src.is_dir() and not any(dst.iterdir()):
        for item in src.iterdir():
            target = dst / item.name
            if item.is_dir():
                shutil.copytree(item, target, dirs_exist_ok=True)
            else:
                shutil.copy2(item, target)
    return dst
