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
import traceback
import json
import plotly.io as pio
import plotly
import os
import copy

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

# スタイル（余白・見出し・明暗コントラスト）
st.markdown(
    """
    <style>
    .block-container { padding-top: 1.2rem; }

    /* サイドバーとメイン領域の明暗をはっきり分離 */
    section[data-testid="stSidebar"] > div {
        background-color: #e5e7eb !important;
        border-right: 2px solid #9ca3af !important;
    }
    section[data-testid="stMain"] .block-container {
        background-color: #ffffff;
    }

    /* 見出し（メイン領域のみ下線・余白を確保して被りを防ぐ） */
    h1 {
        font-weight: 700 !important;
        color: #030712 !important;
        margin-bottom: 0.85rem !important;
    }
    section[data-testid="stMain"] h2,
    section[data-testid="stMain"] h3 {
        font-weight: 700 !important;
        color: #111827 !important;
        border-bottom: 2px solid #d1d5db;
        padding-bottom: 0.45rem;
        margin-top: 1.25rem;
        margin-bottom: 1rem !important;
    }
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        border-bottom: none !important;
        padding-bottom: 0 !important;
        margin-bottom: 0.65rem !important;
    }

    /* 区切り線（前後に余白） */
    [data-testid="stDivider"] {
        margin-top: 1.5rem !important;
        margin-bottom: 1.5rem !important;
    }
    hr,
    [data-testid="stDivider"] hr {
        margin: 0 !important;
        border: none !important;
        border-top: 2px solid #9ca3af !important;
        opacity: 1 !important;
    }

    /* 見出し直後のコンテンツとの間隔 */
    section[data-testid="stMain"] [data-testid="stSubheader"],
    section[data-testid="stMain"] [data-testid="stHeader"] {
        margin-bottom: 0.35rem !important;
    }
    [data-testid="stCaptionContainer"] {
        margin-top: 0.4rem !important;
        margin-bottom: 0.65rem !important;
    }

    /* メトリクス */
    [data-testid="stMetric"] {
        background-color: #f3f4f6 !important;
        border: 1px solid #9ca3af !important;
        border-radius: 0.5rem !important;
        padding: 0.65rem 0.85rem !important;
        margin-bottom: 0.5rem !important;
        box-sizing: border-box !important;
    }
    [data-testid="stMetricLabel"] {
        color: #374151 !important;
        font-weight: 600 !important;
    }
    [data-testid="stMetricValue"] {
        color: #030712 !important;
        font-weight: 700 !important;
    }

    /* テーブル枠（内側の罫線と二重にならないよう外枠のみ） */
    [data-testid="stTable"] > div {
        border: 1px solid #9ca3af !important;
        border-radius: 0.375rem !important;
        overflow: hidden !important;
        margin-top: 0.6rem !important;
        margin-bottom: 0.85rem !important;
    }

    /* 入力欄ラベル（座席・De-ice・燃料の見出しと同じ大きさ） */
    section[data-testid="stMain"] [data-testid="stWidgetLabel"] p,
    section[data-testid="stMain"] [data-testid="stWidgetLabel"] label {
        font-size: 1rem !important;
        font-weight: 700 !important;
        color: #111827 !important;
    }
    section[data-testid="stMain"] [data-testid="column"] p strong {
        font-size: 1rem !important;
        font-weight: 700 !important;
        color: #111827 !important;
    }

    /* 重量入力のグレー枠内の白い線を除去 */
    section[data-testid="stMain"] [data-testid="stNumberInput"] > div,
    section[data-testid="stMain"] [data-testid="stNumberInputContainer"] {
        background-color: #e5e7eb !important;
        border: 1px solid #9ca3af !important;
        border-radius: 0.375rem !important;
    }
    section[data-testid="stMain"] [data-testid="stNumberInput"] input,
    section[data-testid="stMain"] [data-testid="stNumberInputField"] {
        background-color: #e5e7eb !important;
        color: #111827 !important;
        border: none !important;
        box-shadow: none !important;
    }
    section[data-testid="stMain"] [data-testid="stNumberInput"] button {
        background-color: #d1d5db !important;
        color: #111827 !important;
        border: none !important;
        border-left: 1px solid #9ca3af !important;
        box-shadow: none !important;
    }
    section[data-testid="stMain"] [data-testid="stNumberInput"] [data-baseweb="input"],
    section[data-testid="stMain"] [data-testid="stNumberInput"] [data-baseweb="input"] > div {
        background-color: #e5e7eb !important;
        border: none !important;
        box-shadow: none !important;
    }
    section[data-testid="stMain"] [data-testid="stSelectbox"] [data-baseweb="select"] > div {
        background-color: #e5e7eb !important;
        border: 1px solid #9ca3af !important;
        border-radius: 0.375rem !important;
    }
    section[data-testid="stMain"] [data-testid="stSelectbox"] [data-baseweb="select"] > div > div {
        background-color: #e5e7eb !important;
        border: none !important;
    }

    /* カラム内の縦方向の詰まりを緩和 */
    section[data-testid="stMain"] [data-testid="column"] {
        padding-top: 0.2rem;
        padding-bottom: 0.2rem;
    }

    /* 補足テキスト（本文より一段明るいグレー） */
    [data-testid="stCaptionContainer"] p,
    .stCaption, .stCaption p {
        font-size: 0.95rem !important;
        color: #4b5563 !important;
        line-height: 1.55;
    }

    /* 登録者プルダウン（所属タグ色） */
    .wb-sel-ohibirin, .wb-sel-ohibirin span { color: #a21caf !important; font-weight: 700 !important; }
    .wb-sel-jcab, .wb-sel-jcab span { color: #15803d !important; font-weight: 700 !important; }
    .wb-sel-general, .wb-sel-general span { color: #1d4ed8 !important; font-weight: 700 !important; }
    .wb-sel-name, .wb-sel-name span { color: #111827 !important; font-weight: 500 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)


_TABLE_TH_PROPS: list[tuple[str, str]] = [
    ("text-align", "center"),
    ("background-color", "#d1d5db"),
    ("color", "#111827"),
    ("font-weight", "700"),
    ("border-bottom", "2px solid #9ca3af"),
]

_WEIGHT_MODE_MANUAL = "体重を入力/選択"
_WEIGHT_MODE_MANUAL_LEGACY = "体重を入力"
# Rear seat R: 桜美林 + JCAB（wb_registry の import キャッシュに依存しない）
_REAR_RIGHT_SEAT_AFFILIATIONS: tuple[str, ...] = ("桜美林", "JCAB")

_DEICE_MODE_OPTIONS: tuple[str, ...] = ("0L", "22L", "30L", "任意の量を入力")
_DEICE_MODE_CUSTOM = "任意の量を入力"
_DEICE_MODE_LEGACY_RANGE = "22L〜30L"


def _inject_colored_select_options() -> None:
    """登録者・所属プルダウンの選択肢に所属色を付ける。"""
    components.html(
        """
<script>
(function() {
  const MANUAL = "体重を入力/選択";
  const MANUAL_LEGACY = "体重を入力";

  function kind(text) {
    const t = (text || "").trim();
    if (!t || t === MANUAL || t === MANUAL_LEGACY) return null;
    if (t === "桜美林" || t.startsWith("[FO")) return "ohibirin";
    if (t === "JCAB" || t.startsWith("[JCAB]")) return "jcab";
    if (t === "一般" || t.startsWith("[一般]") || t.endsWith("教官")) return "general";
    return null;
  }

  function tagKind(tag) {
    if (tag.startsWith("[FO")) return "ohibirin";
    if (tag === "[JCAB]") return "jcab";
    if (tag === "[一般]") return "general";
    return null;
  }

  function paintRegistrySplit(el, text) {
    const m = text.match(/^(\\[[^\\]]+\\])\\s+(.+)$/);
    if (!m) return false;
    const tk = tagKind(m[1]);
    if (!tk) return false;
    const html =
      '<span class="wb-sel-' + tk + '">' + m[1] + '</span> ' +
      '<span class="wb-sel-name">' + m[2] + '</span>';
    if (el.dataset.wbColored !== text) {
      el.innerHTML = html;
      el.dataset.wbColored = text;
    }
    return true;
  }

  function paintSimple(el, text) {
    const k = kind(text);
    if (!k) return;
    el.classList.remove("wb-sel-ohibirin", "wb-sel-jcab", "wb-sel-general", "wb-sel-name");
    el.classList.add("wb-sel-" + k);
    el.dataset.wbColored = text;
  }

  function paintListItem(li) {
    const text = (li.textContent || "").trim();
    if (!text) return;
    li.classList.remove("wb-sel-ohibirin", "wb-sel-jcab", "wb-sel-general", "wb-sel-name");
    if (paintRegistrySplit(li, text)) return;
    paintSimple(li, text);
    li.querySelectorAll("span").forEach((span) => paintSimple(span, text));
  }

  function paintSelected() {
    document.querySelectorAll('[data-testid="stSelectbox"] [data-baseweb="select"] > div > div').forEach((box) => {
      box.querySelectorAll("span").forEach((span) => {
        const text = (span.textContent || "").trim();
        if (!text || text === MANUAL || text === MANUAL_LEGACY) {
          span.classList.remove("wb-sel-ohibirin", "wb-sel-jcab", "wb-sel-general", "wb-sel-name");
          span.removeAttribute("data-wb-colored");
          return;
        }
        span.classList.remove("wb-sel-ohibirin", "wb-sel-jcab", "wb-sel-general", "wb-sel-name");
        if (!paintRegistrySplit(span, text)) paintSimple(span, text);
      });
    });
  }

  function run() {
    document.querySelectorAll('div[data-baseweb="popover"] ul li').forEach(paintListItem);
    paintSelected();
  }

  const obs = new MutationObserver(() => run());
  obs.observe(document.body, { childList: true, subtree: true });
  run();
  window.addEventListener("click", () => setTimeout(run, 40));
})();
</script>
        """,
        height=0,
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


def point_in_polygon(x: float, y: float, polygon: list[tuple[float, float]]) -> bool:
    """多角形の内外判定（ray casting）。polygon は (x, y) の外周順。"""
    if len(polygon) < 3:
        return False
    inside = False
    n = len(polygon)
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[(i + 1) % n]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
    return inside


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


DEFAULT_TOPVIEW_LAYOUT: dict[str, dict[str, float]] = {
    # 座標は SVG viewBox (0..520, 0..820) 基準
    # 中央のスタックは「くっつける」イメージ
    "front_l": {"x": 190, "y": 230, "w": 65, "h": 95, "pill_dx": 8, "pill_dy": 35, "label_dy": -6},
    "front_r": {"x": 265, "y": 230, "w": 65, "h": 95, "pill_dx": 8, "pill_dy": 35, "label_dy": -6},
    "cockpit_bag": {"x": 165, "y": 328, "w": 190, "h": 40, "pill_dx": 72, "pill_dy": 8, "label_dy": -5},
    "rear_l": {"x": 190, "y": 372, "w": 65, "h": 85, "pill_dx": 8, "pill_dy": 30, "label_dy": -7},
    "rear_r": {"x": 265, "y": 372, "w": 65, "h": 85, "pill_dx": 8, "pill_dy": 30, "label_dy": -7},
    "bag_ext": {"x": 170, "y": 462, "w": 180, "h": 55, "pill_dx": 67, "pill_dy": 15, "label_dy": -5},
    "nose_bag": {"x": 225, "y": 65, "w": 70, "h": 55, "pill_dx": 12, "pill_dy": 17, "label_dy": -5},
    "deice_l": {"x": 210, "y": 145, "w": 100, "h": 70, "pill_dx": 25, "pill_dy": 24, "label_dy": -2},
    # Fuel は「他と離す」+ 翼の上
    "fuel_l": {"x": 40, "y": 280, "w": 130, "h": 72, "pill_dx": 25, "pill_dy": 23, "label_dy": -6},
    "fuel_r": {"x": 350, "y": 280, "w": 130, "h": 72, "pill_dx": 24, "pill_dy": 23, "label_dy": -6},
}


def render_top_view_svg(
    values: dict[str, float],
    unit_weight: str,
    *,
    edit_mode: bool = False,
    layout: dict[str, dict[str, float]] | None = None,
    background_png_data_uri: str | None = None,
) -> str:
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

    def L(key: str) -> dict[str, float]:
        base = DEFAULT_TOPVIEW_LAYOUT.get(key, {})
        ov = (layout or {}).get(key, {}) if isinstance(layout, dict) else {}
        merged = {**base, **(ov or {})}
        return {
            "x": float(merged.get("x", 0.0)),
            "y": float(merged.get("y", 0.0)),
            "w": float(merged.get("w", 80.0)),
            "h": float(merged.get("h", 60.0)),
            "pill_dx": float(merged.get("pill_dx", 10.0)),
            "pill_dy": float(merged.get("pill_dy", 20.0)),
            "label_dy": float(merged.get("label_dy", -6.0)),
        }

    # 背景PNG（上面図）
    bg = ""
    has_bg = bool(background_png_data_uri)
    if has_bg:
        # 参照画像をそのまま背景に敷く（“全く同じ”見た目に近づける）
        #
        # 画像を少し拡大（ズーム）して、入力枠が機体の中に収まりやすいようにする。
        # center を基準にスケールし、微調整は pan_x/pan_y で行う。
        bg_scale = 1.52
        pan_x = -10.0
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

    # 便利: draggable group 生成（main rect + resize handle）
    def _group_open(key: str) -> str:
        return f'<g data-key="{key}">'

    def _group_close() -> str:
        return "</g>"

    def _resize_handle(key: str, x: float, y: float, w: float, h: float) -> str:
        return f'<rect id="handle-{key}" class="resize-handle overlay overlayRect" x="{(x + w - 10):.1f}" y="{(y + h - 10):.1f}" width="10" height="10" rx="2" />'

    edit_js = "true" if edit_mode else "false"

    return f"""
<div style="width:100%; max-width:600px; margin:0 auto;">
<script>
  function setLayout(key, x, y, w, h) {{
    try {{
      const u = new URL(window.top.location.href);
      u.searchParams.set('edit', key);
      u.searchParams.set('lx', String(Math.round(x)));
      u.searchParams.set('ly', String(Math.round(y)));
      u.searchParams.set('lw', String(Math.round(w)));
      u.searchParams.set('lh', String(Math.round(h)));
      u.hash = 'topview';
      window.top.location.href = u.toString();
    }} catch (e) {{
      const u = new URL(window.location.href);
      u.searchParams.set('edit', key);
      u.searchParams.set('lx', String(Math.round(x)));
      u.searchParams.set('ly', String(Math.round(y)));
      u.searchParams.set('lw', String(Math.round(w)));
      u.searchParams.set('lh', String(Math.round(h)));
      u.hash = 'topview';
      window.location.href = u.toString();
    }}
  }}

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

  // drag & resize
  (function () {{
    const EDIT_MODE = {edit_js};
    if (!EDIT_MODE) return;

    const root = document.currentScript?.parentElement;
    const svg = root?.querySelector('svg');
    if (!svg) return;

    let active = null;
    const MIN_W = 60;
    const MIN_H = 40;

    function cssEscape(s) {{
      // CSS.escape が無い環境もあるための簡易版
      const str = String(s ?? "");
      if (window.CSS && typeof window.CSS.escape === "function") return window.CSS.escape(str);
      return str.replace(/[^a-zA-Z0-9_-]/g, "\\\\$&");
    }}

    function sel(idPrefix, key) {{
      return "#" + idPrefix + "-" + cssEscape(key);
    }}

    function getSVGPoint(evt) {{
      const pt = svg.createSVGPoint();
      pt.x = evt.clientX;
      pt.y = evt.clientY;
      const ctm = svg.getScreenCTM();
      if (!ctm) return {{x: 0, y: 0}};
      const p = pt.matrixTransform(ctm.inverse());
      return {{x: p.x, y: p.y}};
    }}

    function start(evt, key, mode) {{
      evt.preventDefault();
      evt.stopPropagation();
      const p = getSVGPoint(evt);
      const rect = svg.querySelector(sel("rect", key));
      if (!rect) return;
      const x = parseFloat(rect.getAttribute('x') || '0');
      const y = parseFloat(rect.getAttribute('y') || '0');
      const w = parseFloat(rect.getAttribute('width') || '0');
      const h = parseFloat(rect.getAttribute('height') || '0');
      active = {{ key, mode, sx: p.x, sy: p.y, ox: x, oy: y, ow: w, oh: h, pid: evt.pointerId }};
      try {{ svg.setPointerCapture(evt.pointerId); }} catch (e) {{}}
    }}

    function move(evt) {{
      if (!active) return;
      const p = getSVGPoint(evt);
      const dx = p.x - active.sx;
      const dy = p.y - active.sy;
      const rect = svg.querySelector(sel("rect", active.key));
      const handle = svg.querySelector(sel("handle", active.key));
      const label = svg.querySelector(sel("label", active.key));
      if (!rect) return;

      let x = active.ox;
      let y = active.oy;
      let w = active.ow;
      let h = active.oh;

      if (active.mode === 'move') {{
        x = active.ox + dx;
        y = active.oy + dy;
      }} else {{
        w = Math.max(MIN_W, active.ow + dx);
        h = Math.max(MIN_H, active.oh + dy);
      }}

      rect.setAttribute('x', x.toFixed(1));
      rect.setAttribute('y', y.toFixed(1));
      rect.setAttribute('width', w.toFixed(1));
      rect.setAttribute('height', h.toFixed(1));
      if (handle) {{
        handle.setAttribute('x', (x + w - 10).toFixed(1));
        handle.setAttribute('y', (y + h - 10).toFixed(1));
      }}
      if (label) {{
        label.setAttribute('x', (x + w / 2).toFixed(1));
      }}
    }}

    function end(evt) {{
      if (!active) return;
      const rect = svg.querySelector(sel("rect", active.key));
      if (rect) {{
        const x = parseFloat(rect.getAttribute('x') || '0');
        const y = parseFloat(rect.getAttribute('y') || '0');
        const w = parseFloat(rect.getAttribute('width') || '0');
        const h = parseFloat(rect.getAttribute('height') || '0');
        setLayout(active.key, x, y, w, h);
      }}
      try {{ svg.releasePointerCapture(active.pid); }} catch (e) {{}}
      active = null;
    }}

    svg.addEventListener('pointermove', move);
    svg.addEventListener('pointerup', end);
    svg.addEventListener('pointercancel', end);

    svg.querySelectorAll('g[data-key]').forEach((g) => {{
      const key = g.getAttribute('data-key');
      const rect = g.querySelector('rect.main-rect');
      const handle = g.querySelector('rect.resize-handle');
      if (key && rect) rect.addEventListener('pointerdown', (e) => start(e, key, 'move'));
      if (key && handle) handle.addEventListener('pointerdown', (e) => start(e, key, 'resize'));
    }});
  }})();
</script>
<svg viewBox="0 0 520 820" width="100%" height="760" xmlns="http://www.w3.org/2000/svg">
  {bg}
  <defs>
    <style>
      .air {{ fill:#f3f4f6; stroke:#cbd5e1; stroke-width:2; }}
      .outline {{ fill:none; stroke:#94a3b8; stroke-width:2; }}
      /* ForeFlightっぽい見た目（背景なし・グレーの座席/荷物 + 緑の数値） */
      .seat {{ fill:#d1d5db; stroke:#9ca3af; stroke-width:2; rx:12; }}
      .bag  {{ fill:#e5e7eb; stroke:#9ca3af; stroke-width:2; rx:12; }}
      .label {{ fill:#374151; font: 700 14px system-ui, -apple-system, Segoe UI, Roboto; letter-spacing: 0.06em; }}
      .valueBox {{ fill:#16a34a; stroke:#15803d; stroke-width:2; }}
      .value {{ fill:#ffffff; font: 900 22px system-ui, -apple-system, Segoe UI, Roboto; }}
      .small {{ fill:#ffffff; font: 700 14px system-ui, -apple-system, Segoe UI, Roboto; opacity:0.95; }}
      .resize-handle {{ fill:#111827; opacity:0.55; cursor:nwse-resize; }}
      .main-rect {{ cursor:move; }}
      .overlay {{ display: {"block" if edit_mode else "none"}; }}
      .overlayRect {{ pointer-events: {"all" if edit_mode else "none"}; }}
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
  {(_group_open("front_l"))}
  <rect id="rect-front_l" class="seat main-rect" x="{L('front_l')['x']:.1f}" y="{L('front_l')['y']:.1f}" width="{L('front_l')['w']:.1f}" height="{L('front_l')['h']:.1f}"/>
  {_resize_handle("front_l", L('front_l')['x'], L('front_l')['y'], L('front_l')['w'], L('front_l')['h'])}
  <text id="label-front_l" class="label" x="{(L('front_l')['x']):.1f}" y="{(L('front_l')['y'] - 10):.1f}" text-anchor="start">FRONT L</text>
  <rect class="valueBox" x="{(L('front_l')['x'] + 8):.1f}" y="{(L('front_l')['y'] + 26):.1f}" width="{(L('front_l')['w'] - 16):.1f}" height="{(L('front_l')['h'] - 46):.1f}" rx="10"/>
  <text class="value" x="{(L('front_l')['x'] + L('front_l')['w']/2):.1f}" y="{(L('front_l')['y'] + L('front_l')['h']/2 + 6):.1f}" text-anchor="middle">{v("front_l")}</text>
  {(_group_close())}

  {(_group_open("front_r"))}
  <rect id="rect-front_r" class="seat main-rect" x="{L('front_r')['x']:.1f}" y="{L('front_r')['y']:.1f}" width="{L('front_r')['w']:.1f}" height="{L('front_r')['h']:.1f}"/>
  {_resize_handle("front_r", L('front_r')['x'], L('front_r')['y'], L('front_r')['w'], L('front_r')['h'])}
  <text id="label-front_r" class="label" x="{(L('front_r')['x']):.1f}" y="{(L('front_r')['y'] - 10):.1f}" text-anchor="start">FRONT R</text>
  <rect class="valueBox" x="{(L('front_r')['x'] + 8):.1f}" y="{(L('front_r')['y'] + 26):.1f}" width="{(L('front_r')['w'] - 16):.1f}" height="{(L('front_r')['h'] - 46):.1f}" rx="10"/>
  <text class="value" x="{(L('front_r')['x'] + L('front_r')['w']/2):.1f}" y="{(L('front_r')['y'] + L('front_r')['h']/2 + 6):.1f}" text-anchor="middle">{v("front_r")}</text>
  {(_group_close())}

  <!-- rear seats -->
  {(_group_open("rear_l"))}
  <rect id="rect-rear_l" class="seat main-rect" x="{L('rear_l')['x']:.1f}" y="{L('rear_l')['y']:.1f}" width="{L('rear_l')['w']:.1f}" height="{L('rear_l')['h']:.1f}"/>
  {_resize_handle("rear_l", L('rear_l')['x'], L('rear_l')['y'], L('rear_l')['w'], L('rear_l')['h'])}
  <text id="label-rear_l" class="label" x="{(L('rear_l')['x']):.1f}" y="{(L('rear_l')['y'] - 10):.1f}" text-anchor="start">REAR L</text>
  <rect class="valueBox" x="{(L('rear_l')['x'] + 8):.1f}" y="{(L('rear_l')['y'] + 22):.1f}" width="{(L('rear_l')['w'] - 16):.1f}" height="{(L('rear_l')['h'] - 40):.1f}" rx="10"/>
  <text class="value" x="{(L('rear_l')['x'] + L('rear_l')['w']/2):.1f}" y="{(L('rear_l')['y'] + L('rear_l')['h']/2 + 6):.1f}" text-anchor="middle">{v("rear_l")}</text>
  {(_group_close())}

  {(_group_open("rear_r"))}
  <rect id="rect-rear_r" class="seat main-rect" x="{L('rear_r')['x']:.1f}" y="{L('rear_r')['y']:.1f}" width="{L('rear_r')['w']:.1f}" height="{L('rear_r')['h']:.1f}"/>
  {_resize_handle("rear_r", L('rear_r')['x'], L('rear_r')['y'], L('rear_r')['w'], L('rear_r')['h'])}
  <text id="label-rear_r" class="label" x="{(L('rear_r')['x']):.1f}" y="{(L('rear_r')['y'] - 10):.1f}" text-anchor="start">REAR R</text>
  <rect class="valueBox" x="{(L('rear_r')['x'] + 8):.1f}" y="{(L('rear_r')['y'] + 22):.1f}" width="{(L('rear_r')['w'] - 16):.1f}" height="{(L('rear_r')['h'] - 40):.1f}" rx="10"/>
  <text class="value" x="{(L('rear_r')['x'] + L('rear_r')['w']/2):.1f}" y="{(L('rear_r')['y'] + L('rear_r')['h']/2 + 6):.1f}" text-anchor="middle">{v("rear_r")}</text>
  {(_group_close())}

  <!-- nose baggage -->
  {(_group_open("nose_bag"))}
  <rect id="rect-nose_bag" class="bag main-rect" x="{L('nose_bag')['x']:.1f}" y="{L('nose_bag')['y']:.1f}" width="{L('nose_bag')['w']:.1f}" height="{L('nose_bag')['h']:.1f}"/>
  {_resize_handle("nose_bag", L('nose_bag')['x'], L('nose_bag')['y'], L('nose_bag')['w'], L('nose_bag')['h'])}
  <text id="label-nose_bag" class="label" x="{(L('nose_bag')['x']):.1f}" y="{(L('nose_bag')['y'] - 10):.1f}" text-anchor="start">NOSE</text>
  <rect class="valueBox" x="{(L('nose_bag')['x'] + 8):.1f}" y="{(L('nose_bag')['y'] + 12):.1f}" width="{(L('nose_bag')['w'] - 16):.1f}" height="{(L('nose_bag')['h'] - 22):.1f}" rx="10"/>
  <text class="value" x="{(L('nose_bag')['x'] + L('nose_bag')['w']/2):.1f}" y="{(L('nose_bag')['y'] + L('nose_bag')['h']/2 + 6):.1f}" text-anchor="middle">{v("nose_bag")}</text>
  {(_group_close())}

  <!-- de-ice (Nose baggage と Front seats の間) -->
  {(_group_open("deice_l"))}
  <rect id="rect-deice_l" class="bag main-rect" x="{L('deice_l')['x']:.1f}" y="{L('deice_l')['y']:.1f}" width="{L('deice_l')['w']:.1f}" height="{L('deice_l')['h']:.1f}"/>
  {_resize_handle("deice_l", L('deice_l')['x'], L('deice_l')['y'], L('deice_l')['w'], L('deice_l')['h'])}
  <text id="label-deice_l" class="label" x="{(L('deice_l')['x']):.1f}" y="{(L('deice_l')['y'] - 10):.1f}" text-anchor="start">DEICE</text>
  <rect class="valueBox" x="{(L('deice_l')['x'] + 8):.1f}" y="{(L('deice_l')['y'] + 18):.1f}" width="{(L('deice_l')['w'] - 16):.1f}" height="{(L('deice_l')['h'] - 30):.1f}" rx="10"/>
  <text class="value" x="{(L('deice_l')['x'] + L('deice_l')['w']/2):.1f}" y="{(L('deice_l')['y'] + L('deice_l')['h']/2 + 2):.1f}" text-anchor="middle">{v1("deice_l")}</text>
  <text class="small" x="{(L('deice_l')['x'] + L('deice_l')['w']/2):.1f}" y="{(L('deice_l')['y'] + L('deice_l')['h']/2 + 22):.1f}" text-anchor="middle">{v1("deice_kg")} {unit_weight}</text>
  {(_group_close())}

  <!-- cockpit baggage (Front/Rear の間の細長い枠) -->
  {(_group_open("cockpit_bag"))}
  <rect id="rect-cockpit_bag" class="bag main-rect" x="{L('cockpit_bag')['x']:.1f}" y="{L('cockpit_bag')['y']:.1f}" width="{L('cockpit_bag')['w']:.1f}" height="{L('cockpit_bag')['h']:.1f}"/>
  {_resize_handle("cockpit_bag", L('cockpit_bag')['x'], L('cockpit_bag')['y'], L('cockpit_bag')['w'], L('cockpit_bag')['h'])}
  <text id="label-cockpit_bag" class="label" x="{(L('cockpit_bag')['x']):.1f}" y="{(L('cockpit_bag')['y'] - 10):.1f}" text-anchor="start">BAGGAGE</text>
  <rect class="valueBox" x="{(L('cockpit_bag')['x'] + 8):.1f}" y="{(L('cockpit_bag')['y'] + 8):.1f}" width="{(L('cockpit_bag')['w'] - 16):.1f}" height="{(L('cockpit_bag')['h'] - 16):.1f}" rx="10"/>
  <text class="value" x="{(L('cockpit_bag')['x'] + L('cockpit_bag')['w']/2):.1f}" y="{(L('cockpit_bag')['y'] + L('cockpit_bag')['h']/2 + 8):.1f}" text-anchor="middle">{v("cockpit_bag")}</text>
  {(_group_close())}

  <!-- baggage extension -->
  {(_group_open("bag_ext"))}
  <rect id="rect-bag_ext" class="bag main-rect" x="{L('bag_ext')['x']:.1f}" y="{L('bag_ext')['y']:.1f}" width="{L('bag_ext')['w']:.1f}" height="{L('bag_ext')['h']:.1f}"/>
  {_resize_handle("bag_ext", L('bag_ext')['x'], L('bag_ext')['y'], L('bag_ext')['w'], L('bag_ext')['h'])}
  <text id="label-bag_ext" class="label" x="{(L('bag_ext')['x']):.1f}" y="{(L('bag_ext')['y'] - 10):.1f}" text-anchor="start">BAG EXT</text>
  <rect class="valueBox" x="{(L('bag_ext')['x'] + 10):.1f}" y="{(L('bag_ext')['y'] + 14):.1f}" width="{(L('bag_ext')['w'] - 20):.1f}" height="{(L('bag_ext')['h'] - 26):.1f}" rx="12"/>
  <text class="value" x="{(L('bag_ext')['x'] + L('bag_ext')['w']/2):.1f}" y="{(L('bag_ext')['y'] + L('bag_ext')['h']/2 + 8):.1f}" text-anchor="middle">{v("bag_ext")}</text>
  {(_group_close())}

  <!-- fuel (left wing / right wing) -->
  {(_group_open("fuel_l"))}
  <rect id="rect-fuel_l" class="bag main-rect" x="{L('fuel_l')['x']:.1f}" y="{L('fuel_l')['y']:.1f}" width="{L('fuel_l')['w']:.1f}" height="{L('fuel_l')['h']:.1f}"/>
  {_resize_handle("fuel_l", L('fuel_l')['x'], L('fuel_l')['y'], L('fuel_l')['w'], L('fuel_l')['h'])}
  <text id="label-fuel_l" class="label" x="{(L('fuel_l')['x']):.1f}" y="{(L('fuel_l')['y'] - 10):.1f}" text-anchor="start">FUEL L</text>
  <rect class="valueBox" x="{(L('fuel_l')['x'] + 8):.1f}" y="{(L('fuel_l')['y'] + 18):.1f}" width="{(L('fuel_l')['w'] - 16):.1f}" height="{(L('fuel_l')['h'] - 30):.1f}" rx="12"/>
  <text class="value" x="{(L('fuel_l')['x'] + L('fuel_l')['w']/2):.1f}" y="{(L('fuel_l')['y'] + L('fuel_l')['h']/2 + 2):.1f}" text-anchor="middle">{v1("fuel_l_gal")}</text>
  <text class="small" x="{(L('fuel_l')['x'] + L('fuel_l')['w']/2):.1f}" y="{(L('fuel_l')['y'] + L('fuel_l')['h']/2 + 22):.1f}" text-anchor="middle">{v1("fuel_l_kg")} {unit_weight}</text>
  {(_group_close())}

  {(_group_open("fuel_r"))}
  <rect id="rect-fuel_r" class="bag main-rect" x="{L('fuel_r')['x']:.1f}" y="{L('fuel_r')['y']:.1f}" width="{L('fuel_r')['w']:.1f}" height="{L('fuel_r')['h']:.1f}"/>
  {_resize_handle("fuel_r", L('fuel_r')['x'], L('fuel_r')['y'], L('fuel_r')['w'], L('fuel_r')['h'])}
  <text id="label-fuel_r" class="label" x="{(L('fuel_r')['x']):.1f}" y="{(L('fuel_r')['y'] - 10):.1f}" text-anchor="start">FUEL R</text>
  <rect class="valueBox" x="{(L('fuel_r')['x'] + 8):.1f}" y="{(L('fuel_r')['y'] + 18):.1f}" width="{(L('fuel_r')['w'] - 16):.1f}" height="{(L('fuel_r')['h'] - 30):.1f}" rx="12"/>
  <text class="value" x="{(L('fuel_r')['x'] + L('fuel_r')['w']/2):.1f}" y="{(L('fuel_r')['y'] + L('fuel_r')['h']/2 + 2):.1f}" text-anchor="middle">{v1("fuel_r_gal")}</text>
  <text class="small" x="{(L('fuel_r')['x'] + L('fuel_r')['w']/2):.1f}" y="{(L('fuel_r')['y'] + L('fuel_r')['h']/2 + 22):.1f}" text-anchor="middle">{v1("fuel_r_kg")} {unit_weight}</text>
  {(_group_close())}
</svg>
</div>
"""

 

    def seat_box(key: str, label: str, value_key: str) -> str:
        p = L(key)
        x, y, w, h = p["x"], p["y"], p["w"], p["h"]
        pill_x = x + p["pill_dx"]
        pill_y = y + p["pill_dy"]
        cx = x + w / 2.0
        return f"""
  {g_open(key)}
  <rect class="seat" x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}"/>
  <text class="label" x="{cx:.1f}" y="{(y + p['label_dy']):.1f}" text-anchor="middle">{label}</text>
  <rect class="pill" x="{pill_x:.1f}" y="{pill_y:.1f}" width="50" height="34" rx="10"/>
  <text class="pillText" x="{(pill_x + 25):.1f}" y="{(pill_y + 25):.1f}" text-anchor="middle">{v(value_key)}</text>
  <text class="small" x="{(pill_x + 25):.1f}" y="{(pill_y + 49):.1f}" text-anchor="middle">{unit_weight}</text>
  {g_close()}
"""

    def bag_box(key: str, label: str, value_text: str, *, second_line: str | None = None) -> str:
        p = L(key)
        x, y, w, h = p["x"], p["y"], p["w"], p["h"]
        pill_x = x + p["pill_dx"]
        pill_y = y + p["pill_dy"]
        cx = x + w / 2.0
        extra = ""
        if second_line is not None:
            extra = f'<text class="small" x="{(pill_x + 25):.1f}" y="{(pill_y + 49):.1f}" text-anchor="middle">{second_line}</text>'
        return f"""
  {g_open(key)}
  <rect class="bag" x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}"/>
  <text class="label" x="{cx:.1f}" y="{(y + p['label_dy']):.1f}" text-anchor="middle">{label}</text>
  <rect class="pill" x="{pill_x:.1f}" y="{pill_y:.1f}" width="50" height="34" rx="10"/>
  <text class="pillText" x="{(pill_x + 25):.1f}" y="{(pill_y + 25):.1f}" text-anchor="middle">{value_text}</text>
  {extra}
  {g_close()}
"""

    fuel_l = bag_box("fuel_l", "Fuel L", v1("fuel_l_gal"), second_line=f'{v1("fuel_l_kg")} {unit_weight}')
    fuel_r = bag_box("fuel_r", "Fuel R", v1("fuel_r_gal"), second_line=f'{v1("fuel_r_kg")} {unit_weight}')

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
      .seat {{ fill:#d1d5db; stroke:#6b7280; stroke-width:2; rx:12; }}
      .bag  {{ fill:#e5e7eb; stroke:#6b7280; stroke-width:2; rx:12; }}
      .pill {{ fill:#16a34a; }}
      .pillText {{ fill:white; font: 700 22px system-ui, -apple-system, Segoe UI, Roboto; }}
      .label {{ fill:#111827; font: 600 16px system-ui, -apple-system, Segoe UI, Roboto; }}
      .small {{ fill:#1f2937; font: 500 14px system-ui, -apple-system, Segoe UI, Roboto; }}
    </style>
  </defs>

  {seat_box("front_l", "Front L", "front_l")}
  {seat_box("front_r", "Front R", "front_r")}
  {seat_box("rear_l", "Rear L", "rear_l")}
  {seat_box("rear_r", "Rear R", "rear_r")}

  {bag_box("nose_bag", "Nose", v("nose_bag"))}
  {bag_box("deice_l", "De-ice", v1("deice_l"), second_line=f'{v1("deice_kg")} {unit_weight}')}
  {bag_box("cockpit_bag", "CockpitBaggage", v("cockpit_bag"))}
  {bag_box("bag_ext", "BaggageExtension", v("bag_ext"))}

  {fuel_l}
  {fuel_r}
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
    try:
        from wb_logic import compute_da42_points, evaluate_components, within_limits
    except Exception:
        st.error("`wb_logic` の読み込みでエラーが発生しました。")
        st.code(traceback.format_exc())
        st.stop()

    # 直接PDF生成（ReportLab）
    try:
        from wb_pdf_direct import build_direct_pdf
    except Exception:
        build_direct_pdf = None  # type: ignore[assignment]

    cfg = load_aircraft_config()
    aircraft_name = str(cfg.get("meta", {}).get("aircraft_name", "重量・重心計算"))
    fleet_default = str(cfg.get("fleet", {}).get("default_tail", "") or "")
    aircraft_map = cfg.get("aircraft", {}) or {}

    unit_weight = str(cfg.get("units", {}).get("weight", "kg"))
    unit_arm = str(cfg.get("units", {}).get("arm", "mm"))
    arm_scale = 0.001 if unit_arm.strip().lower() == "mm" else 1.0
    unit_arm_disp = "m" if arm_scale == 0.001 else unit_arm

    def disp_arm(x: float) -> float:
        return float(x) * arm_scale

    def undisp_arm(x: float) -> float:
        return float(x) / arm_scale if arm_scale != 0 else float(x)

    try:
        import importlib
        import wb_registry as _wb_registry_mod

        importlib.reload(_wb_registry_mod)
        from wb_registry import (
            AFFILIATION_OPTIONS,
            FRONT_LEFT_AFFILIATIONS,
            OHIBIRIN_AFFILIATION,
            OHIBIRIN_COHORT_OPTIONS,
            deletable_display_options,
            format_registry_display,
            format_registry_display_html,
            format_registry_list_item_html,
            format_affiliation_html,
            affiliation_color,
            front_right_instructor_map,
            front_right_instructor_names,
            is_protected_name,
            load_registry,
            registry_display_entry_map,
            remove_entry,
            save_registry,
            seat_name_to_display_map_for_affiliations,
            seat_selectable_display_map_for_affiliations,
            sort_registry_entries_for_display,
            upsert_entry,
        )
    except Exception:
        st.error("`wb_registry` の読み込みでエラーが発生しました。")
        st.code(traceback.format_exc())
        st.stop()

    with st.sidebar:
        st.markdown(
            """
            <style>
            section[data-testid="stSidebar"] button[kind="primary"] {
                background-color: #dc2626 !important;
                border-color: #dc2626 !important;
                color: #ffffff !important;
            }
            section[data-testid="stSidebar"] button[kind="primary"]:hover {
                background-color: #b91c1c !important;
                border-color: #b91c1c !important;
                color: #ffffff !important;
            }
            section[data-testid="stSidebar"] [data-testid="stExpanderDetails"] {
                transform: none !important;
                filter: none !important;
                backface-visibility: visible !important;
            }
            section[data-testid="stSidebar"] [data-baseweb="select"] > div,
            section[data-testid="stSidebar"] [data-baseweb="select"] span,
            section[data-testid="stSidebar"] [data-baseweb="select"] input,
            div[data-baseweb="popover"] ul li,
            div[data-baseweb="popover"] ul li span {
                -webkit-font-smoothing: subpixel-antialiased !important;
                -moz-osx-font-smoothing: auto !important;
                text-rendering: geometricPrecision !important;
                font-weight: 500 !important;
                opacity: 1 !important;
                filter: none !important;
                transform: none !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        st.header("体重登録")
        registry_entries = load_registry()
        display_entries = sort_registry_entries_for_display(
            [e for e in registry_entries if not is_protected_name(str(e["name"]))]
        )

        with st.expander("追加・更新", expanded=False):
            form_id = int(st.session_state.get("weight_reg_form_id", 0))
            reg_name_key = f"weight_reg_name_{form_id}"
            aff_key = f"weight_reg_affiliation_{form_id}"
            cohort_key = f"weight_reg_cohort_{form_id}"
            weight_key = f"weight_reg_value_{form_id}"

            reg_name_value = str(st.session_state.get(reg_name_key, "")).strip()
            matched_entry = (
                next((e for e in registry_entries if str(e["name"]) == reg_name_value), None)
                if reg_name_value
                else None
            )

            st.markdown("**所属**")
            reg_cohort = ""
            if matched_entry:
                reg_affiliation = str(matched_entry.get("affiliation", "一般"))
                st.markdown(
                    f"<div style='padding:0.35rem 0.6rem;border:1px solid #d1d5db;border-radius:0.4rem;"
                    f"background:#f9fafb;'>{format_affiliation_html(reg_affiliation)}</div>",
                    unsafe_allow_html=True,
                )
                if reg_affiliation == OHIBIRIN_AFFILIATION:
                    reg_cohort = str(matched_entry.get("cohort", ""))
                    st.markdown("**期**")
                    st.markdown(
                        f"<div style='padding:0.35rem 0.6rem;border:1px solid #d1d5db;border-radius:0.4rem;"
                        f"background:#f9fafb;'><span style='color:{affiliation_color(OHIBIRIN_AFFILIATION)};font-weight:700;'>"
                        f"{reg_cohort or '—'}</span></div>",
                        unsafe_allow_html=True,
                    )
            else:
                reg_affiliation = st.selectbox(
                    "所属を選択",
                    AFFILIATION_OPTIONS,
                    index=AFFILIATION_OPTIONS.index("一般"),
                    key=aff_key,
                )
                st.markdown(format_affiliation_html(reg_affiliation), unsafe_allow_html=True)
                if reg_affiliation == OHIBIRIN_AFFILIATION:
                    reg_cohort = st.selectbox("期", OHIBIRIN_COHORT_OPTIONS, key=cohort_key)
                elif cohort_key in st.session_state:
                    st.session_state.pop(cohort_key, None)

            reg_name = st.text_input("氏名", key=reg_name_key)
            reg_weight = st.number_input(
                f"体重 [{unit_weight}]",
                min_value=0.0,
                max_value=200.0,
                step=0.1,
                format="%.1f",
                key=weight_key,
            )
            if st.button("登録", key="weight_reg_save", type="primary", use_container_width=True):
                if not reg_name.strip():
                    st.warning("氏名を入力してください。")
                else:
                    save_matched = next(
                        (e for e in registry_entries if str(e["name"]) == reg_name.strip()),
                        None,
                    )
                    save_affiliation = (
                        str(save_matched.get("affiliation", "一般"))
                        if save_matched
                        else str(st.session_state.get(aff_key, "一般"))
                    )
                    save_cohort = (
                        str(save_matched.get("cohort", ""))
                        if save_matched
                        else str(st.session_state.get(cohort_key, ""))
                    )
                    if save_affiliation == OHIBIRIN_AFFILIATION and not save_cohort:
                        st.warning("桜美林を選択した場合は期を選択してください。")
                    else:
                        updated = upsert_entry(
                            registry_entries,
                            reg_name,
                            reg_weight,
                            save_affiliation,
                            save_cohort,
                        )
                        try:
                            save_registry(updated)
                        except OSError as exc:
                            st.error(f"体重登録の保存に失敗しました: {exc}")
                        else:
                            st.session_state["weight_reg_form_id"] = form_id + 1
                            st.rerun()

        with st.expander("削除", expanded=False):
            del_options = deletable_display_options(registry_entries)
            if del_options:
                del_labels = [label for label, _ in del_options]
                del_name_by_label = {label: name for label, name in del_options}
                del_label = st.selectbox("削除する登録", del_labels, key="weight_reg_del_label")
                del_name = del_name_by_label[del_label]
                if st.button("削除", key="weight_reg_delete", use_container_width=True):
                    updated = remove_entry(registry_entries, del_name)
                    try:
                        save_registry(updated)
                    except OSError as exc:
                        st.error(f"体重登録の保存に失敗しました: {exc}")
                    else:
                        del_entry = next(e for e in registry_entries if str(e["name"]) == del_name)
                        del_display = format_registry_display(del_entry)
                        del_affiliation = str(del_entry.get("affiliation", "一般"))
                        if del_affiliation in FRONT_LEFT_AFFILIATIONS and st.session_state.get("front_l_mode") == del_display:
                            st.session_state["front_l_mode"] = _WEIGHT_MODE_MANUAL
                        if del_affiliation in _REAR_RIGHT_SEAT_AFFILIATIONS and st.session_state.get("rear_r_mode") == del_display:
                            st.session_state["rear_r_mode"] = _WEIGHT_MODE_MANUAL
                        if st.session_state.get("front_r_mode") == del_name:
                            st.session_state["front_r_mode"] = _WEIGHT_MODE_MANUAL
                        for pop_key in ("front_l_manual", "rear_r_manual", "front_r_manual"):
                            st.session_state.pop(pop_key, None)
                        st.rerun()
            else:
                st.caption("削除できる登録がありません。")

        with st.expander("登録者一覧", expanded=False):
            if display_entries:
                for entry in display_entries:
                    st.markdown(
                        f"- {format_registry_list_item_html(entry, unit_weight=unit_weight)}",
                        unsafe_allow_html=True,
                    )
            else:
                st.caption("登録がありません")

        instructor_map = front_right_instructor_map(registry_entries)
        front_l_registry_display_map = seat_selectable_display_map_for_affiliations(
            registry_entries, FRONT_LEFT_AFFILIATIONS
        )
        front_l_name_to_display = seat_name_to_display_map_for_affiliations(
            registry_entries, FRONT_LEFT_AFFILIATIONS
        )
        rear_r_registry_display_map = seat_selectable_display_map_for_affiliations(
            registry_entries, _REAR_RIGHT_SEAT_AFFILIATIONS
        )
        rear_r_name_to_display = seat_name_to_display_map_for_affiliations(
            registry_entries, _REAR_RIGHT_SEAT_AFFILIATIONS
        )
        registry_display_entries = registry_display_entry_map(registry_entries)

        st.divider()
        st.header("機体選択")
        tails = sorted([str(k) for k in aircraft_map.keys()]) if isinstance(aircraft_map, dict) else []
        if tails:
            default_idx = tails.index(fleet_default) if fleet_default in tails else 0
            tail = st.selectbox("登録記号", tails, index=default_idx)
            selected = aircraft_map.get(tail, {}) if isinstance(aircraft_map, dict) else {}
        else:
            tail = ""
            selected = {}

    st.title("DA42 WB")
    _inject_colored_select_options()
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

        st.subheader("基本空重（BEW）")
        sel_be = selected.get("basic_empty", {}) if isinstance(selected, dict) else {}
        bew_w = num(sel_be.get("weight", cfg.get("basic_empty", {}).get("weight", 0.0)))
        bew_a = num(sel_be.get("arm", cfg.get("basic_empty", {}).get("arm", 0.0)))
        st.write(f"- 重量: **{bew_w:,.2f} {unit_weight}**")
        st.write(f"- アーム: **{disp_arm(bew_a):,.3f} {unit_arm_disp}**")

        # limits: 機体ごとの上書きを優先
        lim_default = cfg.get("limits", {}) or {}
        lim_override = selected.get("limits", {}) if isinstance(selected, dict) else {}
        lim = {**lim_default, **(lim_override or {})}
        use_limits = bool(lim.get("use_fixed_cg", False))
        cg_min = num(lim.get("cg_min", 0.0)) if use_limits else None
        cg_max = num(lim.get("cg_max", 0.0)) if use_limits else None
        use_limits = st.checkbox("固定CG範囲で判定する", value=use_limits)
        if use_limits:
            cg_min_ui = st.number_input("CG最小", value=float(disp_arm(cg_min or 0.0)), format="%.3f")
            cg_max_ui = st.number_input("CG最大", value=float(disp_arm(cg_max or 0.0)), format="%.3f")
            cg_min = undisp_arm(cg_min_ui)
            cg_max = undisp_arm(cg_max_ui)

        st.subheader("重量制限")
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
    # rear seats のアームが未設定（0）の場合は 3.25m (=3250mm) を採用
    if float(arms.get("rear_seat_left", 0.0) or 0.0) == 0.0:
        arms["rear_seat_left"] = 3250.0
    if float(arms.get("rear_seat_right", 0.0) or 0.0) == 0.0:
        arms["rear_seat_right"] = 3250.0

    if tail:
        st.subheader(f"選択機材: {tail}")
    else:
        st.subheader("選択機材")
        st.warning("未選択です。サイドバーで機体を選んでください。")

    fuel_kg_per_usg = 3.028

    def _ss_num(key: str, default: float = 0.0) -> float:
        return float(st.session_state.get(key, default) or 0.0)

    # 使いやすい初期値（未入力時のみ）
    st.session_state.setdefault("taxi_burn_gal", 1.0)
    st.session_state.setdefault("deice_l", 22.0)
    st.session_state.setdefault("main_fuel_gal", 50.0)
    st.session_state.setdefault("cockpit_bag", 5.0)
    st.session_state.setdefault("bag_ext", 3.0)
    st.session_state.setdefault("front_l_mode", _WEIGHT_MODE_MANUAL)
    st.session_state.setdefault("rear_r_mode", _WEIGHT_MODE_MANUAL)
    st.session_state.setdefault("front_r_mode", _WEIGHT_MODE_MANUAL)

    def _seat_weight_from_registry(
        seat_label: str,
        *,
        mode_key: str,
        weight_key: str,
        manual_key: str,
        registry_display_map: dict[str, float],
        name_to_display: dict[str, str],
        display_entry_map: dict[str, dict[str, float | str]],
    ) -> None:
        options = [_WEIGHT_MODE_MANUAL] + list(registry_display_map.keys())
        prev_mode_key = f"{mode_key}__prev"
        prev_mode = st.session_state.get(prev_mode_key)
        current_mode = st.session_state.get(mode_key)
        if current_mode == _WEIGHT_MODE_MANUAL_LEGACY:
            st.session_state[mode_key] = _WEIGHT_MODE_MANUAL
            current_mode = _WEIGHT_MODE_MANUAL
        if current_mode in front_right_instructor_names():
            st.session_state[mode_key] = _WEIGHT_MODE_MANUAL
        elif current_mode == "増本教官":
            st.session_state[mode_key] = _WEIGHT_MODE_MANUAL
        elif current_mode in name_to_display:
            st.session_state[mode_key] = name_to_display[current_mode]
        elif current_mode not in options:
            st.session_state[mode_key] = _WEIGHT_MODE_MANUAL
        mode = st.selectbox(seat_label, options, key=mode_key)
        if mode == _WEIGHT_MODE_MANUAL:
            if prev_mode not in (None, _WEIGHT_MODE_MANUAL, _WEIGHT_MODE_MANUAL_LEGACY):
                st.session_state[weight_key] = 0.0
                st.session_state.pop(manual_key, None)
            v = st.number_input(
                f"{seat_label}（体重）",
                min_value=0.0,
                step=1.0,
                format="%.1f",
                value=_ss_num(weight_key),
                key=manual_key,
                label_visibility="collapsed",
            )
            st.session_state[weight_key] = float(v)
        else:
            st.session_state[weight_key] = float(registry_display_map.get(mode, 0.0))
            selected_entry = display_entry_map.get(mode)
            if selected_entry:
                st.markdown(
                    f"{format_registry_display_html(selected_entry)}: "
                    f"**{st.session_state[weight_key]:.1f} {unit_weight}**",
                    unsafe_allow_html=True,
                )
            else:
                st.caption(f"{mode}: **{st.session_state[weight_key]:.1f} {unit_weight}**")
        st.session_state[prev_mode_key] = mode

    _, c_reset = st.columns([3, 1], vertical_alignment="bottom")
    with c_reset:
        if st.button("入力をリセット"):
            # 入力値を初期化（使いやすいデフォルトに戻す）
            st.session_state["front_l"] = 45.0
            for k in ["front_r", "rear_l", "rear_r", "nose_bag"]:
                st.session_state[k] = 0.0
            st.session_state["cockpit_bag"] = 5.0
            st.session_state["bag_ext"] = 3.0
            st.session_state["taxi_burn_gal"] = 1.0
            st.session_state["deice_l"] = 22.0
            st.session_state["main_fuel_gal"] = 50.0
            st.session_state["flight_burn_gal"] = 0.0
            st.session_state["return_burn_gal"] = 0.0
            st.session_state["front_l_mode"] = _WEIGHT_MODE_MANUAL
            st.session_state["rear_r_mode"] = _WEIGHT_MODE_MANUAL
            st.session_state["front_r_mode"] = _WEIGHT_MODE_MANUAL
            for pop_key in ("front_l_manual", "rear_r_manual", "front_r_manual"):
                st.session_state.pop(pop_key, None)
            for prev_key in ("front_l_mode__prev", "rear_r_mode__prev"):
                st.session_state.pop(prev_key, None)
            st.rerun()

    # 入力方法はフォームに統一
    col1, col2 = st.columns(2, vertical_alignment="top")
    with col1:
        st.markdown("**座席**")
        _seat_weight_from_registry(
            f"Front seat L [{unit_weight}]",
            mode_key="front_l_mode",
            weight_key="front_l",
            manual_key="front_l_manual",
            registry_display_map=front_l_registry_display_map,
            name_to_display=front_l_name_to_display,
            display_entry_map=registry_display_entries,
        )
        front_r_options = [_WEIGHT_MODE_MANUAL] + front_right_instructor_names()
        if st.session_state.get("front_r_mode") == _WEIGHT_MODE_MANUAL_LEGACY:
            st.session_state["front_r_mode"] = _WEIGHT_MODE_MANUAL
        if st.session_state.get("front_r_mode") == "増本教官":
            st.session_state["front_r_mode"] = "増元教官"
        if st.session_state.get("front_r_mode") not in front_r_options:
            st.session_state["front_r_mode"] = _WEIGHT_MODE_MANUAL
        front_r_mode = st.selectbox(f"Front seat R [{unit_weight}]", front_r_options, key="front_r_mode")
        if front_r_mode == _WEIGHT_MODE_MANUAL:
            v = st.number_input(
                f"Front seat R [{unit_weight}]（体重）",
                min_value=0.0,
                step=1.0,
                format="%.1f",
                value=_ss_num("front_r"),
                key="front_r_manual",
                label_visibility="collapsed",
            )
            st.session_state["front_r"] = float(v)
        else:
            st.session_state["front_r"] = float(instructor_map.get(front_r_mode, 0.0))
            st.caption(f"{front_r_mode}: **{st.session_state['front_r']:.1f} {unit_weight}**")
        st.number_input(f"Rear seat L [{unit_weight}]", min_value=0.0, step=1.0, format="%.1f", key="rear_l")
        _seat_weight_from_registry(
            f"Rear seat R [{unit_weight}]",
            mode_key="rear_r_mode",
            weight_key="rear_r",
            manual_key="rear_r_manual",
            registry_display_map=rear_r_registry_display_map,
            name_to_display=rear_r_name_to_display,
            display_entry_map=registry_display_entries,
        )

        st.markdown("**バゲッジ**")
        if tail in {"JA52DA", "JA53DA", "JA55DA", "JA56DA"}:
            st.number_input(f"Nose baggage [{unit_weight}]", min_value=0.0, max_value=30.0, step=1.0, format="%.1f", key="nose_bag")
            st.number_input(f"Cockpit baggage [{unit_weight}]", min_value=0.0, max_value=45.0, step=1.0, format="%.1f", key="cockpit_bag")
            st.number_input(f"Baggage extension [{unit_weight}]", min_value=0.0, max_value=18.0, step=1.0, format="%.1f", key="bag_ext")
            if _ss_num("cockpit_bag") + _ss_num("bag_ext") > 45.0:
                st.error("JA52/53/55/56: Cockpit baggage + Baggage extension の合計は 45kg 以下にしてください。")
        else:
            st.number_input(f"Nose baggage [{unit_weight}]", min_value=0.0, step=1.0, format="%.1f", key="nose_bag")
            st.number_input(f"Cockpit baggage [{unit_weight}]", min_value=0.0, step=1.0, format="%.1f", key="cockpit_bag")
            st.number_input(f"Baggage extension [{unit_weight}]", min_value=0.0, step=1.0, format="%.1f", key="bag_ext")

    with col2:
        st.markdown("**De-ice / 液体**")
        if tail in {"JA52DA", "JA53DA", "JA55DA", "JA56DA"}:
            if st.session_state.get("deice_mode") == _DEICE_MODE_LEGACY_RANGE:
                st.session_state["deice_mode"] = _DEICE_MODE_CUSTOM

            cur = float(_ss_num("deice_l", 22.0))
            if cur == 0.0:
                deice_mode_index = 0
            elif cur == 22.0:
                deice_mode_index = 1
            elif cur == 30.0:
                deice_mode_index = 2
            elif 22.0 <= cur <= 30.0:
                deice_mode_index = 3
            else:
                st.session_state["deice_l"] = 22.0
                deice_mode_index = 1

            mode = st.radio(
                "De-ice 入力モード",
                list(_DEICE_MODE_OPTIONS),
                index=deice_mode_index,
                key="deice_mode",
            )
            if mode == "0L":
                st.session_state["deice_l"] = 0.0
            elif mode == "22L":
                st.session_state["deice_l"] = 22.0
            elif mode == "30L":
                st.session_state["deice_l"] = 30.0
            else:
                st.number_input("De-ice fluid [L]", min_value=22.0, max_value=30.0, step=1.0, format="%.1f", key="deice_l")
        else:
            st.number_input("De-ice fluid [L]", min_value=0.0, step=1.0, format="%.1f", key="deice_l")
        st.caption(f"換算: {_ss_num('deice_l'):.1f} L → {_ss_num('deice_l') * 1.1:.1f} {unit_weight}")

        st.markdown("**燃料（US gal）**")
        st.number_input("Main fuel loaded [US gal]", min_value=0.0, max_value=50.0, step=1.0, format="%.1f", key="main_fuel_gal")
        st.number_input("Taxi burn [US gal]", min_value=0.0, step=0.1, format="%.1f", key="taxi_burn_gal")
        st.number_input("Flight burn [US gal]", min_value=0.0, step=0.1, format="%.1f", key="flight_burn_gal")
        st.number_input("Return burn [US gal]", min_value=0.0, step=0.1, format="%.1f", key="return_burn_gal")

        mf = _ss_num("main_fuel_gal")
        tb = _ss_num("taxi_burn_gal")
        fb = _ss_num("flight_burn_gal")
        rb = _ss_num("return_burn_gal")
        takeoff_remain = max(mf - tb, 0.0)
        landing1_remain = max(takeoff_remain - fb, 0.0)
        landing2_remain = max(landing1_remain - rb, 0.0)
        st.caption(
            f"換算: {mf:.1f} gal → {mf * fuel_kg_per_usg:.1f} {unit_weight} / "
            f"T/O残 {takeoff_remain:.1f} gal / LDG1残 {landing1_remain:.1f} gal / LDG2残 {landing2_remain:.1f} gal"
        )

    front_l = _ss_num("front_l")
    front_r = _ss_num("front_r")
    rear_l = _ss_num("rear_l")
    rear_r = _ss_num("rear_r")
    nose_bag = _ss_num("nose_bag")
    cockpit_bag = _ss_num("cockpit_bag")
    bag_ext = _ss_num("bag_ext")

    deice_l = _ss_num("deice_l")
    deice_kg = deice_l * 1.1

    main_fuel_gal = _ss_num("main_fuel_gal")
    taxi_burn_gal = _ss_num("taxi_burn_gal")
    flight_burn_gal = _ss_num("flight_burn_gal")
    return_burn_gal = _ss_num("return_burn_gal")

    main_fuel_kg = main_fuel_gal * fuel_kg_per_usg
    taxi_burn_kg = taxi_burn_gal * fuel_kg_per_usg
    flight_burn_kg = flight_burn_gal * fuel_kg_per_usg
    return_burn_kg = return_burn_gal * fuel_kg_per_usg

    st.caption(f"単位: 重量={unit_weight}, アーム={unit_arm_disp}")

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

    # kaleido が plotlyjs をローカルパスで掴めない環境向け（Windowsの日本語ユーザー名等）
    # CDN を使うと安定して PNG 変換できる
    try:
        pio.kaleido.scope.plotlyjs = "https://cdn.plot.ly/plotly-2.27.0.min.js"
    except Exception:
        pass

    # 内訳（ZFM/TOW/LWそれぞれで共通の“入力値”を表示したいので、現在の搭載項目を一覧化）
    def _combined_arm(w1: float, a1: float, w2: float, a2: float) -> float:
        tw = float(w1) + float(w2)
        if tw <= 0:
            return 0.0
        return (float(w1) * float(a1) + float(w2) * float(a2)) / tw

    front_a_l = float(arms.get("front_seat_left", 0.0))
    front_a_r = float(arms.get("front_seat_right", 0.0))
    rear_a_l = float(arms.get("rear_seat_left", 0.0))
    rear_a_r = float(arms.get("rear_seat_right", 0.0))

    # 表示用（順番固定）の内訳を組み立てる
    fuel_arm = float(arms.get("main_fuel", 0.0))
    nose_arm = float(arms.get("nose_baggage", 0.0))
    cockpit_arm = float(arms.get("cockpit_baggage", 0.0))
    bag_ext_arm = float(arms.get("baggage_extension", 0.0))
    deice_arm = float(arms.get("deice_fluid", 0.0))

    front_w = float(front_l + front_r)
    rear_w = float(rear_l + rear_r)
    # 52/53/55/56 は座席のアームが固定（Front=2.30m, Rear=3.25m）
    if tail in {"JA52DA", "JA53DA", "JA55DA", "JA56DA"}:
        front_arm = 2300.0
        rear_arm = 3250.0
    else:
        front_arm = _combined_arm(front_l, front_a_l, front_r, front_a_r)
        rear_arm = _combined_arm(rear_l, rear_a_l, rear_r, rear_a_r)

    def _moment(w: float, a: float) -> float:
        return float(w) * float(a)

    def _row(name: str, w: float, a: float) -> dict:
        return {"name": name, "weight": float(w), "arm": float(a), "moment": _moment(w, a)}

    def _total(name: str, rows: list[dict]) -> dict:
        tw = sum(float(r["weight"]) for r in rows)
        tm = sum(float(r["moment"]) for r in rows)
        a = (tm / tw) if tw > 0 else 0.0
        return {"name": name, "weight": tw, "arm": a, "moment": tm}

    # Basic Empty は設定値の moment_kgm（表示固定値）を ZFW の合算にも使う
    bew_moment_kgm = selected.get("basic_empty", {}).get("moment_kgm") if isinstance(selected, dict) else None
    if isinstance(bew_moment_kgm, (int, float)) and arm_scale != 0:
        bew_moment_internal = float(bew_moment_kgm) / arm_scale  # kg·m -> kg·mm
    else:
        bew_moment_internal = _moment(bew_w, bew_a)

    base_rows = [
        {"name": "Basic Empty", "weight": float(bew_w), "arm": float(bew_a), "moment": float(bew_moment_internal)},
        _row("FrontSeats", front_w, front_arm),
        _row("RearSeats", rear_w, rear_arm),
        _row("Nose baggage", nose_bag, nose_arm),
        _row("Cockpit baggage", cockpit_bag, cockpit_arm),
        _row("Baggage extension", bag_ext, bag_ext_arm),
        _row("De-ice fluid", deice_kg, deice_arm),
    ]
    zfm_row = _total("ZERO FUEL MASS", base_rows)

    main_fuel_row = _row("Main fuel (loaded)", main_fuel_kg, fuel_arm)
    taxi_run_row = _row("TAXI-RUN", -taxi_burn_kg, fuel_arm)

    takeoff_fuel_remain = max(main_fuel_kg - taxi_burn_kg, 0.0)
    tow_row = _total("TAKE OFF WEIGHT", base_rows + [_row("Fuel remaining (T/O)", takeoff_fuel_remain, fuel_arm)])

    out_fuel_cons_row = _row("FUEL Consumption（行き）", -flight_burn_kg, fuel_arm)
    landing1_fuel_remain = max(takeoff_fuel_remain - flight_burn_kg, 0.0)
    ldg1_row = _total("LDG Weight（目的地空港着陸時）", base_rows + [_row("Fuel remaining (LDG1)", landing1_fuel_remain, fuel_arm)])

    return_fuel_cons_row = _row("FUEL Consumption（帰り）", -return_burn_kg, fuel_arm)
    landing2_fuel_remain = max(landing1_fuel_remain - return_burn_kg, 0.0)
    ldg2_row = _total("LDG Weight（帰投時）", base_rows + [_row("Fuel remaining (LDG2)", landing2_fuel_remain, fuel_arm)])

    display_rows = (
        base_rows
        + [zfm_row]
        + [main_fuel_row, taxi_run_row, tow_row]
        + [out_fuel_cons_row, ldg1_row]
        + [return_fuel_cons_row, ldg2_row]
    )

    zfm = points["ZFM"]
    tow = points["TOW"]
    lw1 = points["LW1"]
    lw2 = points["LW2"]

    env_default = cfg.get("envelope", {}) or {}
    env_override = selected.get("envelope", {}) if isinstance(selected, dict) else {}
    env = {**env_default, **(env_override or {})}
    env_points = parse_points(env.get("points", []))

    st.subheader("内訳一覧")
    def _fmt5(x) -> str:
        try:
            s = f"{float(x):.5f}"
            return s.rstrip("0").rstrip(".")
        except Exception:
            return ""

    # 制限値（機体ごとの limits から取得）
    # MZFM=ZERO FUEL MASS, MTOW=TAKE OFF WEIGHT, MLW=LDG Weight
    LIMIT_ZFM = float(mzfm or 0.0) if mzfm else 0.0
    LIMIT_TOW = float(mtow or 0.0) if mtow else 0.0
    LIMIT_LDG = float(mlw or 0.0) if mlw else 0.0

    ldg1_weight = float(ldg1_row.get("weight", 0.0) or 0.0)
    ldg2_weight = float(ldg2_row.get("weight", 0.0) or 0.0)
    ldg1_overrun = max(0.0, ldg1_weight - LIMIT_LDG) if LIMIT_LDG > 0 else 0.0
    ldg2_overrun = max(0.0, ldg2_weight - LIMIT_LDG) if LIMIT_LDG > 0 else 0.0
    has_ldg_weight_overrun = ldg1_overrun > 0 or ldg2_overrun > 0
    ldg_overrun_kg = max(ldg1_overrun, ldg2_overrun)

    def _row_color(name: str, weight: float, arm_mm: float | None) -> str | None:
        weight_limit: float | None = None
        if name == "ZERO FUEL MASS" and LIMIT_ZFM > 0:
            weight_limit = LIMIT_ZFM
        elif name == "TAKE OFF WEIGHT" and LIMIT_TOW > 0:
            weight_limit = LIMIT_TOW
        elif name in {"LDG Weight（目的地空港着陸時）", "LDG Weight（帰投時）"} and LIMIT_LDG > 0:
            weight_limit = LIMIT_LDG
        else:
            return None

        weight_ok = weight <= weight_limit
        if env_points and isinstance(arm_mm, (int, float)):
            arm_ok = point_in_polygon(float(arm_mm), float(weight), env_points)
        elif env_points:
            arm_ok = False
        else:
            arm_ok = True

        if weight_ok and arm_ok:
            return "#15803d"
        return "#b91c1c"

    def _ldg_limit_text(overrun: float) -> str:
        if LIMIT_LDG <= 0:
            return ""
        base = f"{LIMIT_LDG:.0f}kg"
        if overrun > 0:
            return f"{base} / {overrun:.1f}kg超過"
        return base

    def _limit_text(name: str) -> str:
        if name == "LDG Weight（目的地空港着陸時）":
            return _ldg_limit_text(ldg1_overrun)
        if name == "LDG Weight（帰投時）":
            return _ldg_limit_text(ldg2_overrun)
        # 52/53/55/56: ステーション制限（入力値制限）も表示
        if tail in {"JA52DA", "JA53DA", "JA55DA", "JA56DA"}:
            if name == "Nose baggage":
                return "30kg"
            if name == "Cockpit baggage":
                return "45kg"
            if name == "Baggage extension":
                return "18kg"
            if name == "De-ice fluid":
                return "22L - 30L"
            if name == "ZERO FUEL MASS" and LIMIT_ZFM > 0:
                return f"{LIMIT_ZFM:.0f}kg"
            if name == "TAKE OFF WEIGHT" and LIMIT_TOW > 0:
                return f"{LIMIT_TOW:.0f}kg"
            return ""

        if name == "ZERO FUEL MASS" and LIMIT_ZFM > 0:
            return f"{LIMIT_ZFM:.0f}kg"
        if name == "TAKE OFF WEIGHT" and LIMIT_TOW > 0:
            return f"{LIMIT_TOW:.0f}kg"
        return ""

    out = pd.DataFrame(
        {
            "項目": [r.get("name", "") for r in display_rows],
            f"アーム [{unit_arm_disp}]": [
                ("" if not isinstance(r.get("arm"), (int, float)) else _fmt5(disp_arm(float(r["arm"]))))
                for r in display_rows
            ],
            f"重量 [{unit_weight}]": [("" if not isinstance(r.get("weight"), (int, float)) else _fmt5(float(r["weight"]))) for r in display_rows],
            f"モーメント [{unit_weight}·{unit_arm_disp}]": [
                (
                    _fmt5(float(bew_moment_kgm))
                    if r.get("name") == "Basic Empty"
                    else ("" if not isinstance(r.get("moment"), (int, float)) else _fmt5(float(r["moment"]) * arm_scale))
                )
                for r in display_rows
            ],
            "制限": [_limit_text(str(r.get("name", ""))) for r in display_rows],
        }
    )

    # 行ごとの色付け（TOW/LDGの制限判定）＋中央揃え
    def _style_row(row: "pd.Series"):
        name = str(row.get("項目", ""))
        src = display_rows[row.name]
        w = src.get("weight")
        arm_mm = src.get("arm")
        # 以前は制限行を太枠で囲っていたが、太枠は付けない（見た目は従来のまま）
        special = {
            "ZERO FUEL MASS",
            "TAKE OFF WEIGHT",
            "LDG Weight（目的地空港着陸時）",
            "LDG Weight（帰投時）",
        }
        is_special = name in special

        # 色付け（判定できる行だけ、行全体）
        color_css = ""
        if isinstance(w, (int, float)) and is_special:
            arm_val = float(arm_mm) if isinstance(arm_mm, (int, float)) else None
            c = _row_color(name, float(w), arm_val)
            if c:
                color_css = f"background-color: {c}; color: white;"
        emphasis_css = "font-weight: 700;" if is_special else ""

        # 列ごとに枠線を出し分け（行内の仕切りは太くしない）
        cols = list(row.index)
        if not cols:
            return []
        first_col = cols[0]
        last_col = cols[-1]

        per_cell: list[str] = []
        for col in cols:
            cell_css_parts: list[str] = []
            # 制限値のセル自体は色付けしない
            if color_css and col != "制限":
                cell_css_parts.append(color_css)
            if emphasis_css:
                cell_css_parts.append(emphasis_css)
            if col == "制限" and str(row.get(col, "")).strip():
                cell_css_parts.append("color: #dc2626; font-weight: 800;")
            per_cell.append(" ".join(cell_css_parts).strip())

        # 空文字だけだと効かないので、完全空なら空配列を返す
        if all(not s for s in per_cell):
            return [""] * len(row)
        return per_cell

    out_styled = (
        out.style.hide(axis="index")
        .set_properties(**{"text-align": "center"})
        .set_table_styles([{"selector": "th", "props": _TABLE_TH_PROPS}])
        .apply(_style_row, axis=1)
    )
    # スクロールさせず、スタイルが確実に効く表示（table）
    st.table(out_styled)

    st.divider()

    if tail != "JA56DA":
        if has_ldg_weight_overrun:
            st.session_state["fuel_convert_kg"] = ldg_overrun_kg
        with st.expander("燃料換算[ kg to gal/time]", expanded=has_ldg_weight_overrun):
            st.caption("入力した燃料重量が、何 US gal / 何時間何分分かを表示します。")

            fuel_kg = st.number_input("燃料重量 [kg]", min_value=0.0, step=1.0, format="%.1f", key="fuel_convert_kg")
            fuel_gal = (fuel_kg / fuel_kg_per_usg) if fuel_kg_per_usg > 0 else 0.0

            def _hm(hours: float) -> str:
                mins = int(max(0.0, float(hours)) * 60.0)
                return f"{mins // 60}時間{mins % 60}分"

            h10 = _hm(fuel_gal / 10.0) if 10.0 > 0 else "0時間0分"
            h166 = _hm(fuel_gal / 16.6) if 16.6 > 0 else "0時間0分"

            fc1, fc2, fc3 = st.columns(3)
            fc1.metric("換算燃料 [US gal]", f"{fuel_gal:.1f}")
            fc2.metric("10.0 GAL/hr", h10)
            fc3.metric("16.6 GAL/hr", h166)

    remain_gal = max(main_fuel_gal - taxi_burn_gal - flight_burn_gal - return_burn_gal, 0.0)

    def _fmt_hm_from_hours(hours: float) -> str:
        mins = int(max(0.0, float(hours)) * 60.0)
        h = mins // 60
        m = mins % 60
        return f"{h}時間{m}分"

    endurance_hours_10 = remain_gal / 10.0
    endurance_10 = _fmt_hm_from_hours(endurance_hours_10)
    endurance_166 = _fmt_hm_from_hours(remain_gal / 16.6)

    with st.expander("福島帰投時燃料", expanded=False):
        c1, c2, c3 = st.columns(3)
        c1.metric("福島帰投時残燃料 [US gal]", f"{remain_gal:.1f}")
        c2.metric("10.0 GAL/hr", endurance_10)
        c3.metric("16.6 GAL/hr", endurance_166)

    max_nm_120 = max(0.0, endurance_hours_10) * 120.0
    max_nm_140 = max(0.0, endurance_hours_10) * 140.0

    divert = [
        {"空港": "RJSS", "名称": "仙台空港", "距離 [NM]": 61.0},
        {"空港": "RJSN", "名称": "新潟空港", "距離 [NM]": 77.0},
        {"空港": "RJSC", "名称": "山形空港", "距離 [NM]": 71.0},
        {"空港": "RJSY", "名称": "庄内空港", "距離 [NM]": 100.0},
        {"空港": "RJSI", "名称": "花巻空港", "距離 [NM]": 136.0},
        {"空港": "RJSK", "名称": "秋田空港", "距離 [NM]": 143.0},
        {"空港": "RJST", "名称": "松島基地", "距離 [NM]": 80.0},
        {"空港": "RJTU", "名称": "宇都宮飛行場", "距離 [NM]": 52.0},
        {"空港": "RJAH", "名称": "百里基地", "距離 [NM]": 63.0},
    ]
    dvt_df = pd.DataFrame(divert)
    dvt_df["空港"] = dvt_df.apply(lambda r: f"{r['空港']} {r['名称']}", axis=1)

    def _fmt_hm_from_minutes(total_minutes: float) -> str:
        mins = int(max(0.0, float(total_minutes)))
        h = mins // 60
        m = mins % 60
        return f"{h}時間{m}分"

    # DVT時の到着重量は「福島帰投時（LDG Weight（帰投時））」から消費分を差し引く
    ldg_w_at_fukushima = float(ldg2_row.get("weight", 0.0) or 0.0)

    def _ok_with_time(dist_nm: float, gs_kt: float, max_nm: float) -> str:
        if dist_nm <= max_nm:
            minutes = (dist_nm / gs_kt) * 60.0 if gs_kt > 0 else 0.0
            fuel_used_gal = max(0.0, (minutes / 60.0) * 10.0)
            fuel_used_kg = fuel_used_gal * fuel_kg_per_usg
            ldg_w = max(0.0, ldg_w_at_fukushima - fuel_used_kg)
            return f"OK（{_fmt_hm_from_minutes(minutes)} / {fuel_used_gal:.1f}gal / LDG W {ldg_w:.1f}kg）"
        return "NG"

    dvt_df["GS120kt"] = dvt_df["距離 [NM]"].apply(lambda d: _ok_with_time(float(d), 120.0, max_nm_120))
    dvt_df["GS140kt"] = dvt_df["距離 [NM]"].apply(lambda d: _ok_with_time(float(d), 140.0, max_nm_140))
    dvt_df["距離"] = dvt_df["距離 [NM]"].apply(lambda d: f"{float(d):.1f}NM")
    dvt_df = dvt_df[["空港", "距離", "GS120kt", "GS140kt"]]

    def _okng_style(v: str) -> str:
        s = str(v)
        if s.startswith("OK"):
            return "background-color: #86efac; color: #14532d; font-weight: 700;"
        if s == "NG":
            return "background-color: #fca5a5; color: #991b1b; font-weight: 700;"
        return ""

    dvt_styled = (
        dvt_df.style.hide(axis="index")
        .set_properties(**{"text-align": "center"})
        .set_properties(subset=["GS120kt", "GS140kt"], **{"font-size": "0.92rem", "line-height": "1.45"})
        .set_table_styles([{"selector": "th", "props": _TABLE_TH_PROPS}])
        .map(_okng_style, subset=["GS120kt", "GS140kt"])
    )

    with st.expander("DVT候補（10.0 GAL/hr）", expanded=False):
        d1, d2 = st.columns(2)
        d1.metric("GS 120 kt 到達可能距離 [NM]", f"{max_nm_120:.1f}")
        d2.metric("GS 140 kt 到達可能距離 [NM]", f"{max_nm_140:.1f}")
        st.caption("RJSFからの各距離・無風状態")
        st.table(dvt_styled)

    st.divider()
    st.subheader("CGエンベロープ")

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

        # 指定の参考線（常に表示）
        # - JA56DA: 1999kg
        # - JA52/53DA: 1785kg / 1700kg
        # - それ以外: limits の MTOW/MLW を表示（入力がある場合）
        if tail == "JA56DA":
            ref_lines = [(1999.0, "MTOW/MLW 1999kg")]
        elif tail in {"JA52DA", "JA53DA"}:
            ref_lines = [(1785.0, "MTOW 1785kg"), (1700.0, "MLW 1700kg")]
        else:
            ref_lines = []
            if mtow and mtow > 0:
                ref_lines.append((float(mtow), f"MTOW {float(mtow):.0f}kg"))
            if mlw and mlw > 0:
                ref_lines.append((float(mlw), f"MLW {float(mlw):.0f}kg"))

        ref_color = "#3b82f6"  # blue
        for y, title in ref_lines:
            shapes.append(
                dict(
                    type="line",
                    xref="paper",
                    x0=0,
                    x1=1,
                    y0=y,
                    y1=y,
                    line=dict(color=ref_color, width=2, dash="solid"),
                )
            )
            ann.append(
                dict(
                    xref="paper",
                    x=0.02,
                    y=y,
                    text=title,
                    showarrow=False,
                    font=dict(color=ref_color, size=16),
                    yanchor="bottom",
                )
            )

        # 全機体共通: X=2.30 / 2.50 の補助縦線
        for x in (2.30, 2.50):
            shapes.append(
                dict(
                    type="line",
                    xref="x",
                    yref="paper",
                    x0=x,
                    x1=x,
                    y0=0,
                    y1=1,
                    line=dict(color="rgba(148,163,184,0.45)", width=2, dash="dot"),
                )
            )

        # 既定の参考線とタイトルが重複しやすいので、JA52/53/55/56 は limits 由来の線は出さない
        if tail not in {"JA52DA", "JA53DA", "JA55DA", "JA56DA"} and mlw and mlw > 0:
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
                    font=dict(color="#ef4444", size=16),
                    yanchor="bottom",
                )
            )
        if tail not in {"JA52DA", "JA53DA", "JA55DA", "JA56DA"} and mtow and mtow > 0:
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
                    font=dict(color="#ef4444", size=14),
                    yanchor="bottom",
                )
            )

        # 目盛ラベルは残しつつ、上下の余白をできるだけ削る
        _m_l, _m_r, _m_t, _m_b = 60, 20, 12, 28
        fig.update_layout(
            template="plotly_dark",
            xaxis_title="CG [m]",
            yaxis_title=f"Weight [{unit_weight}]",
            height=520,
            width=1020,
            margin=dict(l=_m_l, r=_m_r, t=_m_t, b=_m_b),
            showlegend=False,
            paper_bgcolor="#0b1220",
            plot_bgcolor="#0b1220",
            font=dict(size=14, color="#e2e8f0"),
            shapes=shapes,
            annotations=ann,
        )
        fig.update_xaxes(
            showgrid=True,
            gridcolor="rgba(148,163,184,0.35)",
            zeroline=False,
            tickformat=".2f",
            tickmode="array",
            tickvals=[2.30, 2.35, 2.40, 2.45, 2.50],
            ticktext=["<b>2.30</b>", "<b>2.35</b>", "<b>2.40</b>", "<b>2.45</b>", "<b>2.50</b>"],
            minor=dict(
                dtick=0.01,
                showgrid=True,
                gridcolor="rgba(148,163,184,0.22)",
            ),
        )
        fig.update_xaxes(range=[2.30, 2.50])

        # Y=2000kg まで 50kg 刻みの補助線・目盛
        y_min = 1400 if tail in {"JA55DA", "JA56DA"} else 1250
        y_max = 1850 if tail in {"JA52DA", "JA53DA"} else 2000
        y_vals = list(range(y_min, y_max + 1, 50))

        # 上端/下端の横線（表示範囲の枠線）
        border_color = "rgba(148,163,184,0.45)"
        for y in (y_min, y_max):
            fig.add_shape(
                type="line",
                xref="paper",
                yref="y",
                x0=0,
                x1=1,
                y0=y,
                y1=y,
                line=dict(color=border_color, width=2, dash="dot"),
            )
        fig.update_yaxes(
            showgrid=True,
            gridcolor="rgba(148,163,184,0.25)",
            zeroline=False,
            dtick=50,
            tickmode="array",
            tickvals=y_vals,
            ticktext=[f"<b>{v}</b>" for v in y_vals],
            range=[y_min, y_max],
        )

        # 1マスの辺を揃える（X:0.01 == Y:50）
        # scaleanchor/scaleratio で軸スケールを連動させる
        _scaleratio = 0.01 / 50.0
        fig.update_yaxes(scaleanchor="x", scaleratio=_scaleratio, constrain="domain")
        fig.update_xaxes(constrain="domain")

        # スケール連動を優先しつつ、y_min/y_max がプロット上下端に来るように
        # 「内側プロット領域」の高さを計算して figure の高さを決める。
        # (inner_h / inner_w) = (y_range * scaleratio) / x_range
        _x_range = 2.50 - 2.30
        _y_range = float(y_max) - float(y_min)
        _fig_w = 1020.0
        _inner_w = max(1.0, _fig_w - _m_l - _m_r)
        _inner_h = _inner_w * (_y_range * _scaleratio) / _x_range
        _fig_h = max(420.0, _inner_h + _m_t + _m_b)
        fig.update_layout(height=int(_fig_h), width=int(_fig_w))
        st.plotly_chart(fig, use_container_width=False)

        # --- PDF ---
        st.subheader("PDF")
        if build_direct_pdf is None:
            st.info("PDF出力を使うには `reportlab` が必要です（requirements を更新済み）。")
        else:
            def _mm_to_m(v_mm: float) -> float:
                return float(v_mm) / 1000.0

            arm_basic_empty_m = _mm_to_m(bew_a)
            arm_front_m = _mm_to_m(front_arm)
            arm_rear_m = _mm_to_m(rear_arm)
            arm_nose_m = _mm_to_m(nose_arm)
            arm_cockpit_m = _mm_to_m(cockpit_arm)
            arm_bagext_m = _mm_to_m(bag_ext_arm)
            arm_deice_m = _mm_to_m(deice_arm)
            arm_fuel_m = _mm_to_m(fuel_arm)

            w_basic = float(bew_w)
            w_front = float(front_w)
            w_rear = float(rear_w)
            w_nose = float(nose_bag)
            w_cockpit = float(cockpit_bag)
            w_bagext = float(bag_ext)
            w_deice = float(deice_kg)
            w_mainfuel = float(main_fuel_kg)
            w_taxi = float(taxi_burn_kg)
            w_burn_out = float(flight_burn_kg)
            w_burn_back = float(return_burn_kg)

            _m_basic = float(bew_moment_kgm) if isinstance(bew_moment_kgm, (int, float)) else (w_basic * arm_basic_empty_m)
            _m_front = w_front * arm_front_m
            _m_rear = w_rear * arm_rear_m
            _m_nose = w_nose * arm_nose_m
            _m_cockpit = w_cockpit * arm_cockpit_m
            _m_bagext = w_bagext * arm_bagext_m
            _m_deice = w_deice * arm_deice_m

            def _totals(*, fuel_remaining_kg: float) -> tuple[float, float, float]:
                w = w_basic + w_front + w_rear + w_nose + w_cockpit + w_bagext + w_deice + float(fuel_remaining_kg)
                m = _m_basic + _m_front + _m_rear + _m_nose + _m_cockpit + _m_bagext + _m_deice + (float(fuel_remaining_kg) * arm_fuel_m)
                a = (m / w) if w > 0 else 0.0
                return w, m, a

            fuel_to_kg = w_mainfuel
            fuel_tow_rem = max(fuel_to_kg - w_taxi, 0.0)
            fuel_lw1_rem = max(fuel_tow_rem - w_burn_out, 0.0)
            fuel_lw2_rem = max(fuel_lw1_rem - w_burn_back, 0.0)

            w_zfm, m_zfm, a_zfm = _totals(fuel_remaining_kg=0.0)
            w_tow, m_tow, a_tow = _totals(fuel_remaining_kg=fuel_tow_rem)
            w_lw1, m_lw1, a_lw1 = _totals(fuel_remaining_kg=fuel_lw1_rem)
            w_lw2, m_lw2, a_lw2 = _totals(fuel_remaining_kg=fuel_lw2_rem)

            export_values: dict[str, float | str] = {
                "tail": tail,
                "arm_basic_empty": arm_basic_empty_m,
                "arm_front_seats": arm_front_m,
                "arm_rear_seats": arm_rear_m,
                "arm_nose_baggage": arm_nose_m,
                "arm_cockpit_baggage": arm_cockpit_m,
                "arm_baggage_extension": arm_bagext_m,
                "arm_deice_fluid": arm_deice_m,
                "arm_zfm": a_zfm,
                "arm_main_fuel": arm_fuel_m,
                "arm_taxi_run": arm_fuel_m,
                "arm_tow": a_tow,
                "arm_fuel_burn_out": arm_fuel_m,
                "arm_lw1": a_lw1,
                "arm_fuel_burn_back": arm_fuel_m,
                "arm_lw2": a_lw2,
                "w_basic_empty": w_basic,
                "w_front_seats": w_front,
                "w_rear_seats": w_rear,
                "w_nose_baggage": w_nose,
                "w_cockpit_baggage": w_cockpit,
                "w_baggage_extension": w_bagext,
                "w_deice_fluid": w_deice,
                "w_zfm": w_zfm,
                "w_main_fuel": w_mainfuel,
                "w_taxi_run": w_taxi,
                "w_tow": w_tow,
                "w_fuel_burn_out": w_burn_out,
                "w_lw1": w_lw1,
                "w_fuel_burn_back": w_burn_back,
                "w_lw2": w_lw2,
                "m_basic_empty": _m_basic,
                "m_front_seats": w_front * arm_front_m,
                "m_rear_seats": w_rear * arm_rear_m,
                "m_nose_baggage": w_nose * arm_nose_m,
                "m_cockpit_baggage": w_cockpit * arm_cockpit_m,
                "m_baggage_extension": w_bagext * arm_bagext_m,
                "m_deice_fluid": w_deice * arm_deice_m,
                "m_zfm": m_zfm,
                "m_main_fuel": w_mainfuel * arm_fuel_m,
                "m_taxi_run": w_taxi * arm_fuel_m,
                "m_tow": m_tow,
                "m_fuel_burn_out": w_burn_out * arm_fuel_m,
                "m_lw1": m_lw1,
                "m_fuel_burn_back": w_burn_back * arm_fuel_m,
                "m_lw2": m_lw2,
            }

            def _as_disp(v) -> str:
                try:
                    fv = float(v)
                except Exception:
                    return str(v)
                s = f"{fv:.5f}".rstrip("0").rstrip(".")
                return s

            export_values = {k: (v if isinstance(v, str) else _as_disp(v)) for k, v in export_values.items()}

            export_images: dict[str, bytes] = {}
            try:
                fig_pdf = copy.deepcopy(fig)
                _pdf_grid_major = "rgba(0,0,0,0.30)"
                _pdf_grid_minor = "rgba(0,0,0,0.20)"
                fig_pdf.update_layout(
                    template="plotly_white",
                    paper_bgcolor="white",
                    plot_bgcolor="white",
                    font=dict(color="#111111"),
                )
                fig_pdf.update_xaxes(
                    gridcolor=_pdf_grid_major,
                    zeroline=False,
                    tickfont=dict(color="#111111"),
                    titlefont=dict(color="#111111"),
                    minor=dict(
                        dtick=0.01,
                        showgrid=True,
                        gridcolor=_pdf_grid_minor,
                    ),
                )
                fig_pdf.update_yaxes(
                    gridcolor=_pdf_grid_major,
                    zeroline=False,
                    tickfont=dict(color="#111111"),
                    titlefont=dict(color="#111111"),
                )
                for tr in fig_pdf.data:
                    try:
                        if hasattr(tr, "line") and tr.line is not None:
                            tr.line.color = "#111111"
                        if hasattr(tr, "marker") and tr.marker is not None:
                            tr.marker.color = "#111111"
                            if getattr(tr.marker, "line", None) is not None:
                                tr.marker.line.color = "#111111"
                        if hasattr(tr, "fillcolor") and tr.fillcolor:
                            tr.fillcolor = "rgba(0,0,0,0)"
                    except Exception:
                        pass
                try:
                    for sh in (fig_pdf.layout.shapes or []):
                        if getattr(sh, "line", None) is not None:
                            sh.line.color = "#111111"
                            # 図の枠線（縦: x軸固定 / 横: 上下端）だけ破線→実線
                            xref = getattr(sh, "xref", None)
                            yref = getattr(sh, "yref", None)
                            y0 = getattr(sh, "y0", None)
                            is_vertical_frame = xref == "x" and yref == "paper"
                            is_horizontal_frame = (
                                xref == "paper"
                                and yref == "y"
                                and y0 in (y_min, y_max)
                            )
                            if is_vertical_frame or is_horizontal_frame:
                                sh.line.dash = "solid"
                    for an in (fig_pdf.layout.annotations or []):
                        if getattr(an, "font", None) is not None:
                            an.font.color = "#111111"
                except Exception:
                    pass
                export_images["cg_envelope_png"] = pio.to_image(
                    fig_pdf,
                    format="png",
                    width=800,
                    height=525,
                    scale=2,
                )
            except Exception as e:
                st.warning(f"CGエンベロープ画像の生成に失敗しました: {e}")

            direct_rows = [
                ("Empty mass Actual", export_values.get("arm_basic_empty", ""), export_values.get("w_basic_empty", ""), export_values.get("m_basic_empty", "")),
                ("Front seats", export_values.get("arm_front_seats", ""), export_values.get("w_front_seats", ""), export_values.get("m_front_seats", "")),
                ("Rear seats", export_values.get("arm_rear_seats", ""), export_values.get("w_rear_seats", ""), export_values.get("m_rear_seats", "")),
                ("Nose baggage", export_values.get("arm_nose_baggage", ""), export_values.get("w_nose_baggage", ""), export_values.get("m_nose_baggage", "")),
                ("Cockpit baggage", export_values.get("arm_cockpit_baggage", ""), export_values.get("w_cockpit_baggage", ""), export_values.get("m_cockpit_baggage", "")),
                ("Baggage extention", export_values.get("arm_baggage_extension", ""), export_values.get("w_baggage_extension", ""), export_values.get("m_baggage_extension", "")),
                ("De-ICE Fluid", export_values.get("arm_deice_fluid", ""), export_values.get("w_deice_fluid", ""), export_values.get("m_deice_fluid", "")),
                ("ZERO FUEL MASS", export_values.get("arm_zfm", ""), export_values.get("w_zfm", ""), export_values.get("m_zfm", "")),
                ("Main FUEL", export_values.get("arm_main_fuel", ""), export_values.get("w_main_fuel", ""), export_values.get("m_main_fuel", "")),
                ("TAXI-RUN", export_values.get("arm_taxi_run", ""), export_values.get("w_taxi_run", ""), export_values.get("m_taxi_run", "")),
                ("TKOF Weight", export_values.get("arm_tow", ""), export_values.get("w_tow", ""), export_values.get("m_tow", "")),
                ("Fuel consumption", export_values.get("arm_fuel_burn_out", ""), export_values.get("w_fuel_burn_out", ""), export_values.get("m_fuel_burn_out", "")),
                ("LDG weight", export_values.get("arm_lw1", ""), export_values.get("w_lw1", ""), export_values.get("m_lw1", "")),
                ("Fuel consumption", export_values.get("arm_fuel_burn_back", ""), export_values.get("w_fuel_burn_back", ""), export_values.get("m_fuel_burn_back", "")),
                ("LDG weight", export_values.get("arm_lw2", ""), export_values.get("w_lw2", ""), export_values.get("m_lw2", "")),
            ]

            if st.button("PDFを作成"):
                try:
                    _page2 = {
                        "remain_gal": f"{remain_gal:.1f}",
                        "endurance_10": endurance_10,
                        "endurance_166": endurance_166,
                        "max_nm_120": f"{max_nm_120:.1f}",
                        "max_nm_140": f"{max_nm_140:.1f}",
                        "dvt_rows": [
                            (str(r["空港"]), str(r["距離"]), str(r["GS120kt"]), str(r["GS140kt"]))
                            for _, r in dvt_df.iterrows()
                        ],
                    }
                    pdf = build_direct_pdf(
                        tail=tail,
                        rows=[(a, b, c, d) for (a, b, c, d) in direct_rows],
                        envelope_png=export_images.get("cg_envelope_png"),
                        page2=_page2,
                    )
                    st.download_button(
                        "PDFをダウンロード",
                        data=pdf,
                        file_name=f"{tail}_WB.pdf",
                        mime="application/pdf",
                    )
                except Exception as e:
                    st.error(str(e))

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
