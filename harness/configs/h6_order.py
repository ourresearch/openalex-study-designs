"""H6: state ordering. For structured abstracts, put the Methods/Design sentences first as their own field, then title,
then the rest of the abstract. Position effects: the design evidence leads. Questions and derive as v1.
"""
import re
import configs.v1 as v1
NAME = 'h6_order'
NOTES = 'v1 with a `methods` field extracted from structured abstracts placed before title and abstract'

SEC = re.compile(r'\b(methods?|design|study design|design and setting|design, setting, and participants|materials and methods|methodology)\s*[:.]\s*', re.I)
NEXT = re.compile(r'\b(results?|findings|conclusions?|discussion|outcomes?|main outcome measures?|interventions?|participants|setting)\s*[:.]', re.I)

def methods_of(ab):
    m = SEC.search(ab or '')
    if not m: return None
    rest = ab[m.end():]
    n = NEXT.search(rest)
    return rest[:n.start()].strip() if n else rest[:800].strip()

def questions(): return v1.questions()

def state_for(w):
    s = {"rule_design": v1.RULE}
    meth = methods_of(w.get("abstract") or "")
    if meth: s["methods"] = meth[:1500]
    s["title"] = w.get("title") or ""
    if w.get("venue"): s["venue"] = w["venue"]
    if w.get("abstract"): s["abstract"] = w["abstract"][:6000]
    return s

def derive(a, w): return v1.derive(a, w)
