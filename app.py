"""
Streamlit で公開するメイン画面。
見た目や入力欄の並びを変えたいときは主にこのファイルを編集する。
"""

from __future__ import annotations

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import streamlit.components.v1 as components

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


def parse_points(raw) -> list[tuple[float, float]]:
    """
    aircraft.toml の points = [[cg_mm, weight_kg], ...] を (cg, weight) に正規化。
    """
    pts: list[tuple[float, float]] = []
    if not isinstance(raw, list):
        return pts
    for item in raw:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            x = num(item[0])
            y = num(item[1])
            if x != 0.0 or y != 0.0:
                pts.append((x, y))
    return pts


def render_top_view_svg(values: dict[str, float], unit_weight: str) -> str:
    """
    クリック入力まではせず、「上面図＋現在値の見える化」をする簡易SVG。
    """
    def v(key: str) -> str:
        return f"{values.get(key, 0.0):.0f}"

    # シンプルなトップビュー（左右席・後席・バゲッジ・燃料を配置）
    # Streamlit の markdown/HTML解釈差異で表示が真っ白になるケースがあるため、
    # components.html で確実に描画できるよう HTML として返す。
    return f"""
<div style="width:100%; max-width:520px; margin:0 auto;">
<svg viewBox="0 0 420 700" width="100%" height="700" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <style>
      .air {{ fill:#f3f4f6; stroke:#cbd5e1; stroke-width:2; }}
      .seat {{ fill:#e5e7eb; stroke:#9ca3af; stroke-width:2; rx:12; }}
      .bag  {{ fill:#e5e7eb; stroke:#9ca3af; stroke-width:2; rx:12; }}
      .pill {{ fill:#16a34a; }}
      .pillText {{ fill:white; font: 700 22px system-ui, -apple-system, Segoe UI, Roboto; }}
      .label {{ fill:#111827; font: 600 14px system-ui, -apple-system, Segoe UI, Roboto; }}
      .small {{ fill:#374151; font: 500 12px system-ui, -apple-system, Segoe UI, Roboto; }}
    </style>
  </defs>

  <!-- fuselage -->
  <path class="air" d="M210 20
     C270 40, 315 95, 330 170
     C350 270, 345 430, 320 560
     C300 660, 250 690, 210 690
     C170 690, 120 660, 100 560
     C75 430, 70 270, 90 170
     C105 95, 150 40, 210 20 Z"/>

  <!-- cockpit seats -->
  <rect class="seat" x="95" y="210" width="115" height="130"/>
  <rect class="seat" x="210" y="210" width="115" height="130"/>
  <text class="label" x="152" y="205" text-anchor="middle">Front L</text>
  <text class="label" x="268" y="205" text-anchor="middle">Front R</text>
  <rect class="pill" x="125" y="250" width="55" height="38" rx="10"/>
  <rect class="pill" x="240" y="250" width="55" height="38" rx="10"/>
  <text class="pillText" x="152" y="277" text-anchor="middle">{v("front_l")}</text>
  <text class="pillText" x="268" y="277" text-anchor="middle">{v("front_r")}</text>
  <text class="small" x="152" y="305" text-anchor="middle">{unit_weight}</text>
  <text class="small" x="268" y="305" text-anchor="middle">{unit_weight}</text>

  <!-- rear seats -->
  <rect class="seat" x="95" y="365" width="115" height="120"/>
  <rect class="seat" x="210" y="365" width="115" height="120"/>
  <text class="label" x="152" y="360" text-anchor="middle">Rear L</text>
  <text class="label" x="268" y="360" text-anchor="middle">Rear R</text>
  <rect class="pill" x="125" y="402" width="55" height="38" rx="10"/>
  <rect class="pill" x="240" y="402" width="55" height="38" rx="10"/>
  <text class="pillText" x="152" y="429" text-anchor="middle">{v("rear_l")}</text>
  <text class="pillText" x="268" y="429" text-anchor="middle">{v("rear_r")}</text>
  <text class="small" x="152" y="457" text-anchor="middle">{unit_weight}</text>
  <text class="small" x="268" y="457" text-anchor="middle">{unit_weight}</text>

  <!-- nose baggage -->
  <rect class="bag" x="160" y="90" width="100" height="70"/>
  <text class="label" x="210" y="83" text-anchor="middle">Nose bag</text>
  <rect class="pill" x="182" y="110" width="56" height="38" rx="10"/>
  <text class="pillText" x="210" y="137" text-anchor="middle">{v("nose_bag")}</text>

  <!-- cabin baggage -->
  <rect class="bag" x="155" y="505" width="110" height="75"/>
  <text class="label" x="210" y="500" text-anchor="middle">Cabin bag</text>
  <rect class="pill" x="182" y="527" width="56" height="38" rx="10"/>
  <text class="pillText" x="210" y="554" text-anchor="middle">{v("cockpit_bag")}</text>

  <!-- extension baggage -->
  <rect class="bag" x="145" y="595" width="130" height="70"/>
  <text class="label" x="210" y="590" text-anchor="middle">Ext</text>
  <rect class="pill" x="182" y="615" width="56" height="38" rx="10"/>
  <text class="pillText" x="210" y="642" text-anchor="middle">{v("bag_ext")}</text>

  <!-- fuel / de-ice -->
  <text class="label" x="210" y="175" text-anchor="middle">Fuel / De-ice</text>
  <text class="small" x="210" y="195" text-anchor="middle">Fuel {v("main_fuel")} {unit_weight} / De-ice {v("deice")} {unit_weight}</text>
</svg>
</div>
"""


def _safe_point_xy(p) -> tuple[float | None, float | None]:
    if p.cg is None:
        return None, None
    return float(p.cg), float(p.weight)
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

    tab_input, tab_env, tab_breakdown = st.tabs(["入力（上面図）", "エンベロープ", "内訳"])

    with tab_input:
        st.subheader("入力（DA42用・固定項目）")
        col_viz, col_form = st.columns([1.1, 1.4], vertical_alignment="top")

        with col_form:
            st.markdown("**座席**")
            front_l = st.number_input("FrontSeats Left", min_value=0.0, value=0.0, step=1.0, format="%.2f")
            front_r = st.number_input("FrontSeats Right", min_value=0.0, value=0.0, step=1.0, format="%.2f")
            rear_l = st.number_input("RearSeats Left", min_value=0.0, value=0.0, step=1.0, format="%.2f")
            rear_r = st.number_input("RearSeats Right", min_value=0.0, value=0.0, step=1.0, format="%.2f")

            st.markdown("**バゲッジ・液体**")
            nose_bag = st.number_input("NoseBaggage", min_value=0.0, value=0.0, step=1.0, format="%.2f")
            cockpit_bag = st.number_input("CockpitBaggage", min_value=0.0, value=0.0, step=1.0, format="%.2f")
            bag_ext = st.number_input("BaggageExtension", min_value=0.0, value=0.0, step=1.0, format="%.2f")
            deice = st.number_input("De-iceFluid", min_value=0.0, value=0.0, step=1.0, format="%.2f")

            st.markdown("**燃料（重量換算）**")
            main_fuel = st.number_input("MainFuel（搭載）", min_value=0.0, value=0.0, step=1.0, format="%.2f")
            taxi_burn = st.number_input("FuelConsumption FOR Taxi", min_value=0.0, value=0.0, step=0.5, format="%.2f")
            flight_burn = st.number_input("FuelConsumption（離陸後〜着陸まで）", min_value=0.0, value=0.0, step=0.5, format="%.2f")

            st.caption(f"単位: 重量={unit_weight}, アーム={unit_arm}")

        with col_viz:
            st.markdown("**上面図（現在値の見える化）**")
            svg = render_top_view_svg(
                {
                    "front_l": front_l,
                    "front_r": front_r,
                    "rear_l": rear_l,
                    "rear_r": rear_r,
                    "nose_bag": nose_bag,
                    "cockpit_bag": cockpit_bag,
                    "bag_ext": bag_ext,
                    "deice": deice,
                    "main_fuel": main_fuel,
                },
                unit_weight=unit_weight,
            )
            components.html(svg, height=720)

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
    load_components = {
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
    results, totals = evaluate_components(load_components)

    zfm = points["ZFM"]
    tow = points["TOW"]
    lw = points["LW"]

    with tab_input:
        st.subheader("計算結果")
        c1, c2, c3 = st.columns(3)
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

    with tab_env:
        st.subheader("CGエンベロープ（封筒）")
        # 機体ごとの envelope を優先
        env_default = cfg.get("envelope", {}) or {}
        env_override = selected.get("envelope", {}) if isinstance(selected, dict) else {}
        env = {**env_default, **(env_override or {})}
        env_points = parse_points(env.get("points", []))

        if not env_points:
            st.warning("この機体のエンベロープ点が未入力です。`aircraft.toml` の `[aircraft.<TAIL>.envelope].points` に点を追加してください。")
            st.code('points = [[2400, 1350], [2500, 1900], [2450, 2000]]', language="toml")
        else:
            xs = [p[0] for p in env_points] + [env_points[0][0]]
            ys = [p[1] for p in env_points] + [env_points[0][1]]

            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=xs,
                    y=ys,
                    mode="lines",
                    name="Envelope",
                    line=dict(color="#ef4444", width=3),
                )
            )

            zx, zy = _safe_point_xy(zfm)
            tx, ty = _safe_point_xy(tow)
            lx, ly = _safe_point_xy(lw)
            fig.add_trace(
                go.Scatter(
                    x=[zx],
                    y=[zy],
                    mode="markers+text",
                    name="ZFM",
                    text=["ZFM"],
                    textposition="bottom right",
                    marker=dict(size=10, color="#60a5fa"),
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=[tx],
                    y=[ty],
                    mode="markers+text",
                    name="TOW",
                    text=["TOW"],
                    textposition="bottom right",
                    marker=dict(size=10, color="#f87171"),
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=[lx],
                    y=[ly],
                    mode="markers+text",
                    name="LW",
                    text=["LW"],
                    textposition="bottom right",
                    marker=dict(size=10, color="#34d399"),
                )
            )

            # 参考の制限線（入力がある場合のみ）
            shapes = []
            ann = []
            if mlw and mlw > 0:
                shapes.append(
                    dict(
                        type="line",
                        xref="paper",
                        x0=0,
                        x1=1,
                        y0=mlw,
                        y1=mlw,
                        line=dict(color="#ef4444", width=2, dash="solid"),
                    )
                )
                ann.append(
                    dict(
                        xref="paper",
                        x=0.02,
                        y=mlw,
                        text=f"MAX LDW {mlw:.0f}{unit_weight}",
                        showarrow=False,
                        font=dict(color="#ef4444", size=14),
                        yanchor="bottom",
                    )
                )
            if mtow and mtow > 0:
                shapes.append(
                    dict(
                        type="line",
                        xref="paper",
                        x0=0,
                        x1=1,
                        y0=mtow,
                        y1=mtow,
                        line=dict(color="#ef4444", width=1, dash="dot"),
                    )
                )
                ann.append(
                    dict(
                        xref="paper",
                        x=0.02,
                        y=mtow,
                        text=f"MAX TOW {mtow:.0f}{unit_weight}",
                        showarrow=False,
                        font=dict(color="#ef4444", size=12),
                        yanchor="bottom",
                    )
                )

            fig.update_layout(
                template="plotly_dark",
                xaxis_title=f"CG [{unit_arm}]",
                yaxis_title=f"Weight [{unit_weight}]",
                height=520,
                width=520,
                margin=dict(l=10, r=10, t=30, b=10),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                paper_bgcolor="#0b1220",
                plot_bgcolor="#0b1220",
                shapes=shapes,
                annotations=ann,
            )
            fig.update_xaxes(showgrid=True, gridcolor="rgba(148,163,184,0.25)", zeroline=False)
            fig.update_yaxes(showgrid=True, gridcolor="rgba(148,163,184,0.25)", zeroline=False)
            left_pad, center, right_pad = st.columns([1, 2, 1])
            with center:
                st.plotly_chart(fig, use_container_width=False)

    with tab_breakdown:
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
