"""Small on-disk JSON cache (one file per key)."""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any


def ttl() -> float:
    try:
        return float(os.environ.get("GHTUI_CACHE_TTL", "300"))
    except ValueError:
        return 300.0


def cache_dir() -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "ghtui"


def _path(key: str) -> Path:
    return cache_dir() / (re.sub(r"[^A-Za-z0-9._-]", "__", key) + ".json")


def get(key: str) -> tuple[list[dict], float] | None:
    try:
        data = json.loads(_path(key).read_text())
        items, ts = data["items"], float(data["ts"])
        if not isinstance(items, list):
            return None
        return items, ts
    except (OSError, ValueError, KeyError, TypeError):
        return None


def put(key: str, items: list[dict]) -> None:
    path = _path(key)
    tmp = path.with_suffix(f".{os.getpid()}.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps({"ts": time.time(), "items": items}))
        os.replace(tmp, path)
    except OSError:
        try:
            tmp.unlink()
        except OSError:
            pass


def is_fresh(ts: float) -> bool:
    return time.time() - ts < ttl()


def age_text(ts: float) -> str:
    s = max(0, int(time.time() - ts))
    if s < 60:
        return f"{s}s"
    if s < 3600:
        return f"{s // 60}m"
    if s < 86400:
        return f"{s // 3600}h"
    return f"{s // 86400}d"


def clear() -> None:
    d = cache_dir()
    if d.is_dir():
        for f in d.glob("*.json"):
            try:
                f.unlink()
            except OSError:
                pass
