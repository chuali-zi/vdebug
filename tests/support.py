from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from shutil import rmtree
from uuid import uuid4


@contextmanager
def repo_temp_dir(prefix: str):
    root = Path.cwd() / ".test_tmp"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{prefix}-{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    try:
        yield path
    finally:
        rmtree(path, ignore_errors=True)
