"""Reconstruct the Markdown guide from the official V10 PDF (novembre 2026).

Usage:
    python _scripts/build_markdown.py [path/to/guide.pdf] [--debug]

Layout of the V10 PDF (43 pages, A4):
  p.1        cover
  p.2-4      preamble (Préambule … Abréviations)
  p.5-7      sommaire, with the full statement (énoncé) of the 33 indicators
  p.8-40     one page per indicator (indicator N is on page N + 7)
  p.41-42    glossary
  p.43       back cover

Each indicator page is a two-column layout:
  - top-left  : blue "INDICATEUR COMMUN / SPECIFIQUE" box  -> RASTER IMAGE
                (V10 additions are overlaid on it as white text)
  - top-right : grey "NIVEAU ATTENDU" box                  -> RASTER IMAGE
                (on some pages the body is real text overlaid on the image)
  - below     : "EXEMPLES DE PREUVES" (left), "NON-CONFORMITÉ" and
                "OBLIGATIONS SPÉCIFIQUES" (right), in varying vertical order
  - bottom    : optional full-width "Sous-traitance" box

Because the two boxes are images, text extraction alone cannot recover them:
  - the énoncé is taken from the sommaire (real text, checked against the
    décret n° 2026-728);
  - the niveau attendu is taken from the text layer when the box contains
    text, otherwise from the manual transcription in `raster_v10.py`.

Sections are located by the position of their headings rather than by fixed
coordinates, since the V10 pages do not share a single grid.
"""
import re
import sys
import unicodedata
from pathlib import Path

import pymupdf

from raster_v10 import INDICATOR_TYPES, NIVEAU_ATTENDU_RASTER

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PDF = ROOT / "guide-lecture-qualiopi-v10-nov2026.pdf"
OUT = ROOT / "guide_de_lecture_qualiopi_v10_novembre_2026.md"

N_INDICATORS = 33
INDICATOR_PAGE_OFFSET = 7          # indicator N is on page N + 7 (1-based)
GLOSSARY_PAGES = (41, 42)          # 1-based
COL_SPLIT = 298                    # x separating left and right columns
FOOTER_Y = 780                     # page numbers live below this

HEADINGS = {
    "NIVEAU ATTENDU": "niveau_attendu",
    "EXEMPLES DE PREUVES": "preuves",
    "NON-CONFORMITÉ": "non_conformite",
    "OBLIGATIONS SPÉCIFIQUES": "obligations",
    "Sous-traitance": "sous_traitance",
}

# Prefixes that keep their hyphen when a compound word is split across lines
HYPHEN_PREFIXES = {
    "non", "sous", "sur", "pré", "post", "anti", "demi", "mi", "semi", "ex",
    "co", "ré", "néo", "auto", "multi", "ultra", "para", "inter", "intra",
    "extra", "trans", "vice", "archi", "super", "hyper", "hypo", "méga",
    "mini", "maxi", "micro", "macro", "pro", "pseudo", "quasi", "tri", "bi",
    "uni", "compte", "travail", "porte", "garde", "rendez", "arc", "afro",
    "anglo", "socio", "enquêtes", "auto", "celui", "celle", "au",
}

# --- text helpers ---------------------------------------------------------

def rewrap_paragraphs(text: str) -> str:
    """Join visual lines into paragraphs, with smart hyphenation handling."""
    paras, cur = [], ""

    def flush():
        nonlocal cur
        if cur.strip():
            paras.append(cur.strip())
        cur = ""

    for raw in text.split("\n"):
        line = raw.strip()
        if not line:
            flush()
            continue
        if line.startswith(("•", "·", "- ", "– ")) or re.match(r"^-\s", line):
            flush()
            cur = line
            continue
        if not cur:
            cur = line
            continue
        last = cur.rstrip()[-1]
        legal_ref = re.search(r"\b(?:L|R|D|art)\.$", cur) and line[0].isdigit()   # "article L." / "6231-2"
        if last in ".!?…;" and not legal_ref and (line[0].isupper() or line[0].isdigit() or line[0] == "«"):
            flush()
            cur = line
            continue
        if cur.endswith("-") and len(cur) >= 2 and cur[-2].isalpha() and line[0].islower():
            m = re.search(r"([A-Za-zÀ-ÿ]+)-$", cur)
            prev = m.group(1).lower() if m else ""
            cur = cur + line if prev in HYPHEN_PREFIXES else cur[:-1] + line
        else:
            cur = cur + " " + line
    flush()
    return "\n\n".join(paras)


def fix_french_spacing(text: str) -> str:
    """Tidy French punctuation spacing without breaking URLs."""
    urls = []

    def _mask(m):
        urls.append(m.group(0))
        return f"\x00URL{len(urls) - 1}\x00"

    text = re.sub(r"(?:https?://|www\.)\S+", _mask, text)
    text = re.sub(r"[ \t ]+", " ", text)
    text = re.sub(r" +([,.\)\]])", r"\1", text)
    text = re.sub(r"([\(\[]) +", r"\1", text)
    text = re.sub(r"([^\s\-/])([;:!\?»])", r"\1 \2", text)
    text = re.sub(r"«(?=\S)", "« ", text)
    for i, u in enumerate(urls):
        text = text.replace(f"\x00URL{i}\x00", u)
    return text.strip()


def bullets_to_lists(text: str) -> str:
    """'• item' / '- item' paragraphs become a compact Markdown list."""
    out = []
    for p in text.split("\n\n"):
        m = re.match(r"^(?:•|·|-|–)\s*(.+)$", p, flags=re.DOTALL)
        if m:
            item = "- " + m.group(1).strip()
            if out and out[-1].startswith("- "):
                out[-1] += "\n" + item
            else:
                out.append(item)
        else:
            out.append(p)
    return "\n\n".join(out)


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = rewrap_paragraphs(text)
    text = "\n\n".join(fix_french_spacing(p) for p in text.split("\n\n"))
    text = bullets_to_lists(text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()

# --- page model -------------------------------------------------------------

# Only vector fills count as occluders: the raster boxes have transparent
# margins, so their bounding boxes overlap text that is visible on the page.
OCCLUDERS = ("fill-path", "fill-shade")


def page_spans(page, drop_occluded=True):
    """Visible text spans as dicts: x0,y0,x1,y1,base,text,white,bold,title.

    Built from the text trace, which carries the painting order (seqno) of
    each span. The PDF contains "ghost" layers — leftover text from the V9
    template painted first and then hidden under an opaque shape or image
    painted later. A span whose centre is covered by a fill/image painted
    after it is invisible on the page and is dropped.
    """
    log = page.get_bboxlog()
    occluders = [(i, pymupdf.Rect(r)) for i, (kind, r) in enumerate(log) if kind in OCCLUDERS]
    out = []
    for tr in page.get_texttrace():
        if tr["type"] == 3 or tr["opacity"] == 0:      # invisible render mode
            continue
        # split the trace span on its own line breaks (rare) by baseline
        chars = tr["chars"]
        text = "".join(chr(c[0]) for c in chars)
        if not text.strip():
            continue
        groups, cur = [], [chars[0]]
        for c in chars[1:]:
            if abs(c[2][1] - cur[-1][2][1]) > 2:
                groups.append(cur)
                cur = [c]
            else:
                cur.append(c)
        groups.append(cur)
        r, g, b = (tr["color"] + (0, 0, 0))[:3]
        for grp in groups:
            t = "".join(chr(c[0]) for c in grp)
            if not t.strip():
                continue
            rect = pymupdf.Rect()
            for c in grp:
                rect |= pymupdf.Rect(c[3])
            centre = pymupdf.Point((rect.x0 + rect.x1) / 2, (rect.y0 + rect.y1) / 2)
            if drop_occluded and any(i > tr["seqno"] and o.contains(centre) for i, o in occluders):
                continue
            out.append({
                "x0": rect.x0, "y0": rect.y0, "x1": rect.x1, "y1": rect.y1,
                "base": grp[0][2][1], "text": t,
                "white": min(r, g, b) > 0.99,
                "bold": "Bold" in tr["font"],
                "title": abs(r - 0.184) < 0.01 and abs(b - 0.588) < 0.01,
                "seq": tr["seqno"],
            })
    return out


def rows_of(spans, tol=2.5):
    """Group spans into visual rows (same baseline), each sorted by x."""
    rows = []
    for s in sorted(spans, key=lambda s: (s["base"], s["x0"])):
        if rows and abs(rows[-1][0]["base"] - s["base"]) <= tol:
            rows[-1].append(s)
        else:
            rows.append([s])
    return [sorted(r, key=lambda s: s["x0"]) for r in rows]


def row_text(row) -> str:
    parts = []
    for i, s in enumerate(row):
        t = s["text"]
        if i and not parts[-1].endswith(" ") and not t.startswith(" "):
            # spans of a justified line are separated by a visible gap;
            # spans glued together (font change mid-word) are not
            if s["x0"] - row[i - 1]["x1"] > 1.2:
                t = " " + t
        parts.append(t)
    return re.sub(r" {2,}", " ", "".join(parts)).strip()


def rows_to_text(rows) -> str:
    """Join rows; a vertical gap larger than ~1.5 line produces a blank line."""
    lines, prev = [], None
    for r in rows:
        y0 = min(s["y0"] for s in r)
        y1 = max(s["y1"] for s in r)
        if prev is not None and y0 - prev[1] > 0.55 * (prev[1] - prev[0]) + 1.5:
            lines.append("")
        lines.append(row_text(r))
        prev = (y0, y1)
    return "\n".join(lines)


def large_images(page):
    return [pymupdf.Rect(i["bbox"]) for i in page.get_image_info()
            if i["bbox"][2] - i["bbox"][0] > 100 and i["bbox"][3] - i["bbox"][1] > 30]


def find_headings(spans):
    """Return (headings, heading_span_ids). A heading is a row of bold spans
    whose text is one of HEADINGS (spans may split a word: NON / - / CONFORMITÉ).
    Each heading is (key, rect, full_width)."""
    def squash(t):
        return re.sub(r"\s+", "", unicodedata.normalize("NFC", t))

    labels = {squash(k): v for k, v in HEADINGS.items()}
    found, ids = [], set()

    def scan(rows):
        for row in rows:
            row = [s for s in row if id(s) not in ids]
            label = squash("".join(s["text"] for s in row))
            if row and label in labels and all(s["bold"] for s in row):
                rect = pymupdf.Rect()
                for s in row:
                    rect |= pymupdf.Rect(s["x0"], s["y0"], s["x1"], s["y1"])
                key = labels[label]
                # the Sous-traitance banner is either centred on the page
                # (full-width box) or the title of a box in one column
                full = key == "sous_traitance" and abs((rect.x0 + rect.x1) / 2 - 311) < 40
                found.append((key, rect, full))
                ids.update(id(s) for s in row)

    # 1) centred full-width banner (straddles the column split)
    scan([r for r in rows_of(spans)
          if r[0]["x0"] < COL_SPLIT < r[-1]["x1"] and r[-1]["x1"] - r[0]["x0"] < 120])
    # 2) column headings
    for left in (True, False):
        scan(rows_of([s for s in spans if ((s["x0"] + s["x1"]) / 2 < COL_SPLIT) == left]))
    return sorted(found, key=lambda h: h[1].y0), ids


def is_footer(s):
    """The page number, in its small box at the bottom centre."""
    return s["y0"] > FOOTER_Y and 275 < s["x0"] < 320 and s["text"].strip().isdigit()


def extract_indicator(doc, num, debug=False):
    page = doc[num + INDICATOR_PAGE_OFFSET - 1]
    spans = [s for s in page_spans(page) if not is_footer(s) and not s["title"]]
    imgs = large_images(page)
    # Blue statement box: the large image starting in the left column;
    # niveau attendu box: the large image starting in the right column.
    blue = max((r for r in imgs if r.x0 < 120), key=lambda r: r.get_area())
    niveau_box = max((r for r in imgs if r.x0 > 280), key=lambda r: r.get_area())

    headings, heading_ids = find_headings(spans)
    keys = [k for k, _, _ in headings]
    assert len(keys) == len(set(keys)), f"indicateur {num}: duplicated headings {keys}"
    st_full = next((r for k, r, full in headings if k == "sous_traitance" and full), None)

    zones = {k: [] for k in HEADINGS.values()}
    zones["enonce_overlay"] = []
    zones["orphan"] = []
    for s in spans:
        if id(s) in heading_ids:
            continue
        cx = (s["x0"] + s["x1"]) / 2
        if st_full is not None and s["y0"] > st_full.y1:
            zones["sous_traitance"].append(s)
            continue
        if blue.contains(pymupdf.Point(cx, (s["y0"] + s["y1"]) / 2)) and s["white"]:
            zones["enonce_overlay"].append(s)
            continue
        if niveau_box.contains(pymupdf.Point(cx, (s["y0"] + s["y1"]) / 2)):
            zones["niveau_attendu"].append(s)
            continue
        left = cx < COL_SPLIT
        # nearest heading above, in the same column
        cands = [(k, h) for k, h, full in headings
                 if not full and h.y0 <= s["y0"] + 1
                 and ((h.x0 + h.x1) / 2 < COL_SPLIT) == left]
        if not cands:
            zones["orphan"].append(s)
            continue
        key = max(cands, key=lambda kh: kh[1].y0)[0]
        if key == "niveau_attendu":
            # text below the grey box but under its heading's column
            zones["orphan"].append(s)
            continue
        zones[key].append(s)

    out = {k: normalize(rows_to_text(rows_of(v))) for k, v in zones.items()}
    if not out["niveau_attendu"]:
        out["niveau_attendu"] = NIVEAU_ATTENDU_RASTER[num]
        out["_niveau_source"] = "raster"
    else:
        out["_niveau_source"] = "text"
    # Text in the left column between the statement box and "EXEMPLES DE
    # PREUVES" is a scope note printed under the statement (indicator 12).
    out["precision"] = out.pop("orphan")
    if debug:
        print(f"\n######## Indicateur {num} (page {num + INDICATOR_PAGE_OFFSET})")
        for k, v in out.items():
            print(f"--- {k}:\n{v}")
    return out

# --- sommaire / preamble / glossary ---------------------------------------

CRITERES = [
    (1, "Les conditions d’information du public sur les prestations proposées, les délais pour y accéder et les résultats obtenus", [1, 2, 3]),
    (2, "L’identification précise des objectifs des prestations proposées et l’adaptation de ces prestations aux publics bénéficiaires lors de la conception des prestations", [4, 5, 6, 7, 8]),
    (3, "L’adaptation aux publics bénéficiaires des prestations et des modalités d’accueil, d’accompagnement, de suivi et d’évaluation mises en œuvre", [9, 10, 11, 12, 13, 14, 15, 16]),
    (4, "L’adéquation des moyens pédagogiques, techniques et d’encadrement aux prestations mises en œuvre", [17, 18, 19, 20]),
    (5, "La qualification et le développement des connaissances et compétences des personnels chargés de mettre en œuvre les prestations", [21, 22]),
    (6, "L’inscription et l’investissement du prestataire dans son environnement professionnel", [23, 24, 25, 26, 27, 28, 29]),
    (7, "Le recueil et la prise en compte des appréciations et des réclamations formulées par les parties prenantes aux prestations délivrées", [30, 31, 32, 33]),
]


def extract_statements(doc) -> dict:
    """Full énoncé of each indicator, from the sommaire (pages 5-7)."""
    text = "\n".join(doc[i].get_text("text") for i in range(4, 7))
    text = re.sub(r"^\s*\d{1,2}\s*$", "", text, flags=re.MULTILINE)   # page numbers
    text = re.sub(r"^\s*Sommaire\s*$", "", text, flags=re.MULTILINE)
    pattern = re.compile(
        r"^\s*(?P<num>\d{1,2})\.\s*(?P<body>.+?)(?=^\s*\d{1,2}\.\s|^\s*Critère|^\s*Glossaire|\Z)",
        flags=re.DOTALL | re.MULTILINE,
    )
    out = {}
    for m in pattern.finditer(text):
        n = int(m.group("num"))
        if not 1 <= n <= N_INDICATORS:
            continue
        body = " ".join(ln.strip() for ln in m.group("body").splitlines() if ln.strip())
        body = re.sub(r"\s*\.{3,}\s*\d+\s*$", "", body)
        body = re.sub(r"(\w)- (\w)", lambda mm: mm.group(1) + "-" + mm.group(2)
                      if mm.group(0)[:-2].lower().endswith(("celui", "celle")) else mm.group(0), body)
        body = re.sub(r"\b(celui|celle)-\s+(ci|là)\b", r"\1-\2", body)
        body = body.replace("'", "’")
        out[n] = fix_french_spacing(body)
    return out


PREAMBLE_SECTION_TITLES = [
    "Organisation du guide",
    "Conduite de l’audit",
    "Indicateurs applicables",
    "Nouveaux entrants",
    "Sous-traitance",
    "Pondération des non-conformités",
    "Abréviations",
]


def extract_preamble(doc):
    raw = "\n".join(doc[i].get_text("text") for i in range(1, 4))
    raw = re.sub(r"^\s*\d{1,2}\s*$", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"^\s*e?\s*Préambule\s*$", "", raw, flags=re.MULTILINE)
    # Footnote 1 (bottom of page 2) -> keep it apart, then re-attach as a note
    foot = re.search(r"^\s*1 (Indicateurs mentionnés en annexe.+?)$", raw, flags=re.MULTILINE)
    footnote = foot.group(1).strip() if foot else ""
    if foot:
        raw = raw[:foot.start()] + raw[foot.end():]
    raw = raw.replace("code du travail1.", "code du travail[^1].")
    # Abbreviations: one per line, keep them as a list
    abbr_m = re.search(r"Abréviations\s*\n(.+)$", raw, flags=re.DOTALL)
    abbrs = []
    if abbr_m:
        abbrs = [ln.strip() for ln in abbr_m.group(1).splitlines() if ln.strip()]
        raw = raw[:abbr_m.start()]
    # Bullet list in "Organisation du guide": '•' alone on its line
    raw = re.sub(r"^\s*•\s*\n\s*", "• ", raw, flags=re.MULTILINE)
    # Section titles stand on their own lines: force blank lines around them
    for t in PREAMBLE_SECTION_TITLES[:-1]:
        raw = re.sub(rf"^\s*{re.escape(t)}\s*$", f"\n\n@@{t}@@\n\n", raw, flags=re.MULTILINE)
    # The "Ce document pourra être complété" line is a separate paragraph
    raw = raw.replace("Ce document pourra", "\n\nCe document pourra")
    text = normalize(raw)
    sections, cur = {"_intro": []}, "_intro"
    for p in text.split("\n\n"):
        m = re.fullmatch(r"@@(.+)@@", p.strip())
        if m:
            cur = m.group(1)
            sections[cur] = []
        else:
            sections[cur].append(p)
    sections["Abréviations"] = abbrs
    return sections, footnote


def render_preamble(sections, footnote) -> str:
    out = ["\n\n".join(sections["_intro"])]
    for t in PREAMBLE_SECTION_TITLES:
        body = sections.get(t)
        if not body:
            continue
        if t == "Abréviations":
            out.append(f"### {t}\n\n" + "\n".join(f"- {a}" for a in body))
            continue
        paras = []
        for p in body:
            if p.startswith("•"):
                p = "- " + p.lstrip("• ").strip()
                if paras and paras[-1].startswith("- ") or (paras and paras[-1].endswith(":")):
                    paras[-1] += "\n" + p
                    continue
            paras.append(p)
        out.append(f"### {t}\n\n" + "\n\n".join(paras))
    if footnote:
        out.append(f"[^1]: {footnote}")
    return "\n\n".join(out)


def extract_glossary(doc) -> dict:
    """Glossary pages -> {indicator number: markdown body}."""
    raw = "\n".join(doc[p - 1].get_text("text") for p in GLOSSARY_PAGES)
    raw = re.sub(r"^\s*\d{1,2}\s*$", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"^\s*GLOSSAIRE\s*$", "", raw, flags=re.MULTILINE)
    # '-' / '•' alone on a line introduces a list item
    raw = re.sub(r"^\s*([-•])\s*\n\s*", r"\1 ", raw, flags=re.MULTILINE)
    heads = list(re.finditer(r"^\s*Indicateur (\d{1,2})\s*$", raw, flags=re.MULTILINE))
    out = {}
    for i, m in enumerate(heads):
        body = raw[m.end(): heads[i + 1].start() if i + 1 < len(heads) else len(raw)]
        items, cur = [], ""
        for ln in body.splitlines():
            ls = ln.strip()
            if not ls:
                continue
            new_item = (
                ls.startswith(("- ", "• "))
                or re.match(r"^[A-ZÉÈÀL][\wéèàâêîôûç’'\- ]{0,70}\s:", ls)
                or ls.startswith("L’accompagnement")
            )
            if cur and new_item:
                items.append(cur)
                cur = ls
            else:
                if cur.endswith("-") and ls[:1].islower():
                    cur += ls
                else:
                    cur = f"{cur} {ls}" if cur else ls
        if cur:
            items.append(cur)
        rendered, in_list = [], False
        for it in items:
            it = fix_french_spacing(it).strip()
            if it.startswith(("- ", "• ")):
                it = "- " + it[2:].strip()
                if rendered and (in_list or rendered[-1].endswith(":")):
                    rendered[-1] += "\n" + it
                    in_list = True
                    continue
            elif ":" in it[:80] and not it.startswith("L’"):
                term, defi = it.split(":", 1)
                it = f"**{term.strip()}** : {defi.strip()}".rstrip()
            in_list = False
            rendered.append(it)
        out[int(m.group(1))] = "\n\n".join(rendered)
    return out

# --- rendering ------------------------------------------------------------

SECTION_TITLES = [
    ("precision", "Précision"),
    ("niveau_attendu", "Niveau attendu"),
    ("preuves", "Exemples de preuves"),
    ("non_conformite", "Non-conformité"),
    ("obligations", "Obligations spécifiques"),
    ("sous_traitance", "Sous-traitance"),
]


def render_indicator(num, statement, data) -> str:
    kind, cats = INDICATOR_TYPES[num]
    label = "Indicateur commun d’appréciation" if kind == "commun" else \
        f"Indicateur spécifique d’appréciation ({', '.join(cats)})"
    parts = [f"### Indicateur {num}", "", f"*{label}*", "", statement, ""]
    for key, title in SECTION_TITLES:
        if data.get(key):
            parts += [f"**{title}**", "", data[key], ""]
    return "\n".join(parts)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    debug = "--debug" in sys.argv
    pdf = Path(args[0]) if args else DEFAULT_PDF
    doc = pymupdf.open(pdf)
    assert doc.page_count == 43, f"unexpected page count {doc.page_count} — not the V10 PDF?"

    statements = extract_statements(doc)
    assert sorted(statements) == list(range(1, N_INDICATORS + 1)), sorted(statements)
    preamble, footnote = extract_preamble(doc)
    glossary = extract_glossary(doc)

    out = [
        "# Guide de lecture — Référentiel national qualité (Qualiopi)",
        "",
        "**Version 10 — novembre 2026** (en vigueur au 1er novembre 2026, décret n° 2026-728 du 1er août 2026)",
        "",
        "> Référentiel mentionné à l'article L. 6316-3 du Code du travail.",
        "",
        "---",
        "",
        "## Préambule",
        "",
        render_preamble(preamble, footnote),
        "",
    ]
    report = []
    for crit, title, nums in CRITERES:
        out.append(f"\n## Critère {crit} — {title}\n")
        for n in nums:
            data = extract_indicator(doc, n, debug=debug)
            report.append((n, data["_niveau_source"], data["precision"]))
            out.append(render_indicator(n, statements[n], data))

    out.append("\n## Glossaire\n")
    for n in sorted(glossary):
        out.append(f"### Indicateur {n}\n\n{glossary[n]}\n")
    out.append("---\n")
    out.append("*Source : Ministère du Travail et des Solidarités, DGEFP — novembre 2026.*\n")

    OUT.write_text("\n".join(out), encoding="utf-8")
    print(f"Wrote {OUT}")
    for n, src, orphan in report:
        flag = f"  ORPHAN TEXT: {orphan[:80]!r}" if orphan else ""
        print(f"  indicateur {n:2d}: niveau attendu from {src}{flag}")


if __name__ == "__main__":
    main()
