"""
重量・重心（Weight & Balance）の計算だけをまとめたモジュール。
画面（Streamlit）とは分離してあるので、式を変えたいときはここだけ直せばよい。
"""

from typing import Iterable, Mapping


class RowResult:
    """計算結果の1行。"""

    __slots__ = ("name", "weight", "arm", "moment")

    def __init__(self, *, name: str, weight: float, arm: float, moment: float) -> None:
        self.name = name
        self.weight = float(weight)
        self.arm = float(arm)
        self.moment = float(moment)


class Totals:
    """合計値。"""

    __slots__ = ("weight", "moment", "cg")

    def __init__(self, *, weight: float, moment: float, cg) -> None:
        self.weight = float(weight)
        self.moment = float(moment)
        self.cg = None if cg is None else float(cg)


class WBPoint:
    """ある状態（例: ZFM/TOW/LW）の重量・モーメント・CG。"""

    __slots__ = ("weight", "moment", "cg")

    def __init__(self, *, weight: float, moment: float, cg) -> None:
        self.weight = float(weight)
        self.moment = float(moment)
        self.cg = None if cg is None else float(cg)


def moment(weight: float, arm: float) -> float:
    """モーメント = 重量 × アーム"""
    return weight * arm


def cg_from_totals(total_weight: float, total_moment: float):
    """重心位置（アーム）= 総モーメント ÷ 総重量。重量0なら未定義。"""
    if total_weight <= 0:
        return None
    return total_moment / total_weight


def evaluate_rows(rows: Iterable[tuple[str, float, float]]) -> tuple[list[RowResult], Totals]:
    """
    各行のモーメントと、合計重量・合計モーメント・重心を求める。
    """
    results: list[RowResult] = []
    tw = 0.0
    tm = 0.0
    for name, weight, arm in rows:
        w = float(weight)
        a = float(arm)
        m = moment(w, a)
        results.append(RowResult(name=name, weight=w, arm=a, moment=m))
        tw += w
        tm += m
    cg = cg_from_totals(tw, tm)
    return results, Totals(weight=tw, moment=tm, cg=cg)


def within_limits(cg, cg_min, cg_max):
    """
    許容範囲が入力されていれば「範囲内／外」を返す。CGが無ければ None。
    """
    if cg is None:
        return None
    if cg_min is None and cg_max is None:
        return None
    lo = cg_min if cg_min is not None else float("-inf")
    hi = cg_max if cg_max is not None else float("inf")
    if lo <= cg <= hi:
        return "許容範囲内"
    return "許容範囲外（要確認）"


def evaluate_components(components: Mapping[str, tuple[float, float]]) -> tuple[list[RowResult], Totals]:
    """
    components: {name: (weight, arm)}
    """
    rows = [(k, float(v[0]), float(v[1])) for k, v in components.items()]
    return evaluate_rows(rows)


def compute_da42_points(
    *,
    basic_empty_weight: float,
    basic_empty_arm: float,
    arms_mm: Mapping[str, float],
    inputs_weight: Mapping[str, float],
    main_fuel_weight: float,
    taxi_fuel_burn_weight: float,
    flight_fuel_burn_weight: float,
    return_fuel_burn_weight: float = 0.0,
) -> dict[str, WBPoint]:
    """
    DA42向け（固定項目）の ZFM / TOW / LW をまとめて算出。

    重量の単位は、入力側で統一されていることを前提とする。
    燃料消費は「重量換算済み」を入力してもらう（例: kg）。
    """
    fuel_arm = float(arms_mm.get("main_fuel", 0.0))

    def point(*, include_fuel_weight: float) -> WBPoint:
        comps: dict[str, tuple[float, float]] = {
            "Basic Empty": (basic_empty_weight, basic_empty_arm),
            "Front seat L": (float(inputs_weight.get("front_seat_left", 0.0)), float(arms_mm.get("front_seat_left", 0.0))),
            "Front seat R": (float(inputs_weight.get("front_seat_right", 0.0)), float(arms_mm.get("front_seat_right", 0.0))),
            "Rear seat L": (float(inputs_weight.get("rear_seat_left", 0.0)), float(arms_mm.get("rear_seat_left", 0.0))),
            "Rear seat R": (float(inputs_weight.get("rear_seat_right", 0.0)), float(arms_mm.get("rear_seat_right", 0.0))),
            "Nose baggage": (float(inputs_weight.get("nose_baggage", 0.0)), float(arms_mm.get("nose_baggage", 0.0))),
            "Cockpit baggage": (float(inputs_weight.get("cockpit_baggage", 0.0)), float(arms_mm.get("cockpit_baggage", 0.0))),
            "Baggage extension": (
                float(inputs_weight.get("baggage_extension", 0.0)),
                float(arms_mm.get("baggage_extension", 0.0)),
            ),
            "De-ice fluid": (float(inputs_weight.get("deice_fluid", 0.0)), float(arms_mm.get("deice_fluid", 0.0))),
            "Main fuel (remaining)": (include_fuel_weight, fuel_arm),
        }
        _, totals = evaluate_components(comps)
        return WBPoint(weight=totals.weight, moment=totals.moment, cg=totals.cg)

    zfm = point(include_fuel_weight=0.0)

    takeoff_fuel_remaining = max(main_fuel_weight - taxi_fuel_burn_weight, 0.0)
    tow = point(include_fuel_weight=takeoff_fuel_remaining)

    landing1_fuel_remaining = max(takeoff_fuel_remaining - flight_fuel_burn_weight, 0.0)
    lw1 = point(include_fuel_weight=landing1_fuel_remaining)

    landing2_fuel_remaining = max(landing1_fuel_remaining - return_fuel_burn_weight, 0.0)
    lw2 = point(include_fuel_weight=landing2_fuel_remaining)

    return {"ZFM": zfm, "TOW": tow, "LW1": lw1, "LW2": lw2}
