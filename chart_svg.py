"""Gerador de gráficos SVG inline para previsões de demanda.

Produz SVG puro (sem dependências externas) que pode ser embutido
diretamente em HTML — compatível com ng-bind-html e templates AngularJS.
"""

from typing import List, Dict, Optional
from datetime import datetime

MONTH_ABBR_PT = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"
}


def _parse_date(ds: str) -> datetime:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(ds, fmt)
        except ValueError:
            continue
    return datetime.strptime(ds[:10], "%Y-%m-%d")


def _format_date_label(ds: str) -> str:
    dt = _parse_date(ds)
    return f"{MONTH_ABBR_PT.get(dt.month, dt.strftime('%b'))}/{str(dt.year)[2:]}"


def _nice_ticks(min_val: float, max_val: float, n_ticks: int = 5) -> List[float]:
    """Gera valores de eixo Y espaçados de forma legível."""
    if max_val <= min_val:
        max_val = min_val + 10
    raw_step = (max_val - min_val) / max(n_ticks - 1, 1)

    magnitude = 1
    while magnitude * 10 <= raw_step:
        magnitude *= 10
    nice_steps = [1, 2, 2.5, 5, 10]
    step = nice_steps[0] * magnitude
    for s in nice_steps:
        candidate = s * magnitude
        if candidate >= raw_step:
            step = candidate
            break

    start = (int(min_val / step)) * step
    if start > min_val:
        start -= step
    ticks = []
    v = start
    while v <= max_val + step * 0.5:
        ticks.append(round(v, 2))
        v += step
    return ticks


def _format_number(val: float) -> str:
    if abs(val) >= 1000:
        return f"{val:,.0f}".replace(",", ".")
    if abs(val) >= 10:
        return f"{val:.0f}"
    return f"{val:.1f}"


def generate_forecast_chart_svg(
    chart_data: Dict,
    width: int = 600,
    height: int = 280,
    highlight_ds: Optional[str] = None
) -> str:
    """Gera SVG inline com gráfico de linha: histórico + previsão + IC.

    Args:
        chart_data: {"historical": [{ds, y}], "forecast": [{ds, yhat, yhat_lower, yhat_upper}]}
        width: Largura do viewBox
        height: Altura do viewBox
        highlight_ds: Data a destacar (período atual)

    Returns:
        String SVG completa para embutir em HTML.
    """
    historical = chart_data.get("historical", [])
    forecast = chart_data.get("forecast", [])

    if not historical and not forecast:
        return ""

    margin = {"top": 28, "right": 20, "bottom": 40, "left": 55}
    plot_w = width - margin["left"] - margin["right"]
    plot_h = height - margin["top"] - margin["bottom"]

    all_points = []
    for h in historical:
        all_points.append({"ds": h["ds"], "val": h["y"], "type": "hist"})
    for f in forecast:
        all_points.append({
            "ds": f["ds"], "val": f["yhat"],
            "lower": f.get("yhat_lower", f["yhat"]),
            "upper": f.get("yhat_upper", f["yhat"]),
            "type": "fc"
        })

    if not all_points:
        return ""

    n = len(all_points)
    all_vals = [p["val"] for p in all_points]
    for p in all_points:
        if "lower" in p:
            all_vals.append(p["lower"])
        if "upper" in p:
            all_vals.append(p["upper"])

    y_min_raw = min(all_vals) * 0.92
    y_max_raw = max(all_vals) * 1.08
    if y_min_raw < 0:
        y_min_raw = 0

    ticks = _nice_ticks(y_min_raw, y_max_raw)
    y_min = ticks[0]
    y_max = ticks[-1]

    def x_pos(i: int) -> float:
        return margin["left"] + (i / max(n - 1, 1)) * plot_w

    def y_pos(v: float) -> float:
        if y_max == y_min:
            return margin["top"] + plot_h / 2
        return margin["top"] + (1 - (v - y_min) / (y_max - y_min)) * plot_h

    parts: List[str] = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'style="width:100%;font-family:Arial,sans-serif;font-size:10px;">'
    )

    parts.append(f'<rect x="{margin["left"]}" y="{margin["top"]}" '
                 f'width="{plot_w}" height="{plot_h}" fill="#fafafa" rx="3"/>')

    for tick in ticks:
        ty = y_pos(tick)
        parts.append(f'<line x1="{margin["left"]}" y1="{ty:.1f}" '
                     f'x2="{margin["left"] + plot_w}" y2="{ty:.1f}" '
                     f'stroke="#e0e0e0" stroke-width="0.5"/>')
        parts.append(f'<text x="{margin["left"] - 6}" y="{ty + 3:.1f}" '
                     f'text-anchor="end" fill="#666" font-size="9">'
                     f'{_format_number(tick)}</text>')

    step = max(1, n // 8)
    for i in range(0, n, step):
        lx = x_pos(i)
        label = _format_date_label(all_points[i]["ds"])
        parts.append(f'<text x="{lx:.1f}" y="{margin["top"] + plot_h + 16}" '
                     f'text-anchor="middle" fill="#666" font-size="9">{label}</text>')
    if n > 1 and (n - 1) % step != 0:
        lx = x_pos(n - 1)
        label = _format_date_label(all_points[-1]["ds"])
        parts.append(f'<text x="{lx:.1f}" y="{margin["top"] + plot_h + 16}" '
                     f'text-anchor="middle" fill="#666" font-size="9">{label}</text>')

    split_idx = len(historical)
    if split_idx > 0 and split_idx < n:
        sx = (x_pos(split_idx - 1) + x_pos(split_idx)) / 2
        parts.append(f'<line x1="{sx:.1f}" y1="{margin["top"]}" '
                     f'x2="{sx:.1f}" y2="{margin["top"] + plot_h}" '
                     f'stroke="#bdbdbd" stroke-width="1" stroke-dasharray="4,3"/>')

    fc_points = [(i, p) for i, p in enumerate(all_points) if p["type"] == "fc"]
    if fc_points:
        poly_pts = []
        for i, p in fc_points:
            poly_pts.append(f"{x_pos(i):.1f},{y_pos(p['upper']):.1f}")
        for i, p in reversed(fc_points):
            poly_pts.append(f"{x_pos(i):.1f},{y_pos(p['lower']):.1f}")
        parts.append(f'<polygon points="{" ".join(poly_pts)}" '
                     f'fill="rgba(255,152,0,0.13)" stroke="none"/>')

    hist_pts = [(i, p) for i, p in enumerate(all_points) if p["type"] == "hist"]
    if len(hist_pts) > 1:
        line_d = " ".join(f"{'M' if j == 0 else 'L'}{x_pos(i):.1f},{y_pos(p['val']):.1f}"
                          for j, (i, p) in enumerate(hist_pts))
        parts.append(f'<path d="{line_d}" fill="none" stroke="#1976D2" stroke-width="2"/>')

    if fc_points:
        if hist_pts:
            last_hist_i, last_hist_p = hist_pts[-1]
            bridge = f"M{x_pos(last_hist_i):.1f},{y_pos(last_hist_p['val']):.1f} "
            bridge += f"L{x_pos(fc_points[0][0]):.1f},{y_pos(fc_points[0][1]['val']):.1f}"
            parts.append(f'<path d="{bridge}" fill="none" stroke="#FF9800" '
                         f'stroke-width="1.5" stroke-dasharray="4,3"/>')

        if len(fc_points) > 1:
            fc_d = " ".join(f"{'M' if j == 0 else 'L'}{x_pos(i):.1f},{y_pos(p['val']):.1f}"
                            for j, (i, p) in enumerate(fc_points))
            parts.append(f'<path d="{fc_d}" fill="none" stroke="#FF9800" '
                         f'stroke-width="2" stroke-dasharray="5,3"/>')

    for idx, (i, p) in enumerate(hist_pts):
        cx, cy = x_pos(i), y_pos(p["val"])
        parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="3" fill="#1976D2"/>')
        label_y = cy - 8 if idx % 2 == 0 else cy + 14
        parts.append(f'<text x="{cx:.1f}" y="{label_y:.1f}" text-anchor="middle" '
                     f'fill="#1565C0" font-size="8" font-weight="bold">'
                     f'{_format_number(p["val"])}</text>')

    for idx, (i, p) in enumerate(fc_points):
        cx, cy = x_pos(i), y_pos(p["val"])
        is_highlight = highlight_ds and p["ds"].startswith(highlight_ds[:10])
        r = "5" if is_highlight else "3"
        stroke = ' stroke="#E65100" stroke-width="2"' if is_highlight else ""
        parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="#FF9800"{stroke}/>')
        label_y = cy - 8 if idx % 2 == 0 else cy + 14
        parts.append(f'<text x="{cx:.1f}" y="{label_y:.1f}" text-anchor="middle" '
                     f'fill="#E65100" font-size="8" font-weight="bold">'
                     f'{_format_number(p["val"])}</text>')

    legend_y = height - 6
    lx = margin["left"]
    parts.append(f'<line x1="{lx}" y1="{legend_y}" x2="{lx + 16}" y2="{legend_y}" '
                 f'stroke="#1976D2" stroke-width="2"/>')
    parts.append(f'<text x="{lx + 20}" y="{legend_y + 3}" fill="#333" font-size="9">'
                 f'Histórico</text>')
    lx2 = lx + 80
    parts.append(f'<line x1="{lx2}" y1="{legend_y}" x2="{lx2 + 16}" y2="{legend_y}" '
                 f'stroke="#FF9800" stroke-width="2" stroke-dasharray="4,3"/>')
    parts.append(f'<text x="{lx2 + 20}" y="{legend_y + 3}" fill="#333" font-size="9">'
                 f'Previsão</text>')
    lx3 = lx2 + 80
    parts.append(f'<rect x="{lx3}" y="{legend_y - 5}" width="12" height="10" '
                 f'fill="rgba(255,152,0,0.20)" rx="2"/>')
    parts.append(f'<text x="{lx3 + 16}" y="{legend_y + 3}" fill="#333" font-size="9">'
                 f'Intervalo de Confiança</text>')

    parts.append("</svg>")
    return "\n".join(parts)
