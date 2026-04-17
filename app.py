"""
Streamlit で公開するメイン画面。
見た目や入力欄の並びを変えたいときは主にこのファイルを編集する。
"""

from __future__ import annotations

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import streamlit.components.v1 as components
import base64
from pathlib import Path

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


def _data_uri_for_png(path: str) -> str | None:
    p = Path(path)
    if not p.exists() or not p.is_file():
        return None
    try:
        b64 = base64.b64encode(p.read_bytes()).decode("ascii")
        return f"data:image/png;base64,{b64}"
    except OSError:
        return None


def _find_png_data_uri() -> tuple[str | None, str]:
    """
    Streamlit Cloud での配置ゆれを吸収して、背景PNGを探す。
    戻り値: (data_uri, 見つかったパス or エラーメッセージ)
    """
    here = Path(__file__).resolve().parent
    candidates = [
        here / "assets" / "da42_topview.png",
        here / "assets" / "DA42_topview.png",
        here / "assets" / "da42_topview.jpg",  # 念のため
        here / "assets" / "da42_topview.jpeg",
        Path("assets") / "da42_topview.png",
        Path("WB") / "assets" / "da42_topview.png",
    ]
    for c in candidates:
        uri = _data_uri_for_png(str(c))
        if uri:
            return uri, str(c)
    return None, "not found"


def render_top_view_svg(values: dict[str, float], unit_weight: str, *, background_png_data_uri: str | None = None) -> str:
    """
    クリック入力まではせず、「上面図＋現在値の見える化」をする簡易SVG。
    """
    def v(key: str) -> str:
        return f"{values.get(key, 0.0):.0f}"

    def v1(key: str) -> str:
        return f"{values.get(key, 0.0):.1f}"

    # components.html 内では SVGの <a href> が効かない環境があるため、
    # onclick で top window のURLを更新して確実に遷移させる。
    def g_open(edit_key: str) -> str:
        return f"<g onclick=\"setEdit('{edit_key}')\" style=\"cursor:pointer;\">"

    def g_close() -> str:
        return "</g>"

    # DA42っぽいトップビュー（翼・胴体・エンジン・尾翼）に寄せた簡易シルエット。
    # Streamlit の markdown/HTML解釈差異で表示が真っ白になるケースがあるため、
    # components.html で確実に描画できるよう HTML として返す。
    bg = ""
    has_bg = bool(background_png_data_uri)
    if has_bg:
        # 参照画像をそのまま背景に敷く（“全く同じ”見た目に近づける）
        #
        # 画像を少し拡大（ズーム）して、入力枠が機体の中に収まりやすいようにする。
        # center を基準にスケールし、微調整は pan_x/pan_y で行う。
        bg_scale = 1.52
        pan_x = 0.0
        pan_y = -28.0
        cx = 260.0
        cy = 410.0
        tx = (1.0 - bg_scale) * cx + pan_x
        ty = (1.0 - bg_scale) * cy + pan_y
        bg = (
            f'<g transform="translate({tx:.2f},{ty:.2f}) scale({bg_scale:.4f})">'
            f'<image href="{background_png_data_uri}" x="0" y="0" width="520" height="820" preserveAspectRatio="xMidYMid meet" opacity="1.0" />'
            f"</g>"
        )

    return f"""
<div style="width:100%; max-width:600px; margin:0 auto;">
<script>
  function setEdit(key) {{
    try {{
      const u = new URL(window.top.location.href);
      u.searchParams.set('edit', key);
      u.hash = 'topview';
      window.top.location.href = u.toString();
    }} catch (e) {{
      // fallback: same-frame
      const u = new URL(window.location.href);
      u.searchParams.set('edit', key);
      u.hash = 'topview';
      window.location.href = u.toString();
    }}
  }}
</script>
<svg viewBox="0 0 520 820" width="100%" height="760" xmlns="http://www.w3.org/2000/svg">
  {bg}
  <defs>
    <style>
      .air {{ fill:#f3f4f6; stroke:#cbd5e1; stroke-width:2; }}
      .outline {{ fill:none; stroke:#94a3b8; stroke-width:2; }}
      .seat {{ fill:#e5e7eb; stroke:#9ca3af; stroke-width:2; rx:12; }}
      .bag  {{ fill:#e5e7eb; stroke:#9ca3af; stroke-width:2; rx:12; }}
      .pill {{ fill:#16a34a; }}
      .pillText {{ fill:white; font: 700 22px system-ui, -apple-system, Segoe UI, Roboto; }}
      .label {{ fill:#111827; font: 600 14px system-ui, -apple-system, Segoe UI, Roboto; }}
      .small {{ fill:#374151; font: 500 12px system-ui, -apple-system, Segoe UI, Roboto; }}
    </style>
  </defs>
  {"" if has_bg else """
  <!-- wings (DA42っぽく: 先細り) -->
  <path class="air" d="M35 300
    L485 300
    L470 370
    L50 370 Z" opacity="0.55"/>

  <!-- fuselage (細め・長め) -->
  <path class="air" d="M260 40
     C290 52, 312 94, 318 150
     C325 220, 325 320, 318 440
     C310 565, 295 650, 282 735
     C276 780, 270 805, 260 810
     C250 805, 244 780, 238 735
     C225 650, 210 565, 202 440
     C195 320, 195 220, 202 150
     C208 94, 230 52, 260 40 Z" opacity="0.55"/>

  <!-- engine nacelles (approx) -->
  <rect class="air" x="150" y="285" width="70" height="90" rx="18" opacity="0.55"/>
  <rect class="air" x="300" y="285" width="70" height="90" rx="18" opacity="0.55"/>
  <circle class="outline" cx="185" cy="330" r="26"/>
  <circle class="outline" cx="335" cy="330" r="26"/>

  <!-- twin tail booms -->
  <path class="outline" d="M185 375 L205 735"/>
  <path class="outline" d="M335 375 L315 735"/>

  <!-- tailplane + fins (DA42らしさ) -->
  <path class="air" d="M175 735 L345 735 L345 770 L175 770 Z" opacity="0.55"/>
  <path class="air" d="M175 710 L205 710 L205 770 L175 770 Z" opacity="0.55"/>
  <path class="air" d="M315 710 L345 710 L345 770 L315 770 Z" opacity="0.55"/>
  """}

  <!-- cockpit seats -->
  {g_open("front_l")}
  <rect class="seat" x="190" y="235" width="65" height="95"/>
  <text class="label" x="222" y="229" text-anchor="middle">Front L</text>
  <rect class="pill" x="198" y="270" width="50" height="34" rx="10"/>
  <text class="pillText" x="223" y="295" text-anchor="middle">{v("front_l")}</text>
  <text class="small" x="223" y="319" text-anchor="middle">{unit_weight}</text>
  {g_close()}

  {g_open("front_r")}
  <rect class="seat" x="265" y="235" width="65" height="95"/>
  <text class="label" x="298" y="229" text-anchor="middle">Front R</text>
  <rect class="pill" x="273" y="270" width="50" height="34" rx="10"/>
  <text class="pillText" x="298" y="295" text-anchor="middle">{v("front_r")}</text>
  <text class="small" x="298" y="319" text-anchor="middle">{unit_weight}</text>
  {g_close()}

  <!-- rear seats -->
  {g_open("rear_l")}
  <rect class="seat" x="190" y="490" width="65" height="85"/>
  <text class="label" x="222" y="483" text-anchor="middle">Rear L</text>
  <rect class="pill" x="198" y="520" width="50" height="34" rx="10"/>
  <text class="pillText" x="223" y="545" text-anchor="middle">{v("rear_l")}</text>
  <text class="small" x="223" y="568" text-anchor="middle">{unit_weight}</text>
  {g_close()}

  {g_open("rear_r")}
  <rect class="seat" x="265" y="490" width="65" height="85"/>
  <text class="label" x="298" y="483" text-anchor="middle">Rear R</text>
  <rect class="pill" x="273" y="520" width="50" height="34" rx="10"/>
  <text class="pillText" x="298" y="545" text-anchor="middle">{v("rear_r")}</text>
  <text class="small" x="298" y="568" text-anchor="middle">{unit_weight}</text>
  {g_close()}

  <!-- nose baggage -->
  {g_open("nose_bag")}
  <rect class="bag" x="225" y="65" width="70" height="55"/>
  <text class="label" x="260" y="60" text-anchor="middle">Nose</text>
  <rect class="pill" x="237" y="82" width="46" height="32" rx="10"/>
  <text class="pillText" x="260" y="106" text-anchor="middle">{v("nose_bag")}</text>
  {g_close()}

  <!-- de-ice (Nose baggage と Front seats の間) -->
  {g_open("deice_l")}
  <rect class="bag" x="210" y="145" width="100" height="70"/>
  <text class="label" x="260" y="143" text-anchor="middle">De-ice</text>
  <rect class="pill" x="235" y="169" width="50" height="34" rx="10"/>
  <text class="pillText" x="260" y="194" text-anchor="middle">{v1("deice_l")}</text>
  <text class="small" x="260" y="217" text-anchor="middle">{v1("deice_kg")} {unit_weight}</text>
  {g_close()}

  <!-- cockpit baggage (Front/Rear の間の細長い枠) -->
  {g_open("cockpit_bag")}
  <rect class="bag" x="165" y="395" width="190" height="40"/>
  <text class="label" x="260" y="390" text-anchor="middle">CockpitBaggage</text>
  <rect class="pill" x="237" y="403" width="46" height="28" rx="10"/>
  <text class="pillText" x="260" y="425" text-anchor="middle">{v("cockpit_bag")}</text>
  {g_close()}

  <!-- baggage extension -->
  {g_open("bag_ext")}
  <rect class="bag" x="170" y="675" width="180" height="55"/>
  <text class="label" x="260" y="670" text-anchor="middle">BaggageExtension</text>
  <rect class="pill" x="237" y="690" width="46" height="32" rx="10"/>
  <text class="pillText" x="260" y="714" text-anchor="middle">{v("bag_ext")}</text>
  {g_close()}

  <!-- fuel (left wing / right wing) -->
  {g_open("main_fuel_gal")}
  <rect class="bag" x="86" y="262" width="102" height="72"/>
  <text class="label" x="137" y="256" text-anchor="middle">Fuel L</text>
  <rect class="pill" x="111" y="285" width="54" height="34" rx="10"/>
  <text class="pillText" x="138" y="310" text-anchor="middle">{v1("fuel_l_gal")}</text>
  <text class="small" x="138" y="332" text-anchor="middle">{v1("fuel_l_kg")} {unit_weight}</text>
  {g_close()}

  {g_open("main_fuel_gal")}
  <rect class="bag" x="332" y="262" width="102" height="72"/>
  <text class="label" x="383" y="256" text-anchor="middle">Fuel R</text>
  <rect class="pill" x="356" y="285" width="54" height="34" rx="10"/>
  <text class="pillText" x="383" y="310" text-anchor="middle">{v1("fuel_r_gal")}</text>
  <text class="small" x="383" y="332" text-anchor="middle">{v1("fuel_r_kg")} {unit_weight}</text>
  {g_close()}
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
    st.markdown('<div id="topview"></div>', unsafe_allow_html=True)
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

    # 上面図クリックで ?edit=... が付いたら、ここで受け取る
    edit_key = st.query_params.get("edit")

    with tab_input:
        st.subheader("入力（DA42用・固定項目）")
        col_viz, col_form = st.columns([1.1, 1.4], vertical_alignment="top")

        # クリック編集UI（サイドバー）
        with st.sidebar:
            st.subheader("上面図クリック編集")
            if edit_key:
                st.caption(f"選択中: `{edit_key}`（上面図の枠をクリックすると切り替わります）")
                if st.button("選択解除"):
                    st.query_params.pop("edit", None)
                    st.rerun()
            else:
                st.caption("上面図の枠をクリックすると、ここでその項目を編集できます。")

        with col_form:
            st.markdown("**座席**")
            front_l = st.number_input("FrontSeats Left", min_value=0.0, value=float(st.session_state.get("front_l", 0.0)), step=1.0, format="%.2f", key="front_l")
            front_r = st.number_input("FrontSeats Right", min_value=0.0, value=float(st.session_state.get("front_r", 0.0)), step=1.0, format="%.2f", key="front_r")
            rear_l = st.number_input("RearSeats Left", min_value=0.0, value=float(st.session_state.get("rear_l", 0.0)), step=1.0, format="%.2f", key="rear_l")
            rear_r = st.number_input("RearSeats Right", min_value=0.0, value=float(st.session_state.get("rear_r", 0.0)), step=1.0, format="%.2f", key="rear_r")

            st.markdown("**バゲッジ・液体**")
            nose_bag = st.number_input("NoseBaggage", min_value=0.0, value=float(st.session_state.get("nose_bag", 0.0)), step=1.0, format="%.2f", key="nose_bag")
            cockpit_bag = st.number_input("CockpitBaggage", min_value=0.0, value=float(st.session_state.get("cockpit_bag", 0.0)), step=1.0, format="%.2f", key="cockpit_bag")
            bag_ext = st.number_input("BaggageExtension", min_value=0.0, value=float(st.session_state.get("bag_ext", 0.0)), step=1.0, format="%.2f", key="bag_ext")
            deice_l = st.number_input("De-iceFluid（リットルで入力）", min_value=0.0, value=float(st.session_state.get("deice_l", 0.0)), step=1.0, format="%.1f", key="deice_l")
            deice_kg = deice_l * 1.1

            st.markdown("**燃料（重量換算）**")
            st.caption("燃料は **US gal** で入力（1 US gal = 3.028 kg）")
            main_fuel_gal = st.number_input("MainFuel（搭載・ガロンで入力）", min_value=0.0, value=float(st.session_state.get("main_fuel_gal", 0.0)), step=1.0, format="%.1f", key="main_fuel_gal")
            taxi_burn_gal = st.number_input("FuelConsumption FOR Taxi（ガロンで入力）", min_value=0.0, value=float(st.session_state.get("taxi_burn_gal", 0.0)), step=0.5, format="%.1f", key="taxi_burn_gal")
            flight_burn_gal = st.number_input("FuelConsumption（目的地まで・ガロンで入力）", min_value=0.0, value=float(st.session_state.get("flight_burn_gal", 0.0)), step=0.5, format="%.1f", key="flight_burn_gal")
            return_burn_gal = st.number_input("FuelConsumption（復路・ガロンで入力）", min_value=0.0, value=float(st.session_state.get("return_burn_gal", 0.0)), step=0.5, format="%.1f", key="return_burn_gal")

            fuel_kg_per_usg = 3.028
            main_fuel_kg = main_fuel_gal * fuel_kg_per_usg
            taxi_burn_kg = taxi_burn_gal * fuel_kg_per_usg
            flight_burn_kg = flight_burn_gal * fuel_kg_per_usg
            return_burn_kg = return_burn_gal * fuel_kg_per_usg

            st.caption(f"単位: 重量={unit_weight}, アーム={unit_arm}")

        # クリックで選択された項目を編集（サイドバー）
        with st.sidebar:
            if edit_key:
                if edit_key == "front_l":
                    st.number_input("FrontSeats Left", min_value=0.0, step=1.0, format="%.2f", key="front_l")
                elif edit_key == "front_r":
                    st.number_input("FrontSeats Right", min_value=0.0, step=1.0, format="%.2f", key="front_r")
                elif edit_key == "rear_l":
                    st.number_input("RearSeats Left", min_value=0.0, step=1.0, format="%.2f", key="rear_l")
                elif edit_key == "rear_r":
                    st.number_input("RearSeats Right", min_value=0.0, step=1.0, format="%.2f", key="rear_r")
                elif edit_key == "nose_bag":
                    st.number_input("NoseBaggage", min_value=0.0, step=1.0, format="%.2f", key="nose_bag")
                elif edit_key == "cockpit_bag":
                    st.number_input("CockpitBaggage", min_value=0.0, step=1.0, format="%.2f", key="cockpit_bag")
                elif edit_key == "bag_ext":
                    st.number_input("BaggageExtension", min_value=0.0, step=1.0, format="%.2f", key="bag_ext")
                elif edit_key == "deice_l":
                    st.number_input("De-iceFluid（リットルで入力）", min_value=0.0, step=1.0, format="%.1f", key="deice_l")
                    st.caption("換算: 1 L = 1.1 kg")
                elif edit_key == "main_fuel_gal":
                    st.number_input("MainFuel（搭載・ガロンで入力）", min_value=0.0, step=1.0, format="%.1f", key="main_fuel_gal")
                    st.caption("換算: 1 US gal = 3.028 kg")

        with col_viz:
            st.markdown("**上面図（現在値の見える化）**")
            fuel_half_gal = main_fuel_gal / 2.0
            fuel_half_kg = main_fuel_kg / 2.0
            st.caption("枠をクリックすると、その項目を編集できます。")
            bg_uri, bg_path = _find_png_data_uri()
            if bg_uri:
                st.caption(f"背景画像: `{bg_path}`")
            else:
                st.caption("背景画像: 未検出（`assets/da42_topview.png` を配置してください）")
            svg = render_top_view_svg(
                {
                    "front_l": front_l,
                    "front_r": front_r,
                    "rear_l": rear_l,
                    "rear_r": rear_r,
                    "nose_bag": nose_bag,
                    "cockpit_bag": cockpit_bag,
                    "bag_ext": bag_ext,
                    "deice_l": deice_l,
                    "deice_kg": deice_kg,
                    "fuel_l_gal": fuel_half_gal,
                    "fuel_r_gal": fuel_half_gal,
                    "fuel_l_kg": fuel_half_kg,
                    "fuel_r_kg": fuel_half_kg,
                },
                unit_weight=unit_weight,
                background_png_data_uri=bg_uri,
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
        "deice_fluid": deice_kg,
    }

    points = compute_da42_points(
        basic_empty_weight=bew_w,
        basic_empty_arm=bew_a,
        arms_mm=arms,
        inputs_weight=inputs_weight,
        main_fuel_weight=main_fuel_kg,
        taxi_fuel_burn_weight=taxi_burn_kg,
        flight_fuel_burn_weight=flight_burn_kg,
        return_fuel_burn_weight=return_burn_kg,
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
        "De-ice fluid": (deice_kg, arms.get("deice_fluid", 0.0)),
        "Main fuel (loaded)": (main_fuel_kg, arms.get("main_fuel", 0.0)),
    }
    results, totals = evaluate_components(load_components)

    zfm = points["ZFM"]
    tow = points["TOW"]
    lw1 = points["LW1"]
    lw2 = points["LW2"]

    with tab_input:
        st.subheader("計算結果")
        c1, c2, c3 = st.columns(3)
        c1.metric(f"Zero Fuel Weight (ZFW) [{unit_weight}]", f"{zfm.weight:,.2f}", help="燃料を除いた重量")
        c2.metric(f"Takeoff Weight (TOW) [{unit_weight}]", f"{tow.weight:,.2f}", help="Taxi消費後の燃料を含む")
        c3.metric(f"Landing Weight 1 (LW1) [{unit_weight}]", f"{lw1.weight:,.2f}", help="目的地到着時（燃料消費後）")

        g1, g2, g3 = st.columns(3)
        g1.metric(f"ZFM CG [{unit_arm}]", "—" if zfm.cg is None else f"{zfm.cg:,.1f}")
        g2.metric(f"TOW CG [{unit_arm}]", "—" if tow.cg is None else f"{tow.cg:,.1f}")
        g3.metric(f"LW1 CG [{unit_arm}]", "—" if lw1.cg is None else f"{lw1.cg:,.1f}")

        h1, h2, h3 = st.columns(3)
        h1.metric(f"LW2 [{unit_weight}]", f"{lw2.weight:,.2f}", help="復路消費後（帰投想定）")
        h2.metric(f"LW2 CG [{unit_arm}]", "—" if lw2.cg is None else f"{lw2.cg:,.1f}")
        h3.write("")

        if use_limits:
            for label, p in [("ZFW", zfm), ("TOW", tow), ("LW1", lw1), ("LW2", lw2)]:
                status = within_limits(p.cg, cg_min, cg_max)
                if status and "外" in status:
                    st.error(f"{label}: {status}")
                elif status:
                    st.success(f"{label}: {status}")

    with tab_env:
        st.subheader("CGエンベロープ")
        # 機体ごとの envelope を優先
        env_default = cfg.get("envelope", {}) or {}
        env_override = selected.get("envelope", {}) if isinstance(selected, dict) else {}
        env = {**env_default, **(env_override or {})}
        env_points = parse_points(env.get("points", []))

        if not env_points:
            st.warning("この機体のエンベロープ点が未入力です。`aircraft.toml` の `[aircraft.<TAIL>.envelope].points` に点を追加してください。")
            st.code('points = [[2400, 1350], [2500, 1900], [2450, 2000]]', language="toml")
        else:
            # 表示は m にしたい（例: 2350mm -> 2.35）
            env_points_m = [(cg / 1000.0, wt) for (cg, wt) in env_points]
            xs = [p[0] for p in env_points_m] + [env_points_m[0][0]]
            ys = [p[1] for p in env_points] + [env_points[0][1]]

            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=xs,
                    y=ys,
                    mode="lines",
                    name="",
                    line=dict(color="#ef4444", width=3),
                    showlegend=False,
                )
            )

            zx, zy = _safe_point_xy(zfm)
            tx, ty = _safe_point_xy(tow)
            l1x, l1y = _safe_point_xy(lw1)
            l2x, l2y = _safe_point_xy(lw2)
            fig.add_trace(
                go.Scatter(
                    x=[None if zx is None else zx / 1000.0],
                    y=[zy],
                    mode="markers+text",
                    name="ZFW",
                    text=["ZFW"],
                    textposition="bottom right",
                    marker=dict(size=10, color="#60a5fa"),
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=[None if tx is None else tx / 1000.0],
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
                    x=[None if l1x is None else l1x / 1000.0],
                    y=[l1y],
                    mode="markers+text",
                    name="LW1",
                    text=["LW1"],
                    textposition="bottom right",
                    marker=dict(size=10, color="#34d399"),
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=[None if l2x is None else l2x / 1000.0],
                    y=[l2y],
                    mode="markers+text",
                    name="LW2",
                    text=["LW2"],
                    textposition="bottom right",
                    marker=dict(size=10, color="#fbbf24"),
                )
            )

            # 点を直線で結ぶ（ZFW -> TOW -> LW1 -> LW2）
            path_x = []
            path_y = []
            for x_mm, y in [(zx, zy), (tx, ty), (l1x, l1y), (l2x, l2y)]:
                if x_mm is None or y is None:
                    continue
                path_x.append(x_mm / 1000.0)
                path_y.append(y)
            if len(path_x) >= 2:
                fig.add_trace(
                    go.Scatter(
                        x=path_x,
                        y=path_y,
                        mode="lines",
                        line=dict(color="rgba(226,232,240,0.9)", width=2),
                        showlegend=False,
                        hoverinfo="skip",
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
                xaxis_title="CG [m]",
                yaxis_title=f"Weight [{unit_weight}]",
                height=520,
                width=1020,
                margin=dict(l=60, r=20, t=30, b=50),
                showlegend=False,
                paper_bgcolor="#0b1220",
                plot_bgcolor="#0b1220",
                shapes=shapes,
                annotations=ann,
            )
            fig.update_xaxes(
                showgrid=True,
                gridcolor="rgba(148,163,184,0.25)",
                zeroline=False,
                tickformat=".2f",
                tickmode="array",
                tickvals=[2.35, 2.40, 2.45, 2.50],
                ticktext=["<b>2.35</b>", "<b>2.40</b>", "<b>2.45</b>", "<b>2.50</b>"],
                minor=dict(
                    dtick=0.01,
                    showgrid=True,
                    gridcolor="rgba(148,163,184,0.12)",
                ),
            )
            fig.update_yaxes(
                showgrid=True,
                gridcolor="rgba(148,163,184,0.25)",
                zeroline=False,
                dtick=20,
                tickmode="array",
                tickvals=[1250, 1300, 1350, 1400, 1450, 1500, 1550, 1600, 1650, 1700, 1750, 1800],
                ticktext=[
                    "<b>1250</b>",
                    "<b>1300</b>",
                    "<b>1350</b>",
                    "<b>1400</b>",
                    "<b>1450</b>",
                    "<b>1500</b>",
                    "<b>1550</b>",
                    "<b>1600</b>",
                    "<b>1650</b>",
                    "<b>1700</b>",
                    "<b>1750</b>",
                    "<b>1800</b>",
                ],
            )
            left_pad, center, right_pad = st.columns([1, 3, 1])
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
