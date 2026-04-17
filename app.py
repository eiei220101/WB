"""
Streamlit で公開するメイン画面。
見た目や入力欄の並びを変えたいときは主にこのファイルを編集する。
"""

from __future__ import annotations

import streamlit as st
import pandas as pd

from wb_logic import compute_da42_points, evaluate_components, within_limits

try:
    import tomllib  # py3.11+
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None  # type: ignore[assignment]

# --- ページ設定（見やすさ） ---
st.set_page_config(
    page_title="重量・重心計算",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# スタイル（余白・見出し）
st.markdown(
    """
    <style>
    .block-container { padding-top: 1.2rem; }
    h1 { font-weight: 600; }
    </style>
    """,
    unsafe_allow_html=True,
)
def load_aircraft_config(path: str = "aircraft.toml") -> dict:
    if tomllib is None:
        raise RuntimeError("Python 3.11+ が必要です（tomllibが無い環境）。")
    with open(path, "rb") as f:
        return tomllib.load(f)


def num(x) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def main() -> None:
    cfg = load_aircraft_config()
    aircraft_name = str(cfg.get("meta", {}).get("aircraft_name", "重量・重心計算"))
    fleet_default = str(cfg.get("fleet", {}).get("default_tail", "") or "")
    aircraft_map = cfg.get("aircraft", {}) or {}

    with st.sidebar:
        st.header("機体選択")
        tails = sorted([str(k) for k in aircraft_map.keys()]) if isinstance(aircraft_map, dict) else []
        if tails:
            default_idx = tails.index(fleet_default) if fleet_default in tails else 0
            tail = st.selectbox("登録記号", tails, index=default_idx)
            selected = aircraft_map.get(tail, {}) if isinstance(aircraft_map, dict) else {}
        else:
            tail = ""
            selected = {}

    subtitle = f"{aircraft_name}" + (f" / {tail}" if tail else "")
    st.title(f"{subtitle} 重量・重心（W&B）")
    st.caption(
        "基準点（Datum）からの距離を「アーム」として入力します。"
        " モーメント = 重量 × アーム、重心アーム = 総モーメント ÷ 総重量 です。"
    )

    with st.sidebar:
        st.header("機体設定（aircraft.toml）")
        st.caption(str(cfg.get("meta", {}).get("arm_reference_note", "")))
        model = str(selected.get("model", "") or "")
        notes = str(selected.get("notes", "") or "")
        if model:
            st.write(f"- 型式: **{model}**")
        if notes:
            st.write(f"- メモ: **{notes}**")
        st.info("アームやBEWは `aircraft.toml` を編集して更新します。")

        unit_weight = str(cfg.get("units", {}).get("weight", "kg"))
        unit_arm = str(cfg.get("units", {}).get("arm", "mm"))

        st.subheader("基本空重（BEW）")
        sel_be = selected.get("basic_empty", {}) if isinstance(selected, dict) else {}
        bew_w = num(sel_be.get("weight", cfg.get("basic_empty", {}).get("weight", 0.0)))
        bew_a = num(sel_be.get("arm", cfg.get("basic_empty", {}).get("arm", 0.0)))
        st.write(f"- 重量: **{bew_w:,.2f} {unit_weight}**")
        st.write(f"- アーム: **{bew_a:,.1f} {unit_arm}**")

        # limits: 機体ごとの上書きを優先
        lim_default = cfg.get("limits", {}) or {}
        lim_override = selected.get("limits", {}) if isinstance(selected, dict) else {}
        lim = {**lim_default, **(lim_override or {})}
        use_limits = bool(lim.get("use_fixed_cg", False))
        cg_min = num(lim.get("cg_min", 0.0)) if use_limits else None
        cg_max = num(lim.get("cg_max", 0.0)) if use_limits else None
        use_limits = st.checkbox("固定CG範囲で判定する", value=use_limits)
        if use_limits:
            cg_min = st.number_input("CG最小", value=float(cg_min or 0.0), format="%.3f")
            cg_max = st.number_input("CG最大", value=float(cg_max or 0.0), format="%.3f")

        st.subheader("重量制限（任意）")
        mzfm = num(lim.get("mzfm", 0.0)) or None
        mtow = num(lim.get("mtow", 0.0)) or None
        mlw = num(lim.get("mlw", 0.0)) or None
        if any(v is not None for v in [mzfm, mtow, mlw]):
            st.write(
                f"- MZFM: **{('—' if mzfm is None else f'{mzfm:,.1f} {unit_weight}')}**\n"
                f"- MTOW: **{('—' if mtow is None else f'{mtow:,.1f} {unit_weight}')}**\n"
                f"- MLW: **{('—' if mlw is None else f'{mlw:,.1f} {unit_weight}')}**"
            )

    arms = {k: num(v) for k, v in (cfg.get("arms_mm", {}) or {}).items()}

    st.subheader("入力（DA42用・固定項目）")
    left, right = st.columns(2)
    with left:
        st.markdown("**座席**")
        front_l = st.number_input("FrontSeats Left", min_value=0.0, value=0.0, step=1.0, format="%.2f")
        front_r = st.number_input("FrontSeats Right", min_value=0.0, value=0.0, step=1.0, format="%.2f")
        rear_l = st.number_input("RearSeats Left", min_value=0.0, value=0.0, step=1.0, format="%.2f")
        rear_r = st.number_input("RearSeats Right", min_value=0.0, value=0.0, step=1.0, format="%.2f")

        st.markdown("**燃料**")
        main_fuel = st.number_input("MainFuel（搭載）", min_value=0.0, value=0.0, step=1.0, format="%.2f")
        taxi_burn = st.number_input("FuelConsumption FOR Taxi", min_value=0.0, value=0.0, step=0.5, format="%.2f")
        flight_burn = st.number_input("FuelConsumption（離陸後〜着陸まで）", min_value=0.0, value=0.0, step=0.5, format="%.2f")

    with right:
        st.markdown("**バゲッジ・液体**")
        nose_bag = st.number_input("NoseBaggage", min_value=0.0, value=0.0, step=1.0, format="%.2f")
        cockpit_bag = st.number_input("CockpitBaggage", min_value=0.0, value=0.0, step=1.0, format="%.2f")
        bag_ext = st.number_input("BaggageExtension", min_value=0.0, value=0.0, step=1.0, format="%.2f")
        deice = st.number_input("De-iceFluid", min_value=0.0, value=0.0, step=1.0, format="%.2f")

        st.markdown("**表示単位**")
        st.caption(f"重量: {unit_weight} / アーム: {unit_arm}")

    if bew_w <= 0 or bew_a <= 0:
        st.warning("`aircraft.toml` の basic_empty（BEWの重量とアーム）を入力してください。入力が無いと実機の結果になりません。")

    inputs_weight = {
        "front_seat_left": front_l,
        "front_seat_right": front_r,
        "rear_seat_left": rear_l,
        "rear_seat_right": rear_r,
        "nose_baggage": nose_bag,
        "cockpit_baggage": cockpit_bag,
        "baggage_extension": bag_ext,
        "deice_fluid": deice,
    }

    points = compute_da42_points(
        basic_empty_weight=bew_w,
        basic_empty_arm=bew_a,
        arms_mm=arms,
        inputs_weight=inputs_weight,
        main_fuel_weight=main_fuel,
        taxi_fuel_burn_weight=taxi_burn,
        flight_fuel_burn_weight=flight_burn,
    )

    # 内訳（ZFM/TOW/LWそれぞれで共通の“入力値”を表示したいので、現在の搭載項目を一覧化）
    components = {
        "Basic Empty": (bew_w, bew_a),
        "Front seat L": (front_l, arms.get("front_seat_left", 0.0)),
        "Front seat R": (front_r, arms.get("front_seat_right", 0.0)),
        "Rear seat L": (rear_l, arms.get("rear_seat_left", 0.0)),
        "Rear seat R": (rear_r, arms.get("rear_seat_right", 0.0)),
        "Nose baggage": (nose_bag, arms.get("nose_baggage", 0.0)),
        "Cockpit baggage": (cockpit_bag, arms.get("cockpit_baggage", 0.0)),
        "Baggage extension": (bag_ext, arms.get("baggage_extension", 0.0)),
        "De-ice fluid": (deice, arms.get("deice_fluid", 0.0)),
        "Main fuel (loaded)": (main_fuel, arms.get("main_fuel", 0.0)),
    }
    results, totals = evaluate_components(components)

    st.subheader("計算結果")
    c1, c2, c3 = st.columns(3)
    zfm = points["ZFM"]
    tow = points["TOW"]
    lw = points["LW"]
    c1.metric(f"Zero Fuel Mass (ZFM) [{unit_weight}]", f"{zfm.weight:,.2f}", help="燃料を除いた重量")
    c2.metric(f"Takeoff Weight (TOW) [{unit_weight}]", f"{tow.weight:,.2f}", help="Taxi消費後の燃料を含む")
    c3.metric(f"Landing Weight (LW) [{unit_weight}]", f"{lw.weight:,.2f}", help="飛行中の燃料消費後")

    g1, g2, g3 = st.columns(3)
    g1.metric(f"ZFM CG [{unit_arm}]", "—" if zfm.cg is None else f"{zfm.cg:,.1f}")
    g2.metric(f"TOW CG [{unit_arm}]", "—" if tow.cg is None else f"{tow.cg:,.1f}")
    g3.metric(f"LW CG [{unit_arm}]", "—" if lw.cg is None else f"{lw.cg:,.1f}")

    if use_limits:
        for label, p in [("ZFM", zfm), ("TOW", tow), ("LW", lw)]:
            status = within_limits(p.cg, cg_min, cg_max)
            if status and "外" in status:
                st.error(f"{label}: {status}")
            elif status:
                st.success(f"{label}: {status}")

    st.subheader("内訳一覧")
    out = pd.DataFrame(
        [
            {
                "項目": r.name,
                f"重量 [{unit_weight}]": r.weight,
                f"アーム [{unit_arm}]": r.arm,
                f"モーメント [{unit_weight}·{unit_arm}]": r.moment,
            }
            for r in results
        ]
    )
    st.dataframe(out, use_container_width=True, hide_index=True)

    with st.expander("計算の考え方（初心者向け）"):
        st.markdown(
            """
            1. **基準点（Datum）** … 機体マニュアルで決まった「距離の起点」。ここから各荷重の重心までの距離が **アーム** です。
            2. **モーメント** … `重量 × アーム`。前後に荷重が偏るほど総モーメントが変わります。
            3. **重心アーム** … `総モーメント ÷ 総重量`。機体全体のバランスの中心が基準点からどれだけ離れているかを表します。
            4. 実運用では **POH / 正式な W&B 資料** の許容範囲と照合してください。このツールは補助計算です。
            """
        )


if __name__ == "__main__":
    main()
