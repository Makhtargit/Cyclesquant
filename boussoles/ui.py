"""Composants visuels (HTML/SVG) du tableau de bord."""
import numpy as np

COUL = dict(ok="#22c55e", warn="#f59e0b", bad="#ef4444", info="#3b82f6", mute="#64748b")
FOND = dict(ok="rgba(34,197,94,.12)", warn="rgba(245,158,11,.12)", bad="rgba(239,68,68,.12)", info="rgba(59,130,246,.12)", mute="rgba(100,116,139,.12)")
ICON = dict(ok="●", warn="▲", bad="■", info="◆", mute="○")

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap');
html, body, [class*="css"], .stMarkdown, .stText { font-family: 'Inter', sans-serif; }
.block-container { padding-top: 1.6rem; padding-bottom: 3rem; max-width: 1400px; }
header[data-testid="stHeader"] { background: transparent; }
.num { font-family: 'JetBrains Mono', monospace; font-variant-numeric: tabular-nums; }
.topbar { display:flex; justify-content:space-between; align-items:flex-end; margin-bottom: 1.1rem; gap: 12px; flex-wrap: wrap; }
.brand { font-size: 13px; letter-spacing: .22em; color:#64748b; font-weight:700; }
.title { font-size: 30px; font-weight: 800; color:#f8fafc; line-height:1.1; margin-top:4px; }
.sub { color:#94a3b8; font-size: 14px; margin-top: 4px; }
.card { background:#121a2b; border:1px solid #1e293b; border-radius:16px; padding:16px 18px; height:100%; }
.card.tight { padding: 12px 14px; }
.lab { font-size:11.5px; letter-spacing:.12em; text-transform:uppercase; color:#94a3b8; font-weight:600; }
.big { font-size:30px; font-weight:800; color:#f8fafc; line-height:1.15; }
.mid { font-size:20px; font-weight:700; color:#f1f5f9; }
.txt { font-size:13.5px; color:#cbd5e1; line-height:1.45; }
.small { font-size:12px; color:#64748b; }
.chip { display:inline-block; padding:3px 10px; border-radius:999px; font-size:12px; font-weight:700; letter-spacing:.04em; margin: 2px 4px 2px 0; }
.badge { display:inline-block; padding:5px 12px; border-radius:8px; font-size:12.5px; font-weight:800; letter-spacing:.12em; }
.badge.lg { font-size:16px; padding:8px 16px; }
.row { display:flex; justify-content:space-between; align-items:center; gap:8px; }
.bar { height:8px; background:#1e293b; border-radius:99px; position:relative; overflow:visible; margin-top:8px; }
.bar > i { position:absolute; left:0; top:0; bottom:0; border-radius:99px; }
.bar > b { position:absolute; top:-4px; width:2px; height:16px; background:#e2e8f0; border-radius:2px; }
.law { border-left: 4px solid; }
.counter { text-align:center; }
.counter .n { font-size:40px; font-weight:800; line-height:1; }
.dot { width:14px; height:14px; border-radius:50%; display:inline-block; margin-right:6px; vertical-align:middle; }
.sec { font-size:13px; letter-spacing:.2em; color:#64748b; font-weight:700; margin: 26px 0 10px 0; text-transform: uppercase; }
.kv { display:flex; justify-content:space-between; font-size:13px; color:#cbd5e1; padding:3px 0; border-bottom:1px dashed #1e293b; }
.kv:last-child { border-bottom: none; }
div[data-testid="stTabs"] button p { font-size: 15px; font-weight: 600; }
@media (max-width: 640px) { .block-container { padding-left: .6rem !important; padding-right: .6rem !important; padding-top: 2.6rem !important; } }
</style>
"""

def badge(txt, niv, lg=False):
    return f'<span class="badge{" lg" if lg else ""}" style="color:{COUL[niv]};background:{FOND[niv]};border:1px solid {COUL[niv]}55">{txt}</span>'

def chip(txt, niv):
    return f'<span class="chip" style="color:{COUL[niv]};background:{FOND[niv]}">{txt}</span>'

def bar(frac, niv, repere=None, bande=None):
    """Barre de progression ; repère = trait blanc ; bande = intervalle normal (zone claire)."""
    f = float(np.clip(frac, 0, 1)) * 100
    mk = f'<b style="left:{float(np.clip(repere, 0, 1)) * 100:.1f}%"></b>' if repere is not None else ""
    bd = ""
    if bande is not None:
        a, b = (float(np.clip(x, 0, 1)) * 100 for x in bande)
        bd = f'<u style="position:absolute;left:{a:.1f}%;width:{max(b - a, 0.5):.1f}%;top:-3px;bottom:-3px;border:1px solid #94a3b8;border-radius:4px;background:rgba(148,163,184,.12)"></u>'
    return f'<div class="bar">{bd}<i style="width:{f:.1f}%;background:{COUL[niv]}"></i>{mk}</div>'

def jauge(valeur, vmax, niv, repere=None, w=150):
    """Demi-cercle : arc rempli jusqu'à valeur / vmax, repère (seuil) en trait blanc."""
    r = w / 2 - 10; cx = w / 2; cy = w / 2; h = w / 2 + 6
    def pt(f): a = np.pi * (1 - f); return cx + r * np.cos(a), cy - r * np.sin(a)
    f = float(np.clip(valeur / vmax, 0, 1)); x0, y0 = pt(0); x1, y1 = pt(1); xf, yf = pt(f)
    base = f'<path d="M{x0:.1f},{y0:.1f} A{r:.1f},{r:.1f} 0 0 1 {x1:.1f},{y1:.1f}" stroke="#1e293b" stroke-width="12" fill="none" stroke-linecap="round"/>'
    arc = f'<path d="M{x0:.1f},{y0:.1f} A{r:.1f},{r:.1f} 0 0 1 {xf:.1f},{yf:.1f}" stroke="{COUL[niv]}" stroke-width="12" fill="none" stroke-linecap="round"/>' if f > 0.005 else ""
    mk = ""
    if repere is not None:
        fr = float(np.clip(repere / vmax, 0, 1)); a = np.pi * (1 - fr)
        mk = f'<line x1="{cx + (r - 11) * np.cos(a):.1f}" y1="{cy - (r - 11) * np.sin(a):.1f}" x2="{cx + (r + 11) * np.cos(a):.1f}" y2="{cy - (r + 11) * np.sin(a):.1f}" stroke="#e2e8f0" stroke-width="2.5"/>'
    return f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">{base}{arc}{mk}</svg>'

def sparkline(vals, niv="info", w=280, h=56, bandes=None):
    v = np.asarray(vals, float); v = v[~np.isnan(v)]
    if len(v) < 2: return ""
    lo, hi = v.min(), v.max()
    if bandes: lo, hi = min(lo, bandes[0]), max(hi, bandes[1])
    rng = hi - lo or 1; W = w - 40 if bandes else w
    xs = np.linspace(2, W, len(v)); ys = h - 4 - (v - lo) / rng * (h - 8)
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys)); c = COUL[niv]
    area = f'<polygon points="2,{h} {pts} {W:.1f},{h}" fill="{c}" opacity=".10"/>'
    cone = ""
    if bandes:
        yl = h - 4 - (bandes[0] - lo) / rng * (h - 8); yh = h - 4 - (bandes[1] - lo) / rng * (h - 8)
        cone = f'<polygon points="{W:.1f},{ys[-1]:.1f} {w - 2},{yh:.1f} {w - 2},{yl:.1f}" fill="#3b82f6" opacity=".28"/>'
    return (f'<svg width="100%" height="{h}" viewBox="0 0 {w} {h}" preserveAspectRatio="none">{area}{cone}'
            f'<polyline points="{pts}" fill="none" stroke="{c}" stroke-width="2"/><circle cx="{xs[-1]:.1f}" cy="{ys[-1]:.1f}" r="3" fill="{c}"/></svg>')

def carte(html, cls="card", style=""):
    return f'<div class="{cls}" style="{style}">{html}</div>'
