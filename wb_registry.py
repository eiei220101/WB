"""
登録済み体重（氏名と kg）の読み書き。
"""

from __future__ import annotations

import json
import os
from pathlib import Path

AFFILIATION_OPTIONS: tuple[str, ...] = ("桜美林", "一般", "JCAB")
DEFAULT_AFFILIATION = "一般"
OHIBIRIN_COHORT_OPTIONS: tuple[str, ...] = tuple(f"{n}期" for n in range(15, 26))
DEFAULT_OHIBIRIN_COHORT = "15期"
OHIBIRIN_AFFILIATION = "桜美林"

AFFILIATION_COLORS: dict[str, str] = {
    OHIBIRIN_AFFILIATION: "#a21caf",
    DEFAULT_AFFILIATION: "#1d4ed8",
    "JCAB": "#15803d",
}
INSTRUCTOR_COLOR = "#dc2626"

DEFAULT_REGISTRY: list[dict[str, float | str]] = [
    {"name": "山口教官", "weight": 72.0, "affiliation": DEFAULT_AFFILIATION},
    {"name": "羽山教官", "weight": 73.0, "affiliation": DEFAULT_AFFILIATION},
    {"name": "増元教官", "weight": 83.0, "affiliation": DEFAULT_AFFILIATION},
]

PROTECTED_NAMES: frozenset[str] = frozenset(str(e["name"]) for e in DEFAULT_REGISTRY)

_LEGACY_NAME_MAP: dict[str, str] = {
    "増本教官": "増元教官",
}


_LEGACY_REGISTRY_PATH = Path.home() / ".da42_wb" / "registered_weights.json"


def registry_path() -> Path:
    override = os.environ.get("WB_REGISTRY_PATH", "").strip()
    if override:
        return Path(override).expanduser()
    return Path(__file__).resolve().parent / "data" / "registered_weights.json"


def legacy_registry_path() -> Path:
    return _LEGACY_REGISTRY_PATH


def bundled_registry_path() -> Path:
    return registry_path()


def _load_bundled_or_defaults() -> list[dict[str, float | str]]:
    return _migrate_and_ensure_defaults(list(DEFAULT_REGISTRY))


def _merge_registry_entries(*groups: list[dict[str, float | str]]) -> list[dict[str, float | str]]:
    by_name: dict[str, dict[str, float | str]] = {}
    for group in groups:
        for entry in group:
            name = str(entry["name"])
            if name in _LEGACY_NAME_MAP:
                name = _LEGACY_NAME_MAP[name]
            by_name[name] = _entry_from_raw(name, entry)
    return _migrate_and_ensure_defaults(list(by_name.values()))


def _read_registry_file(path: Path) -> list[dict[str, float | str]] | None:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(raw, list):
        return None
    return _migrate_and_ensure_defaults(_normalize(raw))


def _write_registry_file(path: Path, entries: list[dict[str, float | str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cleaned = _migrate_and_ensure_defaults(_normalize(entries))
    payload = json.dumps(cleaned, ensure_ascii=False, indent=2) + "\n"
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(payload, encoding="utf-8")
    tmp.replace(path)


def is_protected_name(name: str) -> bool:
    return str(name).strip() in PROTECTED_NAMES


def normalize_affiliation(raw) -> str:
    value = str(raw or DEFAULT_AFFILIATION).strip()
    return value if value in AFFILIATION_OPTIONS else DEFAULT_AFFILIATION


def normalize_cohort(affiliation: str, raw) -> str:
    if affiliation != OHIBIRIN_AFFILIATION:
        return ""
    value = str(raw or DEFAULT_OHIBIRIN_COHORT).strip()
    return value if value in OHIBIRIN_COHORT_OPTIONS else ""


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
        affiliation = normalize_affiliation(item.get("affiliation"))
        out.append(
            {
                "name": name,
                "weight": weight,
                "affiliation": affiliation,
                "cohort": normalize_cohort(affiliation, item.get("cohort")),
            }
        )
    return out


def _entry_from_raw(name: str, entry: dict[str, float | str]) -> dict[str, float | str]:
    affiliation = normalize_affiliation(entry.get("affiliation"))
    return {
        "name": name,
        "weight": float(entry["weight"]),
        "affiliation": affiliation,
        "cohort": normalize_cohort(affiliation, entry.get("cohort")),
    }


def _migrate_and_ensure_defaults(entries: list[dict[str, float | str]]) -> list[dict[str, float | str]]:
    migrated: list[dict[str, float | str]] = []
    for entry in entries:
        name = str(entry["name"])
        if name in _LEGACY_NAME_MAP:
            name = _LEGACY_NAME_MAP[name]
        migrated.append(_entry_from_raw(name, entry))

    by_name = {str(e["name"]): e for e in migrated}
    for default in DEFAULT_REGISTRY:
        default_name = str(default["name"])
        if default_name not in by_name:
            by_name[default_name] = _entry_from_raw(default_name, default)
        else:
            by_name[default_name]["affiliation"] = normalize_affiliation(
                by_name[default_name].get("affiliation", default.get("affiliation"))
            )

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
    primary = _read_registry_file(path) if path.exists() else None

    legacy_path = legacy_registry_path()
    legacy = (
        _read_registry_file(legacy_path)
        if legacy_path.exists() and legacy_path.resolve() != path.resolve()
        else None
    )

    if primary is not None and legacy is not None:
        merged = _merge_registry_entries(primary, legacy)
        try:
            _write_registry_file(path, merged)
        except OSError:
            pass
        return merged
    if primary is not None:
        return primary
    if legacy is not None:
        try:
            _write_registry_file(path, legacy)
        except OSError:
            pass
        return legacy

    seeded = _load_bundled_or_defaults()
    try:
        _write_registry_file(path, seeded)
    except OSError:
        pass
    return seeded


def save_registry(entries: list[dict[str, float | str]]) -> None:
    _write_registry_file(registry_path(), entries)


def upsert_entry(
    entries: list[dict[str, float | str]],
    name: str,
    weight: float,
    affiliation: str,
    cohort: str = "",
) -> list[dict[str, float | str]]:
    name = name.strip()
    if not name:
        return list(entries)
    w = round(float(weight), 1)
    aff = normalize_affiliation(affiliation)
    coh = normalize_cohort(aff, cohort)
    updated_entry = {
        "name": name,
        "weight": w,
        "affiliation": aff,
        "cohort": coh if aff == OHIBIRIN_AFFILIATION else "",
    }
    out: list[dict[str, float | str]] = []
    replaced = False
    for entry in entries:
        if str(entry["name"]) == name:
            out.append(updated_entry)
            replaced = True
        else:
            out.append(dict(entry))
    if not replaced:
        out.append(updated_entry)
    return out


def affiliation_color(affiliation: str) -> str:
    return AFFILIATION_COLORS.get(str(affiliation).strip(), "#374151")


def registry_tag_color(entry: dict[str, float | str]) -> str:
    if is_protected_name(str(entry.get("name", ""))):
        return INSTRUCTOR_COLOR
    return affiliation_color(str(entry.get("affiliation", DEFAULT_AFFILIATION)))


def select_option_style_kind(label: str) -> str | None:
    """プルダウン選択肢の所属色キー（ohibirin / jcab / general / instructor）。"""
    text = str(label).strip()
    if not text or text in ("体重を入力/選択", "体重を入力"):
        return None
    if text.startswith("[教官]"):
        return "instructor"
    if text == OHIBIRIN_AFFILIATION or text.startswith("[FO"):
        return "ohibirin"
    if text == "JCAB" or text.startswith("[JCAB]"):
        return "jcab"
    if text == DEFAULT_AFFILIATION or text.startswith("[一般]"):
        return "general"
    return None


def format_affiliation_html(affiliation: str) -> str:
    aff = str(affiliation).strip()
    color = affiliation_color(aff)
    return f'<span style="color:{color};font-weight:700;">{aff}</span>'


def format_registry_tag(entry: dict[str, float | str]) -> str:
    name = str(entry.get("name", "")).strip()
    if is_protected_name(name):
        return "[教官]"
    affiliation = str(entry.get("affiliation", DEFAULT_AFFILIATION))
    if affiliation == OHIBIRIN_AFFILIATION:
        cohort = str(entry.get("cohort", "")).strip()
        if cohort.endswith("期"):
            num = cohort[:-1]
            if num.isdigit():
                return f"[FO{num}]"
        return "[FO]"
    if affiliation == "JCAB":
        return "[JCAB]"
    return "[一般]"


def format_registry_display_html(entry: dict[str, float | str]) -> str:
    tag = format_registry_tag(entry)
    name = str(entry.get("name", "")).strip()
    color = registry_tag_color(entry)
    return (
        f'<span style="color:{color};font-weight:700;">{tag}</span> '
        f'<span style="color:#111827;">{name}</span>'
    )


def format_registry_list_tag(entry: dict[str, float | str]) -> str:
    """登録者一覧用タグ（桜美林は期番号ではなく所属名を表示）。"""
    name = str(entry.get("name", "")).strip()
    if is_protected_name(name):
        return "[教官]"
    affiliation = str(entry.get("affiliation", DEFAULT_AFFILIATION))
    if affiliation == OHIBIRIN_AFFILIATION:
        return "[桜美林]"
    if affiliation == "JCAB":
        return "[JCAB]"
    return "[一般]"


def format_registry_list_item_html(
    entry: dict[str, float | str],
    *,
    unit_weight: str = "kg",
) -> str:
    """登録者一覧用。JCAB のみ体重を横に表示。"""
    tag = format_registry_list_tag(entry)
    name = str(entry.get("name", "")).strip()
    color = registry_tag_color(entry)
    line = (
        f'<span style="color:{color};font-weight:700;">{tag}</span> '
        f'<span style="color:#111827;">{name}</span>'
    )
    if str(entry.get("affiliation", DEFAULT_AFFILIATION)) == "JCAB":
        weight = float(entry.get("weight", 0.0))
        line += f' <span style="color:#4b5563;">{weight:.1f} {unit_weight}</span>'
    return line


AFFILIATION_DISPLAY_ORDER: tuple[str, ...] = (OHIBIRIN_AFFILIATION, DEFAULT_AFFILIATION, "JCAB")

_INSTRUCTOR_NAME_ORDER: dict[str, int] = {
    str(entry["name"]): index for index, entry in enumerate(DEFAULT_REGISTRY)
}


def registry_display_sort_key(entry: dict[str, float | str]) -> tuple[int, int, str]:
    name = str(entry.get("name", ""))
    if is_protected_name(name):
        return (2, _INSTRUCTOR_NAME_ORDER.get(name, 999), name)
    affiliation = str(entry.get("affiliation", DEFAULT_AFFILIATION))
    if affiliation == OHIBIRIN_AFFILIATION:
        aff_order = 0
    elif affiliation == DEFAULT_AFFILIATION:
        aff_order = 1
    elif affiliation == "JCAB":
        aff_order = 3
    else:
        aff_order = 4
    cohort = str(entry.get("cohort", "")).strip()
    if cohort.endswith("期") and cohort[:-1].isdigit():
        cohort_num = int(cohort[:-1])
    else:
        cohort_num = 999
    return (aff_order, cohort_num, name)


def sort_registry_entries_for_display(entries: list[dict[str, float | str]]) -> list[dict[str, float | str]]:
    """登録者一覧の表示順: 桜美林 → 一般 → 教官 → JCAB（教官は山口→羽山→増元）。"""
    return sorted(entries, key=registry_display_sort_key)


def format_registry_display(entry: dict[str, float | str]) -> str:
    name = str(entry.get("name", "")).strip()
    if is_protected_name(name):
        return f"[教官] {name}"
    affiliation = str(entry.get("affiliation", DEFAULT_AFFILIATION))
    if affiliation == OHIBIRIN_AFFILIATION:
        cohort = str(entry.get("cohort", "")).strip()
        if cohort.endswith("期"):
            num = cohort[:-1]
            if num.isdigit():
                return f"[FO{num}] {name}"
        return f"[FO] {name}"
    if affiliation == "JCAB":
        return f"[JCAB] {name}"
    return f"[一般] {name}"


def registry_display_entry_map(entries: list[dict[str, float | str]]) -> dict[str, dict[str, float | str]]:
    return {
        format_registry_display(entry): entry
        for entry in entries
        if not is_protected_name(str(entry["name"]))
    }


def remove_entry(entries: list[dict[str, float | str]], name: str) -> list[dict[str, float | str]]:
    if is_protected_name(name):
        return entries
    return [e for e in entries if e["name"] != name]


def deletable_names(entries: list[dict[str, float | str]]) -> list[str]:
    return [str(e["name"]) for e in entries if not is_protected_name(str(e["name"]))]


def deletable_display_options(entries: list[dict[str, float | str]]) -> list[tuple[str, str]]:
    """削除候補を (表示ラベル, 氏名) で返す。"""
    out: list[tuple[str, str]] = []
    for entry in entries:
        if is_protected_name(str(entry["name"])):
            continue
        out.append((format_registry_display(entry), str(entry["name"])))
    return out


def registry_as_map(entries: list[dict[str, float | str]]) -> dict[str, float]:
    return {str(e["name"]): float(e["weight"]) for e in entries}


def front_right_instructor_names() -> list[str]:
    return [str(e["name"]) for e in DEFAULT_REGISTRY]


def front_right_instructor_display_map(
    entries: list[dict[str, float | str]],
) -> dict[str, float]:
    """Front seat R 用: 表示ラベル -> 体重。"""
    return {
        format_registry_display(entry): float(entry["weight"])
        for entry in entries
        if is_protected_name(str(entry["name"]))
    }


def front_right_instructor_name_to_display(
    entries: list[dict[str, float | str]],
) -> dict[str, str]:
    return {
        str(entry["name"]): format_registry_display(entry)
        for entry in entries
        if is_protected_name(str(entry["name"]))
    }


def front_right_instructor_map(entries: list[dict[str, float | str]]) -> dict[str, float]:
    weights = registry_as_map(entries)
    return {name: weights[name] for name in front_right_instructor_names() if name in weights}


def _seat_entries_for_affiliations(
    entries: list[dict[str, float | str]],
    affiliations: tuple[str, ...],
) -> list[dict[str, float | str]]:
    allowed = set(affiliations)
    out: list[dict[str, float | str]] = []
    for entry in entries:
        if is_protected_name(str(entry["name"])):
            continue
        if str(entry.get("affiliation", DEFAULT_AFFILIATION)) in allowed:
            out.append(entry)
    return out


def seat_selectable_display_map_for_affiliations(
    entries: list[dict[str, float | str]],
    affiliations: tuple[str, ...],
) -> dict[str, float]:
    """指定所属の登録者だけを、表示ラベル -> 体重 で返す。"""
    out: dict[str, float] = {}
    filtered = _seat_entries_for_affiliations(entries, affiliations)
    for entry in sort_registry_entries_for_display(filtered):
        out[format_registry_display(entry)] = float(entry["weight"])
    return out


def seat_name_to_display_map_for_affiliations(
    entries: list[dict[str, float | str]],
    affiliations: tuple[str, ...],
) -> dict[str, str]:
    return {
        str(entry["name"]): format_registry_display(entry)
        for entry in _seat_entries_for_affiliations(entries, affiliations)
    }


FRONT_LEFT_AFFILIATIONS: tuple[str, ...] = (OHIBIRIN_AFFILIATION, DEFAULT_AFFILIATION)
REAR_RIGHT_AFFILIATIONS: tuple[str, ...] = (OHIBIRIN_AFFILIATION, "JCAB")


def seat_selectable_display_map(entries: list[dict[str, float | str]]) -> dict[str, float]:
    """前左・後左・後右席の表示ラベル -> 体重。"""
    out: dict[str, float] = {}
    for entry in entries:
        if is_protected_name(str(entry["name"])):
            continue
        out[format_registry_display(entry)] = float(entry["weight"])
    return out


def seat_name_to_display_map(entries: list[dict[str, float | str]]) -> dict[str, str]:
    """氏名 -> 表示ラベル。"""
    return {
        str(entry["name"]): format_registry_display(entry)
        for entry in entries
        if not is_protected_name(str(entry["name"]))
    }


def seat_selectable_map(entries: list[dict[str, float | str]]) -> dict[str, float]:
    """前左・後左・後右席で選べる登録者（前右席の3教官を除く）。"""
    return {str(e["name"]): float(e["weight"]) for e in entries if not is_protected_name(str(e["name"]))}
