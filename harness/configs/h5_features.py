"""H5: precomputed features in the state. Jev is weak at pattern-spotting and counting, so code extracts the facts:
trial-registry ids, 'randomi[sz]ed' in the title, structured-abstract section names, abstract length, work type, year, language.
Same questions and derive as v1.
"""
import re
import configs.v1 as v1
NAME = 'h5_features'
NOTES = 'v1 + code-extracted signals in state (registry ids, randomized-in-title, sections, length, type, year, lang)'

RULE = v1.RULE + (" The `signals` field lists facts extracted by code from the title and abstract; use them as evidence, "
                  "but a registration number or the word randomized does not by itself make this paper the trial's primary report.")
REG = re.compile(r'\b(NCT\d{8}|ISRCTN\s?\d{8}|ChiCTR[-\w]*\d{6,}|ACTRN\d{14}|DRKS\d{8}|CTRI/\d{4}/\d{2}/\d{6}|UMIN\d{9}|NTR\d{3,5}|EudraCT\s?\d{4}-\d{6}-\d{2}|PROSPERO\s?CRD\d{11}|CRD\d{11}|KCT\d{7}|JPRN-\w+|IRCT\w+|PACTR\d{15}|TCTR\d{11}|SLCTR/\d{4}/\d{3})\b', re.I)
SECTIONS = re.compile(r'\b(background|objective[s]?|aim[s]?|introduction|methods?|design|setting|participants|patients|interventions?|main outcome measures?|results|conclusions?|discussion|trial registration|registration|funding)\s*[:.]', re.I)
RANDOMI = re.compile(r'randomi[sz]', re.I)

def questions(): return v1.questions()

def signals(w):
    t = w.get('title') or ''; ab = w.get('abstract') or ''
    regs = sorted(set(m.group(0).upper().replace(' ', '') for m in REG.finditer(t + ' ' + ab)))
    secs = [m.group(1).lower() for m in SECTIONS.finditer(ab)]
    return {
        'registry_ids': regs[:6] or 'none',
        'randomized_in_title': bool(RANDOMI.search(t)),
        'randomized_in_abstract': bool(RANDOMI.search(ab)),
        'structured_abstract_sections': sorted(set(secs))[:10] or 'none',
        'abstract_words': len(ab.split()),
        'work_type': w.get('type') or 'unknown', 'year': w.get('year'), 'language': w.get('language') or 'unknown',
    }

def state_for(w):
    s = {"rule_design": RULE, "signals": signals(w), "title": w.get("title") or ""}
    if w.get("venue"): s["venue"] = w["venue"]
    if w.get("abstract"): s["abstract"] = w["abstract"][:6000]
    return s

def derive(a, w): return v1.derive(a, w)
