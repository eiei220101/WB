from __future__ import annotations

import io
from typing import Iterable

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle


def _ensure_jp_font() -> str:
    """
    ReportLab標準のCIDフォント（埋め込み不要）で日本語を描画する。
    """
    name = "HeiseiKakuGo-W5"
    try:
        pdfmetrics.getFont(name)
    except Exception:
        pdfmetrics.registerFont(UnicodeCIDFont(name))
    return name


def _pick_font(text: str) -> str:
    # ASCII以外が含まれる場合は日本語フォントへ
    try:
        text.encode("ascii")
        return "Helvetica"
    except Exception:
        return _ensure_jp_font()


def _is_wb_summary_row(item: str) -> bool:
    """ZFM / T/O / LDG の合計行を判定（表記ゆれに対応）。"""
    key = str(item).strip().upper()
    if key in {"ZERO FUEL MASS", "ZERO FUEL WEIGHT", "TKOF WEIGHT"}:
        return True
    return key.startswith("LDG WEIGHT") or key == "LDG WEIGHT"


def build_direct_pdf(
    *,
    tail: str,
    rows: Iterable[tuple[str, str, str, str]],
    envelope_png: bytes | None,
    page2: dict | None = None,
) -> bytes:
    """
    LibreOffice不要の簡易PDF。
    rows: (item, arm_m, mass_kg, moment_kgm) すべて「表示文字列」を渡す
    """
    buf = io.BytesIO()
    page_w, page_h = landscape(A4)
    c = canvas.Canvas(buf, pagesize=(page_w, page_h))

    jp = _ensure_jp_font()
    styles = getSampleStyleSheet()
    s_title = ParagraphStyle("t", parent=styles["Normal"], fontName=jp, fontSize=12, leading=14)
    s_jp = ParagraphStyle("jp", parent=styles["Normal"], fontName=jp, fontSize=9, leading=12)
    s_en = ParagraphStyle("en", parent=styles["Normal"], fontName="Helvetica", fontSize=9, leading=12)

    # --- Layout constants (領域固定して干渉を防ぐ) ---
    m_l, m_r, m_t, m_b = 10 * mm, 10 * mm, 8 * mm, 8 * mm
    gap = 6 * mm
    left_w = 125 * mm
    x_left = m_l
    x_right = x_left + left_w + gap
    right_w = page_w - m_r - x_right
    y_top = page_h - m_t
    y_bottom = m_b

    # --- Header (left/top) ---
    header_tbl = Table(
        [
            [Paragraph("WB・離着陸距離・性能確認シート", s_title)],
            [
                Table(
                    [[Paragraph("ACFT TYPE", s_en), "DA42"], [Paragraph("IDENT", s_en), tail]],
                    colWidths=[22 * mm, 28 * mm],
                    rowHeights=[6 * mm, 6 * mm],
                    style=TableStyle(
                        [
                            # ラベル側/値側とも枠線を付ける + 行間の横線
                            ("BOX", (0, 0), (0, 1), 0.8, colors.black),
                            ("BOX", (1, 0), (1, 1), 0.8, colors.black),
                            ("LINEBELOW", (0, 0), (1, 0), 0.8, colors.black),
                            ("ALIGN", (1, 0), (1, 1), "CENTER"),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                            ("FONT", (1, 0), (1, 1), "Helvetica", 9),
                        ]
                    ),
                )
            ],
        ],
        colWidths=[left_w],
        style=TableStyle([("BOTTOMPADDING", (0, 0), (-1, -1), 2), ("TOPPADDING", (0, 0), (-1, -1), 1)]),
    )
    hw, hh = header_tbl.wrapOn(c, left_w, 50 * mm)
    header_tbl.drawOn(c, x_left, y_top - hh)

    # --- Main W&B table (left) ---
    _cream = colors.HexColor("#FFF8E7")
    _sky = colors.HexColor("#DBEAFE")
    main_data = [[Paragraph("Item", s_en), Paragraph("Level arm (m)", s_en), Paragraph("Mass (kg)", s_en), Paragraph("Moment (kgm)", s_en)]]
    for item, arm, mass, mom in rows:
        main_data.append([Paragraph(str(item), s_en), str(arm), str(mass), str(mom)])

    main_style: list[tuple] = [
        ("GRID", (0, 0), (-1, -1), 0.8, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), _cream),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
        ("FONT", (1, 1), (-1, -1), "Helvetica", 9),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]
    for row_idx, (item, *_rest) in enumerate(rows, start=1):
        if _is_wb_summary_row(item):
            main_style.append(("BACKGROUND", (0, row_idx), (-1, row_idx), _sky))
            main_style.append(("FONT", (0, row_idx), (-1, row_idx), "Helvetica-Bold", 9))

    main_tbl = Table(
        main_data,
        colWidths=[56 * mm, 22 * mm, 22 * mm, 25 * mm],
        style=TableStyle(main_style),
    )
    tw, th = main_tbl.wrapOn(c, left_w, page_h)
    # IDENT の下に2行ぶん余白を作る
    y_tbl_top = (y_top - hh) - 14 * mm
    c.setFont(jp, 9)
    c.drawString(x_left, y_tbl_top + 3 * mm, "1   W&B   許容重心位置")
    main_tbl.drawOn(c, x_left, y_tbl_top - th)

    # --- Notes block (left/bottom) ---
    notes_lines = [
        "※   FUEL 1 USgal = 3.785 ltrs = 3.028kg",
        "　　Main tank 2 × 25.0 USgal  (2 × 94.6 ltrs ) = 2 × 75.7kg = 151.4 kg",
        "　　Aux tank 2 × 13.2 USgal  (2 × 50.0ltrs ) = 2 × 40.0kg = 80 kg",
        "　　De - ice fluid 1ltrs = 1.1kg",
        "",
        "※    燃料消費量（片ENG）",
    ]
    s_notes = ParagraphStyle("notes", parent=s_jp, fontSize=7.5, leading=9)
    notes_tbl = Table(
        [[Paragraph(line if line else " ", s_notes)] for line in notes_lines],
        colWidths=[left_w],
        style=TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        ),
    )
    fuel_tbl = Table(
        [
            [Paragraph("パワー設定", s_jp), Paragraph("US gal", s_en), Paragraph("kg", s_en)],
            ["100%", "8.3", "25.1"],
            ["70%", "5.3", "15.9"],
            ["60%", "4.4", "13.3"],
            ["50%", "3.6", "10.9"],
        ],
        colWidths=[30 * mm, 16 * mm, 16 * mm],
        style=TableStyle([("BOX", (0, 0), (-1, -1), 0.8, colors.black), ("ALIGN", (1, 1), (-1, -1), "RIGHT"), ("FONT", (0, 0), (-1, 0), jp, 9), ("FONT", (0, 1), (-1, -1), "Helvetica", 9)]),
    )
    extra_lines = [
        "以下の液体は　Empty mass actual に含まれる。",
        "ブレーキ液、ハイドロ液、滑油、クーラント液、ギアBOX OIL",
        "使用不能燃料　　Main ( 2 x 3.8litrs = 2 × 1 Usgal )",
        "　　　　　      Aux ( 2 x 1.9litrs = 2 × 0.5 Usgal )",
    ]
    gap_notes = 3 * mm
    gap_cols = 3 * mm
    fuel_col_w = 62 * mm
    extra_col_w = max(20 * mm, left_w - fuel_col_w - gap_cols)
    extra_tbl = Table(
        [[Paragraph(l, s_notes)] for l in extra_lines],
        colWidths=[extra_col_w],
        style=TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.8, colors.black),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        ),
    )

    _, notes_h = notes_tbl.wrapOn(c, left_w, page_h)
    fw, fh = fuel_tbl.wrapOn(c, fuel_col_w, page_h)
    ew, eh = extra_tbl.wrapOn(c, extra_col_w, page_h)
    row_h = max(fh, eh)

    y_area_top = (y_tbl_top - th) - 6 * mm
    y_notes_top = y_area_top
    y_notes_bottom = y_notes_top - notes_h
    y_row_top = y_notes_bottom - gap_notes
    y_row_bottom = y_row_top - row_h

    min_bottom = y_bottom + 6 * mm
    if y_row_bottom < min_bottom:
        shift = min_bottom - y_row_bottom
        y_notes_top += shift
        y_notes_bottom += shift
        y_row_top += shift
        y_row_bottom += shift

    notes_tbl.drawOn(c, x_left, y_notes_bottom)
    fuel_tbl.drawOn(c, x_left, y_row_top - fh)
    extra_tbl.drawOn(c, x_left + fw + gap_cols, y_row_top - eh)

    # --- Right/top: envelope image (fixed box) ---
    # 右側は「左表の下端」と揃える：性能枠の上辺＝左表の下端
    y_main_bottom = y_tbl_top - th

    # エンベロープは「性能枠の上」に収まる範囲で最大化
    env_gap = 4 * mm
    # 上端（=エンベロープ上側、1850付近）が左表の上辺と揃うようにする
    env_box_top = y_tbl_top
    env_box_y0 = y_main_bottom + env_gap
    env_box_h = max(30 * mm, env_box_top - env_box_y0)
    env_right_edge = x_right + right_w
    env_left_edge = x_right  # 画像の実描画左端（後で更新）
    if envelope_png:
        try:
            ir = ImageReader(io.BytesIO(envelope_png))
            iw, ih = ir.getSize()
            # fit into right box with margins
            box_pad = 2 * mm
            bw = right_w - 2 * box_pad
            bh = env_box_h - 2 * box_pad
            scale = min(bw / iw, bh / ih) if iw and ih else 1.0
            dw = iw * scale
            dh = ih * scale
            dx = x_right + (right_w - dw) / 2
            # 上端揃え（余白は下側へ寄せる）
            dy = (env_box_y0 + env_box_h) - dh
            c.drawImage(ir, dx, dy, width=dw, height=dh, preserveAspectRatio=True, mask="auto")
            env_left_edge = dx  # エンベロープの左端（=2.30付近の縦線と揃える基準）
        except Exception:
            c.setFont(jp, 9)
            c.drawString(x_right, env_box_y0 + env_box_h - 12 * mm, "（CGエンベロープ画像の描画に失敗）")
    else:
        c.setFont(jp, 9)
        c.drawString(x_right, env_box_y0 + env_box_h - 12 * mm, "（CGエンベロープ画像なし）")

    # --- Right/bottom: performance box (fixed) ---
    # 性能枠：上辺を左表の下端に揃える
    perf_h = 78 * mm
    perf_top = y_main_bottom
    perf_y0 = perf_top - perf_h
    if perf_y0 < y_bottom + 2 * mm:
        perf_y0 = y_bottom + 2 * mm
        perf_top = perf_y0 + perf_h

    # 左辺を「エンベロープの左端（2.30縦線付近）」に揃える
    perf_x = env_left_edge
    perf_w = max(40 * mm, env_right_edge - perf_x)

    # シンプルな1列レイアウトに戻す（文字列のみ）
    s_perf = ParagraphStyle("perf", parent=s_jp, fontSize=10, leading=13)
    perf_tbl = Table(
        [
            [Paragraph("2  離着陸距離及び性能", s_perf)],
            [Paragraph("気温　____________ ℃　　　気圧高度　____________ ft　　　風　____________", s_perf)],
            [Paragraph("離陸距離　________________ m　　　グランドロール　________________ m", s_perf)],
            [Paragraph("着陸距離　________________ m　　　グランドロール　________________ m", s_perf)],
            [Paragraph("TWO ENG  CLIMB　________ ft/min　( ________ % )", s_perf)],
            [Paragraph("ONE ENG  CLIMB　________ ft/min　( ________ % )", s_perf)],
            [Paragraph("ONE ENG サービスシーリング　________ ft", s_perf)],
            [Paragraph("ACGO DIST　________________ m　　　ACSTOP DIST　________________ m", s_perf)],
        ],
        colWidths=[perf_w],
        style=TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.9, colors.black),
                ("FONT", (0, 0), (-1, -1), jp, 9),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        ),
    )
    perf_tbl.wrapOn(c, perf_w, perf_h)
    perf_tbl.drawOn(c, perf_x, perf_y0)

    c.showPage()

    # -------------------------
    # Page 2: Fuel (Fukushima) + DVT candidates
    # -------------------------
    if page2:
        c.setFont(jp, 12)
        c.drawString(m_l, y_top - 6 * mm, "福島帰投時燃料 / DVT候補")
        c.setFont("Helvetica", 9)
        c.drawString(m_l, y_top - 13 * mm, f"IDENT: {tail}")

        # Fuel box
        fuel_box_x = m_l
        fuel_box_w = page_w - m_l - m_r
        fuel_box_h = 32 * mm
        fuel_box_top = y_top - 18 * mm
        fuel_box_y = fuel_box_top - fuel_box_h

        # 見やすさ重視：3カラムのカード風
        s_h2 = ParagraphStyle("h2", parent=s_jp, fontSize=11, leading=13)
        s_big = ParagraphStyle("big", parent=s_jp, fontSize=12, leading=14)
        s_mid = ParagraphStyle("mid", parent=s_jp, fontSize=10, leading=13)

        card_w = (fuel_box_w - 2 * 4 * mm) / 3.0
        cards = Table(
            [
                [
                    Paragraph("残燃料 [US gal]", s_mid),
                    Paragraph("10.0 GAL/hr", s_mid),
                    Paragraph("16.6 GAL/hr", s_mid),
                ],
                [
                    Paragraph(f"<b>{page2.get('remain_gal','')}</b>", s_big),
                    Paragraph(f"<b>{page2.get('endurance_10','')}</b>", s_big),
                    Paragraph(f"<b>{page2.get('endurance_166','')}</b>", s_big),
                ],
                [
                    Paragraph(f"GS120 到達距離: <b>{page2.get('max_nm_120','')}</b> NM", s_mid),
                    Paragraph(f"GS140 到達距離: <b>{page2.get('max_nm_140','')}</b> NM", s_mid),
                    Paragraph("", s_mid),
                ],
            ],
            colWidths=[card_w, card_w, card_w],
            style=TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 0.9, colors.black),
                    ("GRID", (0, 0), (-1, -1), 0.6, colors.black),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 1), (-1, 1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("FONT", (0, 0), (-1, -1), jp, 9),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            ),
        )

        fuel_block = Table(
            [
                [Paragraph("福島帰投時燃料", s_h2)],
                [cards],
            ],
            colWidths=[fuel_box_w],
            style=TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 0.9, colors.black),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            ),
        )
        fuel_block.wrapOn(c, fuel_box_w, fuel_box_h)
        fuel_block.drawOn(c, fuel_box_x, fuel_box_y)

        # DVT table
        dvt_title_y = fuel_box_y - 8 * mm
        c.setFont(jp, 10)
        c.drawString(m_l, dvt_title_y, "DVT候補（10.0 GAL/hr / RJSFからの各距離・無風状態）")

        dvt_rows = page2.get("dvt_rows") or []
        dvt_data = [[Paragraph("空港", s_jp), Paragraph("距離", s_jp), Paragraph("GS120kt", s_jp), Paragraph("GS140kt", s_jp)]]
        for r in dvt_rows:
            dvt_data.append([Paragraph(str(r[0]), s_jp), str(r[1]), Paragraph(str(r[2]), s_jp), Paragraph(str(r[3]), s_jp)])

        # style OK/NG
        ts = [("GRID", (0, 0), (-1, -1), 0.6, colors.black), ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke)]
        for i in range(1, len(dvt_data)):
            for j in (2, 3):
                s = str(dvt_rows[i - 1][j] if i - 1 < len(dvt_rows) else "")
                if s.startswith("OK"):
                    ts.append(("BACKGROUND", (j, i), (j, i), colors.Color(0.73, 0.97, 0.82)))  # light green
                elif s == "NG":
                    ts.append(("BACKGROUND", (j, i), (j, i), colors.Color(1.0, 0.79, 0.79)))  # light red

        dvt_tbl = Table(
            dvt_data,
            colWidths=[70 * mm, 20 * mm, 70 * mm, 70 * mm],
            style=TableStyle(
                ts
                + [
                    ("FONT", (0, 0), (-1, -1), jp, 9),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 3),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ]
            ),
        )

        dvt_x = m_l
        dvt_y = dvt_title_y - 6 * mm
        dw2, dh2 = dvt_tbl.wrapOn(c, page_w - m_l - m_r, page_h)
        dvt_tbl.drawOn(c, dvt_x, dvt_y - dh2)

        c.showPage()

    c.save()
    return buf.getvalue()

