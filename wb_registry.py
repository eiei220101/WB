"""
登録済み体重（氏名と kg）の読み書き。
"""

from __future__ import annotations

import json
from pathlib import Path

DEFAULT_REGISTRY: list[dict[str, float | str]] = [
    {"name": "山口教官", "weight": 72.0},
    {"name": "羽山教官", "weight": 73.0},
    {"name": "増元教官", "weight": 83.0},
]

PROTECTED_NAMES: frozenset[str] = frozenset(str(e["name"]) for e in DEFAULT_REGISTRY)

_LEGACY_NAME_MAP: dict[str, str] = {
    "増本教官": "増元教官",
}


def registry_path() -> Path:
    return Path(__file__).resolve().parent / "data" / "registered_weights.json"


def is_protected_name(name: str) -> bool:
    return str(name).strip() in PROTECTED_NAMES


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


def _migrate_and_ensure_defaults(entries: list[dict[str, float | str]]) -> list[dict[str, float | str]]:
    migrated: list[dict[str, float | str]] = []
    for entry in entries:
        name = str(entry["name"])
        if name in _LEGACY_NAME_MAP:
            name = _LEGACY_NAME_MAP[name]
        migrated.append({"name": name, "weight": float(entry["weight"])})

    by_name = {str(e["name"]): e for e in migrated}
    for default in DEFAULT_REGISTRY:
        default_name = str(default["name"])
        if default_name not in by_name:
            by_name[default_name] = {"name": default_name, "weight": float(default["weight"])}

    ordered: list[dict[str, float | str]] = []
    seen: set[str] = set()
    for default in DEFAULT_REGISTRY:
        default_name = str(default["name"])
        if default_name in by_name:
            ordered.append(by_name[default_name])
            seen.add(default_name)
    for entry in migrated:
        name = str(entry["name"])
        if name not in seen:
            ordered.append(by_name[name])
            seen.add(name)
    return ordered


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
    if not normalized:
        return list(DEFAULT_REGISTRY)
    result = _migrate_and_ensure_defaults(normalized)
    if result != normalized:
        save_registry(result)
    return result


def save_registry(entries: list[dict[str, float | str]]) -> None:
    path = registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    cleaned = _migrate_and_ensure_defaults(_normalize(entries))
    path.write_text(
        json.dumps(cleaned, ensure_ascii=False, indent=2) + "\n",
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
    if is_protected_name(name):
        return entries
    return [e for e in entries if e["name"] != name]


def deletable_names(entries: list[dict[str, float | str]]) -> list[str]:
    return [str(e["name"]) for e in entries if not is_protected_name(str(e["name"]))]


def registry_as_map(entries: list[dict[str, float | str]]) -> dict[str, float]:
    return {str(e["name"]): float(e["weight"]) for e in entries}
