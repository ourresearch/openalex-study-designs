"""Code-side text signals shared by configs. stated_random(): does the title/abstract explicitly say random allocation
(any of ~10 languages)? Under rubric v2 an RCT must state randomisation, so this is a hard gate, not a hint.
The same three regexes as tagger/study_design.py (tagger/check_same.py compares them on text).

The cached development set holds no text. Each of its works carries `gates`, the three answers computed from the text
the tagger read; when a work has no title, these functions return those answers."""
import re
RAND = re.compile(r"randomi[sz]|randomly|at random|random(?:ized|ised|isation|ization)?\b|aleatori[sz]|aleat[oó]ri|randomisiert|randomisé|"
                  r"gerandomiseerd|randomiser|随机|ランダム|無作為|무작위|рандомиз|случайн|losow", re.I)
def _cached(w, k):
    return w['gates'][k] if 'title' not in w and 'gates' in w else None
def stated_random(w):
    c = _cached(w, 'stated_random')
    if c is not None: return c
    return bool(RAND.search((w.get('title') or '') + ' ' + (w.get('abstract') or '')))
SIM = re.compile(r"\b(simulat(?:ion|or|ed)|manikin|mannequin|phantom|cadaver(?:ic|s)?|bench(?:top)?\s+(?:study|model)|in vitro)\b", re.I)
def simulation_title(w):
    c = _cached(w, 'simulation_title')
    if c is not None: return c
    return bool(SIM.search(w.get('title') or ''))
SECONDARY = re.compile(r"\b(secondary|post[- ]?hoc|exploratory|subgroup|sub-study|substudy|ancillary|pooled|mediation|moderat(?:or|ion))\s+analys|"
                       r"\b(safety|secondary|data|lessons|insights|analysis)\s+from\s+(?:a|the|two|three|\d+)\s+randomi|"
                       r"\bparticipants\s+(?:of|in|from)\s+(?:a|the)\s+randomi|\bin\s+the\s+[A-Z][A-Za-z0-9-]+\s+trial\b", re.I)
def secondary_title(w):
    c = _cached(w, 'secondary_title')
    if c is not None: return c
    return bool(SECONDARY.search(w.get('title') or ''))
