"""Reconstruct the markdown from the official PDF, page by page, respecting columns."""
import re
import pymupdf

PDF = r"D:\sources\qualiopi-markdown\guide_de_lecture_qualiopi_v9_du_8_janvier_2024.pdf"
OUT = r"D:\sources\qualiopi-markdown\guide_de_lecture_qualiopi_v9_du_8_janvier_2024.md"

PAGE_W, PAGE_H = 596, 842
INDICATOR_FIRST_PAGE = 7

# Prefixes that keep their hyphen in compound French words
HYPHEN_PREFIXES = {
    "non", "sous", "sur", "pré", "post", "anti", "demi", "mi", "semi",
    "ex", "co", "ré", "néo", "auto", "multi", "ultra", "para", "inter",
    "intra", "extra", "trans", "sur", "vice", "archi", "super", "hyper",
    "hypo", "méga", "mini", "maxi", "micro", "macro", "pro", "pseudo",
    "quasi", "tri", "bi", "uni",
    # Common compound first parts (not prefixes proper)
    "compte", "compte-", "travail", "porte", "garde", "rendez",
    "arc", "demi", "afro", "anglo",
}

# --- text helpers -------------------------------------------------------

def rewrap_paragraphs(text: str) -> str:
    """Join visual lines into paragraphs, with smart hyphenation handling."""
    lines = [ln.rstrip() for ln in text.split("\n")]
    paras = []
    cur = ""

    def flush():
        nonlocal cur
        if cur.strip():
            paras.append(cur.strip())
        cur = ""

    for raw in lines:
        line = raw.strip()
        if not line:
            flush()
            continue
        # Bullet starts a new paragraph
        if line.startswith(("•", "·")):
            flush()
            cur = line
            continue
        if not cur:
            cur = line
            continue
        # Sentence end + capital → new paragraph
        last_char = cur.rstrip()[-1] if cur.rstrip() else ""
        if last_char in ".!?…" and (line[0].isupper() or line[0].isdigit() or line[0] == "«"):
            flush()
            cur = line
            continue
        # Hyphen continuation
        if cur.endswith("-") and len(cur) >= 2 and cur[-2].isalpha() and line and line[0].islower():
            # Extract the alpha word immediately before the hyphen (ignore leading punctuation/apostrophe)
            m = re.search(r"([A-Za-zÀ-ÿ]+)-$", cur)
            prev_word = m.group(1).lower() if m else ""
            if prev_word in HYPHEN_PREFIXES:
                # Keep the hyphen (compound)
                cur = cur + line
            else:
                # Drop the hyphen (line-break hyphenation)
                cur = cur[:-1] + line
        else:
            cur = cur + " " + line
    flush()
    return "\n\n".join(paras)

def fix_french_spacing(text: str) -> str:
    """Tidy French punctuation spacing without breaking URLs."""
    urls = []
    def _mask(m):
        urls.append(m.group(0))
        return f"\x00URL{len(urls)-1}\x00"
    text = re.sub(r"https?://\S+", _mask, text)

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s+([,.\)\]])", r"\1", text)
    text = re.sub(r"([\(\[])\s+", r"\1", text)
    text = re.sub(r"([^\s])([;:!\?»])", r"\1 \2", text)
    text = re.sub(r"«\s+", "« ", text)

    for i, u in enumerate(urls):
        text = text.replace(f"\x00URL{i}\x00", u)
    return text.strip()

def filter_phantoms(text: str) -> str:
    """Remove paragraphs that look like clipping artefacts (single chars, tiny letters).
    Does NOT filter short titles."""
    out = []
    paras = text.split("\n\n")
    for p in paras:
        p_str = p.strip()
        if not p_str:
            continue
        # Strip trailing isolated single letters added by clip artifacts
        # e.g. "...en début de formation. p" → drop " p"
        p_str = re.sub(r"\s+[A-Za-zÀ-ÿ]\s*$", "", p_str).strip()
        if not p_str:
            continue
        words = p_str.split()
        # Single character paragraph (e.g. "p", "T")
        if len(p_str) <= 2:
            continue
        # 3+ words mostly single/double letters → phantom
        # (skip bullets and number lists — em-dash separators count as short words)
        if len(words) > 2 and not p_str.startswith(("•", "·")):
            short_ratio = sum(1 for w in words if len(w) <= 2) / len(words)
            if short_ratio > 0.6:
                continue
        # 1-word fragment that is clearly truncated: contains hyphen and ends with 2-3 lowercase letters
        # without being a known prefix (avoids filtering "Sous-traitance")
        if len(words) == 1 and "-" in p_str:
            tail = p_str.rsplit("-", 1)[-1]
            if 1 <= len(tail) <= 3 and tail.islower() and tail not in {"là", "ci", "ou", "et"}:
                # truncated like "Sous-tra"
                if p_str.lower() not in {"sous-traitance", "non-conformité", "non-respect"}:
                    continue
        out.append(p_str)
    return "\n\n".join(out)

def normalize(text: str) -> str:
    text = rewrap_paragraphs(text)
    text = fix_french_spacing(text)
    text = filter_phantoms(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text

# --- zone discovery -----------------------------------------------------

def page_blocks(page):
    """Return cleaned blocks: tuples (x0,y0,x1,y1,text). Filter out empty/decorative."""
    raw = page.get_text("blocks")
    out = []
    for b in raw:
        x0, y0, x1, y1, text, bno, btype = b
        if btype != 0:
            continue
        t = text.strip()
        if not t:
            continue
        if re.fullmatch(r"[\s\|·•\-_]+", t):
            continue
        out.append((x0, y0, x1, y1, t))
    return out

def find_sous_traitance_y_via_words(page):
    """Locate the 'Sous-traitance' banner using words; robust to combined blocks."""
    # Look for 'Sous-traitance' that is roughly centered, font isolated
    for w in page.get_text("words"):
        x0, y0, x1, y1, text, *_ = w
        if text == "Sous-traitance":
            cx = (x0 + x1) / 2
            # Must be centered (banner) — not within a paragraph
            if abs(cx - PAGE_W / 2) < 60:
                return y0
    return None

# --- extracting one indicator page -------------------------------------

def extract_indicator(doc, page_idx):
    page = doc[page_idx]
    blocks = page_blocks(page)
    y_sous = find_sous_traitance_y_via_words(page)
    y_col_bottom = (y_sous - 20) if y_sous else 780

    # Classify blocks by zone, sort by y, join.
    top_blocks  = []
    left_blocks = []
    right_blocks = []
    for b in blocks:
        x0, y0, x1, y1, text = b
        cx = (x0 + x1) / 2
        if y0 > 780:
            continue  # page number
        if y_sous and y0 >= y_sous - 5:
            continue  # handled separately
        if y1 < 110:
            top_blocks.append(b)
        elif cx < 295 and y0 < y_col_bottom:
            left_blocks.append(b)
        elif cx > 305 and y0 < y_col_bottom:
            right_blocks.append(b)

    top_blocks.sort(key=lambda b: (b[1], b[0]))
    left_blocks.sort(key=lambda b: (b[1], b[0]))
    right_blocks.sort(key=lambda b: (b[1], b[0]))

    def join_blocks(bs):
        """Group blocks by vertical proximity; close blocks become one paragraph."""
        if not bs:
            return ""
        groups = [[bs[0]]]
        for b in bs[1:]:
            prev_bottom = groups[-1][-1][3]
            gap = b[1] - prev_bottom
            if gap < 14:
                groups[-1].append(b)
            else:
                groups.append([b])
        # Within a group, join with newline; across groups, blank line
        return "\n\n".join("\n".join(b[4] for b in g) for g in groups)

    top_text = join_blocks(top_blocks)
    left_text_raw = join_blocks(left_blocks)
    right_text_raw = join_blocks(right_blocks)

    # Sous-traitance content (full-width blocks below y_sous)
    sous_text = ""
    if y_sous:
        sous_blocks = [b for b in blocks
                       if b[1] >= y_sous + 5
                       and (b[2] - b[0]) > 350
                       and b[1] < 780]
        sous_blocks.sort(key=lambda b: b[1])
        sous_text = "\n\n".join(b[4] for b in sous_blocks)

    critere_title = normalize(top_text)
    left_normalized = normalize(left_text_raw)
    if "EXEMPLES DE PREUVES" in left_normalized:
        niveau_left, preuves_raw = left_normalized.split("EXEMPLES DE PREUVES", 1)
        niveau_left = niveau_left.strip()
        # Strip any subsequent "EXEMPLES DE PREUVES" markers left by ghost layers
        preuves = re.sub(r"\bEXEMPLES DE PREUVES\b\s*", "", preuves_raw).strip()
    else:
        niveau_left, preuves = "", left_normalized
    right_parsed = split_right(normalize(right_text_raw))
    niveau_parts = [p for p in [niveau_left, right_parsed["niveau_attendu"]] if p]
    niveau_attendu = "\n\n".join(niveau_parts)
    sous_traitance = normalize(sous_text)

    return {
        "critere_title": critere_title,
        "niveau_attendu": niveau_attendu,
        "preuves": preuves,
        "non_conformite": right_parsed["non_conformite"],
        "obligations": right_parsed["obligations"],
        "sous_traitance": sous_traitance,
    }

def strip_header(text: str, header: str) -> str:
    pattern = re.compile(rf"^\s*{re.escape(header)}\s*", flags=re.MULTILINE)
    return pattern.sub("", text, count=1).strip()

def split_right(right_text: str) -> dict:
    out = {"niveau_attendu": "", "non_conformite": "", "obligations": ""}
    pattern = re.compile(r"(NIVEAU ATTENDU|NON-CONFORMIT[ÉE]|OBLIGATIONS SP[ÉE]CIFIQUES)")
    parts = pattern.split(right_text)
    current = None
    for i, p in enumerate(parts):
        p_stripped = p.strip()
        if i == 0:
            continue
        if pattern.fullmatch(p_stripped):
            current = p_stripped
            continue
        body = p_stripped
        if current == "NIVEAU ATTENDU":
            out["niveau_attendu"] = body
        elif current and current.startswith("NON-CONFORMIT"):
            out["non_conformite"] = body
        elif current and current.startswith("OBLIGATIONS"):
            out["obligations"] = body
    return out

# --- summary, preamble, glossary, annexe --------------------------------

def extract_summary_indicators(doc) -> dict:
    text = ""
    for pi in range(3, 6):
        text += "\n" + doc[pi].get_text("text")
    pattern = re.compile(
        r"(?P<num>\d{1,2})\.\s+(?P<body>.+?)(?=\n\s*(?:\d{1,2}\.|Critère|Glossaire|Annexe|$))",
        flags=re.DOTALL,
    )
    indicators = {}
    for m in pattern.finditer(text):
        n = int(m.group("num"))
        if 1 <= n <= 32:
            body = m.group("body").replace("\n", " ")
            body = re.sub(r"\.{2,}.*$", "", body).strip()
            body = re.sub(r"\s+", " ", body).strip()
            # Strip trailing page numbers (1-2 digit isolated tokens after the period)
            body = re.sub(r"\.\s*\d{1,2}\s*$", ".", body)
            # Fix line-break hyphenation patterns ('celui- ci' → 'celui-ci', etc.)
            body = re.sub(r"\b(cel(?:ui|le|les|ux))-\s+(ci|là)\b", r"\1-\2", body)
            body = re.sub(r"\b(rendez)-\s+(vous)\b", r"\1-\2", body)
            body = fix_french_spacing(body)
            indicators[n] = body
    return indicators

PREAMBLE_SECTION_TITLES = [
    "Préambule",
    "Organisation du guide",
    "Conduite de l’audit",
    "Indicateurs applicables",
    "Nouveaux entrants",
    "Sous-traitance",
    "Pondération des non-conformités",
    "Abréviations",
]

def extract_preamble(doc) -> dict:
    """Pages 1-4 (preamble + 'Pondération' + 'Abréviations'), stopping before the Sommaire."""
    parts = []
    for pi in range(0, 4):
        parts.append(doc[pi].get_text("text"))
    full = "\n".join(parts)
    full = re.sub(r"^\s*\d{1,2}\s*$", "", full, flags=re.MULTILINE)
    # Skip cover lockup
    m = re.search(r"La certification qualité.*", full, flags=re.DOTALL)
    if m:
        full = m.group(0)
    # Stop at the start of the table of contents ("Sommaire")
    end_m = re.search(r"\n\s*Sommaire\b", full)
    if end_m:
        full = full[:end_m.start()]
    normalized = normalize(full)

    # Some titles (e.g. "Abréviations") have no blank line after them in the
    # PDF and got merged with the next paragraph. Split them back out.
    paragraphs = normalized.split("\n\n")
    refined = []
    for p in paragraphs:
        p_str = p.strip()
        if not p_str:
            continue
        matched = False
        for title in PREAMBLE_SECTION_TITLES:
            if p_str == title:
                refined.append(title)
                matched = True
                break
            if p_str.startswith(title) and len(p_str) > len(title):
                # Title followed by content on the same paragraph
                rest = p_str[len(title):].lstrip(" : ")
                refined.append(title)
                if rest:
                    refined.append(rest)
                matched = True
                break
        if not matched:
            refined.append(p_str)

    sections = {"_intro": []}
    current = "_intro"
    titles_set = set(PREAMBLE_SECTION_TITLES)
    for p in refined:
        if p in titles_set:
            current = p
            sections.setdefault(current, [])
        else:
            sections.setdefault(current, []).append(p)
    return sections

def render_preamble(sections) -> str:
    parts = []
    if sections.get("_intro"):
        parts.append("\n\n".join(sections["_intro"]))
    for title in PREAMBLE_SECTION_TITLES:
        if title in sections and sections[title]:
            parts.append(f"\n### {title}\n\n" + "\n\n".join(sections[title]))
    return "\n\n".join(parts).strip()

def extract_glossary(doc) -> dict:
    """Pages 39-40 → dict mapping 'Indicateur N' → entries.

    Splitting happens BEFORE rewrap because the PDF puts no blank line
    between 'Indicateur N' and its first definition.
    """
    parts = []
    for pi in [38, 39]:
        t = doc[pi].get_text("text")
        t = re.sub(r"^\s*\d{1,2}\s*$", "", t, flags=re.MULTILINE)
        t = re.sub(r"^GLOSSAIRE\s*$", "", t, flags=re.MULTILINE)
        parts.append(t)
    raw = "\n".join(parts)
    # Split by 'Indicateur N' header (must be on its own line)
    pattern = re.compile(r"^[ \t]*Indicateur (\d{1,2})[ \t]*$", flags=re.MULTILINE)
    matches = list(pattern.finditer(raw))
    out = {}
    if not matches:
        return {"_": normalize(raw)}
    for i, m in enumerate(matches):
        num = int(m.group(1))
        start = m.end()
        end = matches[i+1].start() if i+1 < len(matches) else len(raw)
        body = raw[start:end]
        # Treat each definition (one per line, label-style) as its own paragraph
        # by inserting a blank line before each "Label :" line.
        lines = body.split("\n")
        body_para = []
        cur = ""
        for ln in lines:
            ls = ln.strip()
            if not ls:
                if cur:
                    body_para.append(cur)
                    cur = ""
                continue
            # New definition starts with "Word ... :" before midline? Heuristic:
            # if line starts with an uppercase word and contains " : " in first 60 chars
            if cur and re.match(r"^[A-ZÉÈÀ][\wéèàâêîôûç’'\- ]{0,60}\s:", ls):
                body_para.append(cur)
                cur = ls
            else:
                cur = cur + " " + ls if cur else ls
        if cur:
            body_para.append(cur)
        # Now normalize each para (cleans hyphenation etc.)
        cleaned = [normalize(p) for p in body_para if p.strip()]
        out[f"Indicateur {num}"] = "\n\n".join(cleaned).strip()
    return out

def render_glossary(gloss: dict) -> str:
    parts = []
    for key in sorted(gloss.keys(), key=lambda k: int(re.search(r"\d+", k).group()) if re.search(r"\d+", k) else 0):
        if key == "_":
            parts.append(gloss[key])
        else:
            parts.append(f"\n### {key}\n\n{gloss[key]}")
    return "\n\n".join(parts).strip()

def extract_annexe(doc) -> str:
    t = doc[40].get_text("text")
    t = re.sub(r"^\s*\d{1,2}\s*$", "", t, flags=re.MULTILINE)
    t = re.sub(r"^\s*Annexe\s*$", "", t, flags=re.MULTILINE | re.IGNORECASE)
    return normalize(t)

# --- markdown rendering -------------------------------------------------

CRITERES = [
    (1, "Les conditions d’information du public sur les prestations proposées, les délais pour y accéder et les résultats obtenus", [1, 2, 3]),
    (2, "L’identification précise des objectifs des prestations proposées et l’adaptation de ces prestations aux publics bénéficiaires lors de la conception des prestations", [4, 5, 6, 7, 8]),
    (3, "L’adaptation aux publics bénéficiaires des prestations et des modalités d’accueil, d’accompagnement, de suivi et d’évaluation mises en œuvre", [9, 10, 11, 12, 13, 14, 15, 16]),
    (4, "L’adéquation des moyens pédagogiques, techniques et d’encadrement aux prestations mises en œuvre", [17, 18, 19, 20]),
    (5, "La qualification et le développement des connaissances et compétences des personnels chargés de mettre en œuvre les prestations", [21, 22]),
    (6, "L’inscription et l’investissement du prestataire dans son environnement professionnel", [23, 24, 25, 26, 27, 28, 29]),
    (7, "Le recueil et la prise en compte des appréciations et des réclamations formulées par les parties prenantes aux prestations délivrées", [30, 31, 32]),
]

def render_indicator(num, statement, data) -> str:
    parts = [f"### Indicateur {num}", "", statement, ""]
    if data["niveau_attendu"]:
        parts += ["**Niveau attendu**", "", data["niveau_attendu"], ""]
    if data["preuves"]:
        parts += ["**Exemples de preuves**", "", data["preuves"], ""]
    if data["non_conformite"]:
        parts += ["**Non-conformité**", "", data["non_conformite"], ""]
    if data["obligations"]:
        parts += ["**Obligations spécifiques**", "", data["obligations"], ""]
    if data["sous_traitance"]:
        parts += ["**Sous-traitance**", "", data["sous_traitance"], ""]
    return "\n".join(parts)

def main():
    doc = pymupdf.open(PDF)
    indicators = extract_summary_indicators(doc)
    preamble = extract_preamble(doc)
    glossary = extract_glossary(doc)
    annexe = extract_annexe(doc)

    print(f"Indicators recovered: {len(indicators)}")
    print(f"Preamble sections: {[k for k in preamble.keys() if k != '_intro']}")
    print(f"Glossary entries: {list(glossary.keys())[:5]}...")

    out = []
    out.append("# Guide de lecture — Référentiel national qualité (Qualiopi)")
    out.append("")
    out.append("**Version 9 — 8 janvier 2024**")
    out.append("")
    out.append("> Référentiel mentionné à l'article L. 6316-3 du Code du travail.")
    out.append("")
    out.append("---")
    out.append("")
    out.append("## Préambule")
    out.append("")
    out.append(render_preamble(preamble))
    out.append("")

    for crit_num, title, ind_nums in CRITERES:
        out.append(f"\n## Critère {crit_num} — {title}\n")
        for n in ind_nums:
            page_idx = INDICATOR_FIRST_PAGE - 1 + (n - 1)
            data = extract_indicator(doc, page_idx)
            stmt = indicators.get(n, "(énoncé non trouvé)")
            out.append(render_indicator(n, stmt, data))

    out.append("\n## Glossaire\n")
    out.append(render_glossary(glossary))
    out.append("\n## Annexe — Modalités d'audit aménagées (article 10)\n")
    out.append(annexe)
    out.append("\n---\n")
    out.append("*Source : Ministère du Travail, du Plein emploi et de l'Insertion, DGEFP — janvier 2024.*\n")

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print(f"Wrote {OUT}")

if __name__ == "__main__":
    main()
