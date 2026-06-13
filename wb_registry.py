"""
登録済み体重（氏名と kg）の読み書き。
"""

from __future__ import annotations

import json
from pathlib import Path

DEFAULT_REGISTRY: list[dict[str, float | str]] = [
    {"name": "山口教官", "weight": 72.0},
    {"name": "羽山教官", "weight": 73.0},
    {"name": "増本教官", "weight": 83.0},
]


def registry_path() -> Path:
    return Path(__file__).resolve().parent / "data" / "registered_weights.json"


def _normalize(entries: list) -> list[dict[str, float | str]]:
    out: list[dict[str, float | str]] = []
    for item in entries:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        try:
            weight = round(float(item.get("weight", 0.0)), 1)
        except (TypeError, ValueError):
            continue
        out.append({"name": name, "weight": weight})
    return out


def load_registry() -> list[dict[str, float | str]]:
    path = registry_path()
    if not path.exists():
        return list(DEFAULT_REGISTRY)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return list(DEFAULT_REGISTRY)
    if not isinstance(raw, list):
        return list(DEFAULT_REGISTRY)
    normalized = _normalize(raw)
    return normalized if normalized else list(DEFAULT_REGISTRY)


def save_registry(entries: list[dict[str, float | str]]) -> None:
    path = registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_normalize(entries), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def upsert_entry(entries: list[dict[str, float | str]], name: str, weight: float) -> list[dict[str, float | str]]:
    name = name.strip()
    if not name:
        return entries
    w = round(float(weight), 1)
    for entry in entries:
        if entry["name"] == name:
            entry["weight"] = w
            return entries
    return entries + [{"name": name, "weight": w}]


def remove_entry(entries: list[dict[str, float | str]], name: str) -> list[dict[str, float | str]]:
    return [e for e in entries if e["name"] != name]


def registry_as_map(entries: list[dict[str, float | str]]) -> dict[str, float]:
    return {str(e["name"]): float(e["weight"]) for e in entries}
