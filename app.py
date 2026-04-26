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
      .label {{ fill:#6b7280; font: 700 12px system-ui, -apple-system, Segoe UI, Roboto; letter-spacing: 0.06em; }}
      .valueBox {{ fill:#16a34a; stroke:#15803d; stroke-width:2; }}
      .value {{ fill:#ffffff; font: 900 22px system-ui, -apple-system, Segoe UI, Roboto; }}
      .small {{ fill:#ffffff; font: 700 12px system-ui, -apple-system, Segoe UI, Roboto; opacity:0.95; }}
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
      .seat {{ fill:#e5e7eb; stroke:#9ca3af; stroke-width:2; rx:12; }}
      .bag  {{ fill:#e5e7eb; stroke:#9ca3af; stroke-width:2; rx:12; }}
      .pill {{ fill:#16a34a; }}
      .pillText {{ fill:white; font: 700 22px system-ui, -apple-system, Segoe UI, Roboto; }}
      .label {{ fill:#111827; font: 600 14px system-ui, -apple-system, Segoe UI, Roboto; }}
      .small {{ fill:#374151; font: 500 12px system-ui, -apple-system, Segoe UI, Roboto; }}
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
        # 画面表示は「m」に統一（内部計算は従来通り mm ベースのまま）
        arm_scale = 0.001 if unit_arm.strip().lower() == "mm" else 1.0
        unit_arm_disp = "m" if arm_scale == 0.001 else unit_arm

        def disp_arm(x: float) -> float:
            return float(x) * arm_scale

        def undisp_arm(x: float) -> float:
            return float(x) / arm_scale if arm_scale != 0 else float(x)

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

    st.subheader("入力")
    st.caption("燃料は **US gal** で入力（1 US gal = 3.028 kg）。De-ice は **L** 入力（1 L = 1.1 kg）。")

    fuel_kg_per_usg = 3.028

    def _ss_num(key: str, default: float = 0.0) -> float:
        return float(st.session_state.get(key, default) or 0.0)

    c_mode, c_reset = st.columns([3, 1], vertical_alignment="bottom")
    with c_mode:
        input_mode = st.radio("入力方法", ["フォーム（おすすめ）", "表（一覧で編集）"], horizontal=True, key="input_mode")
    with c_reset:
        if st.button("入力をリセット"):
            for k in [
                "front_l",
                "front_r",
                "rear_l",
                "rear_r",
                "nose_bag",
                "cockpit_bag",
                "bag_ext",
                "deice_l",
                "main_fuel_gal",
                "taxi_burn_gal",
                "flight_burn_gal",
                "return_burn_gal",
            ]:
                st.session_state[k] = 0.0
            st.rerun()

    if input_mode == "表（一覧で編集）":
        input_rows = [
            {"key": "front_l", "カテゴリ": "座席", "項目": "Front seat L", "入力値": _ss_num("front_l"), "単位": unit_weight},
            {"key": "front_r", "カテゴリ": "座席", "項目": "Front seat R", "入力値": _ss_num("front_r"), "単位": unit_weight},
            {"key": "rear_l", "カテゴリ": "座席", "項目": "Rear seat L", "入力値": _ss_num("rear_l"), "単位": unit_weight},
            {"key": "rear_r", "カテゴリ": "座席", "項目": "Rear seat R", "入力値": _ss_num("rear_r"), "単位": unit_weight},
            {"key": "nose_bag", "カテゴリ": "バゲッジ", "項目": "Nose baggage", "入力値": _ss_num("nose_bag"), "単位": unit_weight},
            {"key": "cockpit_bag", "カテゴリ": "バゲッジ", "項目": "Cockpit baggage", "入力値": _ss_num("cockpit_bag"), "単位": unit_weight},
            {"key": "bag_ext", "カテゴリ": "バゲッジ", "項目": "Baggage extension", "入力値": _ss_num("bag_ext"), "単位": unit_weight},
            {"key": "deice_l", "カテゴリ": "液体", "項目": "De-ice fluid", "入力値": _ss_num("deice_l"), "単位": "L"},
            {"key": "main_fuel_gal", "カテゴリ": "燃料", "項目": "Main fuel (loaded)", "入力値": _ss_num("main_fuel_gal"), "単位": "US gal"},
            {"key": "taxi_burn_gal", "カテゴリ": "燃料", "項目": "Taxi burn", "入力値": _ss_num("taxi_burn_gal"), "単位": "US gal"},
            {"key": "flight_burn_gal", "カテゴリ": "燃料", "項目": "Flight burn", "入力値": _ss_num("flight_burn_gal"), "単位": "US gal"},
            {"key": "return_burn_gal", "カテゴリ": "燃料", "項目": "Return burn", "入力値": _ss_num("return_burn_gal"), "単位": "US gal"},
        ]

        in_df = pd.DataFrame(input_rows)
        edited = st.data_editor(
            in_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "key": st.column_config.TextColumn("key", disabled=True),
                "カテゴリ": st.column_config.TextColumn("カテゴリ", disabled=True),
                "項目": st.column_config.TextColumn("項目", disabled=True),
                "入力値": st.column_config.NumberColumn("入力値", min_value=0.0, step=1.0),
                "単位": st.column_config.TextColumn("単位", disabled=True),
            },
            key="input_table",
        )

        for _, r in edited.iterrows():
            try:
                st.session_state[str(r["key"])] = max(0.0, float(r["入力値"] or 0.0))
            except Exception:
                st.session_state[str(r["key"])] = 0.0

    else:
        col1, col2 = st.columns(2, vertical_alignment="top")
        with col1:
            st.markdown("**座席**")
            st.number_input("Front seat L", min_value=0.0, step=1.0, format="%.1f", key="front_l")
            st.number_input("Front seat R", min_value=0.0, step=1.0, format="%.1f", key="front_r")
            st.number_input("Rear seat L", min_value=0.0, step=1.0, format="%.1f", key="rear_l")
            st.number_input("Rear seat R", min_value=0.0, step=1.0, format="%.1f", key="rear_r")

            st.markdown("**バゲッジ**")
            st.number_input("Nose baggage", min_value=0.0, step=1.0, format="%.1f", key="nose_bag")
            st.number_input("Cockpit baggage", min_value=0.0, step=1.0, format="%.1f", key="cockpit_bag")
            st.number_input("Baggage extension", min_value=0.0, step=1.0, format="%.1f", key="bag_ext")

        with col2:
            st.markdown("**De-ice / 液体**")
            st.number_input("De-ice fluid [L]", min_value=0.0, step=1.0, format="%.1f", key="deice_l")
            st.caption(f"換算: {_ss_num('deice_l'):.1f} L → {_ss_num('deice_l') * 1.1:.1f} {unit_weight}")

            st.markdown("**燃料（US gal）**")
            st.number_input("Main fuel loaded [US gal]", min_value=0.0, step=1.0, format="%.1f", key="main_fuel_gal")
            st.number_input("Taxi burn [US gal]", min_value=0.0, step=0.5, format="%.1f", key="taxi_burn_gal")
            st.number_input("Flight burn [US gal]", min_value=0.0, step=0.5, format="%.1f", key="flight_burn_gal")
            st.number_input("Return burn [US gal]", min_value=0.0, step=0.5, format="%.1f", key="return_burn_gal")

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

    load_components = {
        "Basic Empty": (bew_w, bew_a),
        "FrontSeat": (front_l + front_r, _combined_arm(front_l, front_a_l, front_r, front_a_r)),
        "RearSeat": (rear_l + rear_r, _combined_arm(rear_l, rear_a_l, rear_r, rear_a_r)),
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

    st.subheader("内訳一覧")
    out = pd.DataFrame(
        [
            {
                "項目": r.name,
                f"アーム [{unit_arm_disp}]": disp_arm(r.arm),
                f"重量 [{unit_weight}]": r.weight,
                f"モーメント [{unit_weight}·{unit_arm_disp}]": r.moment * arm_scale,
            }
            for r in results
        ]
    )
    st.dataframe(out, use_container_width=True, hide_index=True)

    st.divider()
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
