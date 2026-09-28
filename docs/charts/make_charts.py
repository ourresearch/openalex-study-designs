"""Draw the README's charts as static SVGs.

    python3 docs/charts/make_charts.py

Numbers are read from benchmarks/data/pubmed/results.json (written by benchmarks/score_pubmed.py) or typed in
below; the README's tables carry the same numbers, so the charts can be checked against them.
"""
import json
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
OUT = HERE.parent / "img"

# One version per chart that reads on GitHub's light (#ffffff) and dark (#0d1117) pages alike (a <picture> with a
# dark variant follows the operating system, not the GitHub theme). Text #707a84 is 4.4:1 on both; the two bar
# colors clear 3:1 on both and pass a colour-blind separation check.
THEME = dict(ink="#707a84", grid="#8b949e", pubmed="#199e70", ours="#2a78d6")
FONT = '-apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial, sans-serif'
ORDER = ["randomized-controlled-trial", "clinical-trial", "observational-study", "case-report", "systematic-review",
         "meta-analysis", "study-protocol"]
NAME = {"randomized-controlled-trial": "Randomized Controlled Trial", "clinical-trial": "Clinical Trial",
        "observational-study": "Observational Study", "case-report": "Case Report",
        "systematic-review": "Systematic Review", "meta-analysis": "Meta-Analysis", "study-protocol": "Study Protocol"}


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class Svg:
    def __init__(self, w, h, title):
        self.w, self.h, self.parts, self.title = w, h, [], title

    def add(self, s):
        self.parts.append(s)

    def text(self, x, y, s, fill, size=14, anchor="start", weight=400):
        self.add(f'<text x="{x:.1f}" y="{y:.1f}" fill="{fill}" font-size="{size}" font-weight="{weight}" '
                 f'text-anchor="{anchor}" dominant-baseline="middle">{esc(s)}</text>')

    def line(self, x1, y1, x2, y2, stroke, opacity=0.35):
        self.add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" '
                 f'stroke-width="1" stroke-opacity="{opacity}"/>')

    def save(self, path):
        path.write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" width="{self.w}" height="{self.h}" '
            f'role="img" font-family=\'{FONT}\' style="font-variant-numeric: tabular-nums">\n'
            f'<title>{esc(self.title)}</title>\n' + "\n".join(self.parts) + "\n</svg>\n")


def hbar(x0, y, w, h, r=4):
    """Bar from the baseline x0, square at the baseline, rounded at the data end."""
    if w < 0.5:
        return ""
    r = min(r, w / 2, h / 2)
    return (f"M{x0:.1f},{y:.1f} H{x0 + w - r:.1f} Q{x0 + w:.1f},{y:.1f} {x0 + w:.1f},{y + r:.1f} "
            f"V{y + h - r:.1f} Q{x0 + w:.1f},{y + h:.1f} {x0 + w - r:.1f},{y + h:.1f} H{x0:.1f} Z")


def legend(s, x, y, items, t):
    for label, color in items:
        s.add(f'<rect x="{x}" y="{y - 6}" width="12" height="12" rx="2" fill="{color}"/>')
        s.text(x + 18, y, label, t["ink"], 14)
        x += 18 + len(label) * 7.6 + 26


def grouped(t, title, rows, series, fmt, sub=None):
    """Grouped horizontal bars on a visible 0-100% scale, one row per study design."""
    W, L, R, bh, gap, pad = 720, 210, 56, 14, 4, 22
    n = len(series)
    top = 62
    rowH = n * bh + (n - 1) * gap + pad
    H = top + len(rows) * rowH + 4
    s = Svg(W, H, title)
    x = lambda v: L + v / 100 * (W - L - R)
    legend(s, L, 14, series, t)
    for tick in (0, 25, 50, 75, 100):
        s.line(x(tick), top - 12, x(tick), H - 4, t["grid"], opacity=0.8 if tick == 0 else 0.35)
        s.text(x(tick), top - 22, f"{tick}%", t["ink"], 12, "middle")
    for i, (label, vals) in enumerate(rows):
        y0 = top + i * rowH + pad / 2
        cy = y0 + (n * bh + (n - 1) * gap) / 2
        s.text(0, cy, label, t["ink"], 15, weight=600)
        for j, v in enumerate(vals):
            y = y0 + j * (bh + gap)
            s.add(f'<path d="{hbar(x(0), y, x(v) - x(0), bh)}" fill="{series[j][1]}"/>')
            s.text(x(v) + 6, y + bh / 2, fmt(v), t["ink"], 13, weight=600 if j == n - 1 else 400)
    return s


def main():
    t = THEME
    OUT.mkdir(exist_ok=True)
    res = json.loads((ROOT / "benchmarks/data/pubmed/results.json").read_text())
    series = [("PubMed's tags", t["pubmed"]), ("OpenAlex", t["ours"])]
    pct = lambda v: f"{v:.0f}%" if v < 99.5 or v == 100 else f"{v:.1f}%"
    rows = [(NAME[v], [100 * res[v]["est"]["precision_pubmed"], 100 * res[v]["est"]["precision_openalex"]]) for v in ORDER]
    grouped(t, "Precision on the same PubMed-indexed works: PubMed's tags and OpenAlex's, by study design",
            rows, series, pct).save(OUT / "precision-vs-pubmed.svg")
    rows = [(NAME[v], [100 * res[v]["est"]["recall_pubmed"], 100 * res[v]["est"]["recall_openalex"]]) for v in ORDER]
    grouped(t, "Recall on the same PubMed-indexed works: PubMed's tags and OpenAlex's, by study design",
            rows, series, lambda v: f"{v:.0f}%").save(OUT / "recall-vs-pubmed.svg")
    print("wrote", ", ".join(p.name for p in sorted(OUT.glob("*.svg"))))


if __name__ == "__main__":
    main()
