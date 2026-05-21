"""Split the complete Markdown guide into one file per indicator + INDEX.md.

Reads:  guide_de_lecture_qualiopi_v9_du_8_janvier_2024.md
Writes: indicateurs/NN-slug.md  (32 files)
        indicateurs/INDEX.md
"""
import re
from pathlib import Path

ROOT = Path(r"D:\sources\qualiopi-markdown")
SOURCE = ROOT / "guide_de_lecture_qualiopi_v9_du_8_janvier_2024.md"
OUT_DIR = ROOT / "indicateurs"

# --- metadata maps --------------------------------------------------------

# Slugs for each indicator (short, kebab-case, used in filenames and links)
SLUGS = {
    1:  "information-publique",
    2:  "indicateurs-resultats",
    3:  "taux-obtention-certification",
    4:  "analyse-besoin-beneficiaire",
    5:  "objectifs-operationnels",
    6:  "contenus-modalites",
    7:  "adequation-contenus-certification",
    8:  "positionnement-evaluation-entree",
    9:  "conditions-deroulement",
    10: "mise-en-oeuvre-adaptation",
    11: "evaluation-atteinte-objectifs",
    12: "engagement-prevention-ruptures",
    13: "alternance-coordination",
    14: "accompagnement-socio-professionnel",
    15: "droits-devoirs-apprentis",
    16: "presentation-certification",
    17: "moyens-techniques-encadrement",
    18: "coordination-intervenants",
    19: "ressources-pedagogiques",
    20: "referent-handicap-mobilite",
    21: "competences-intervenants",
    22: "developpement-competences-salaries",
    23: "veille-legale-reglementaire",
    24: "veille-competences-metiers",
    25: "veille-innovations-pedagogiques",
    26: "handicap-expertise-reseau",
    27: "sous-traitance-portage",
    28: "partenaires-socio-economiques",
    29: "insertion-poursuite-etudes",
    30: "recueil-appreciations",
    31: "traitement-reclamations",
    32: "mesures-amelioration",
}

# Indicators that can be graded as "mineure ou majeure" (else: majeure only)
GRADUATED_INDICATORS = {1, 2, 3, 8, 9, 12, 13, 17, 18, 19, 23, 24, 25, 28, 30}

# Indicators with adapted "Nouveaux entrants" audit modalities
# (cited in the preamble: "indicateurs 2, 3, 11, 13, 14, 19, 22, 24, 25, 26 et 32")
NOUVEAUX_ENTRANTS = {2, 3, 11, 13, 14, 19, 22, 24, 25, 26, 32}

SOURCE_NOTE = "Guide de lecture du Référentiel national qualité — V9 du 8 janvier 2024, DGEFP, Ministère du Travail."

# --- parsing --------------------------------------------------------------

def parse_complete_md(text: str):
    """Yield {num, critere, critere_title, body} per indicator."""
    # First, split by critère
    critere_pattern = re.compile(
        r"^## Critère (\d+) — (.+?)$",
        flags=re.MULTILINE,
    )
    # Find all critère headers with positions
    crit_matches = list(critere_pattern.finditer(text))

    indicator_pattern = re.compile(
        r"^### Indicateur (\d+)\s*$",
        flags=re.MULTILINE,
    )

    for ci, cm in enumerate(crit_matches):
        crit_num = int(cm.group(1))
        crit_title = cm.group(2).strip()
        crit_start = cm.end()
        crit_end = crit_matches[ci+1].start() if ci+1 < len(crit_matches) else len(text)
        crit_block = text[crit_start:crit_end]

        # Find indicators within this critère (and stop before "## Glossaire" if present)
        # Find indicator headers
        ind_matches = list(indicator_pattern.finditer(crit_block))
        for ii, im in enumerate(ind_matches):
            ind_num = int(im.group(1))
            ind_start = im.end()
            ind_end = ind_matches[ii+1].start() if ii+1 < len(ind_matches) else len(crit_block)
            body = crit_block[ind_start:ind_end].strip()
            # Stop at next "## " (e.g. "## Glossaire") if it sneaks in
            stop = re.search(r"^##\s", body, flags=re.MULTILINE)
            if stop:
                body = body[:stop.start()].strip()
            yield {
                "num": ind_num,
                "critere": crit_num,
                "critere_title": crit_title,
                "body": body,
            }

def extract_sections(body: str) -> dict:
    """Extract the energy (first paragraph) and labelled sections from an indicator body."""
    # The first paragraph is the énoncé (before any **section** label)
    section_pattern = re.compile(r"^\*\*([^*]+)\*\*\s*$", flags=re.MULTILINE)
    first_sec = section_pattern.search(body)
    if first_sec:
        enonce = body[:first_sec.start()].strip()
        rest = body[first_sec.start():]
    else:
        enonce, rest = body, ""

    sections = {"_enonce": enonce}
    # Split rest by section headers
    parts = section_pattern.split(rest)
    # parts = [pre, name1, body1, name2, body2, ...]
    for i in range(1, len(parts), 2):
        name = parts[i].strip()
        sec_body = parts[i+1].strip() if i+1 < len(parts) else ""
        sections[name] = sec_body
    return sections

# --- rendering ------------------------------------------------------------

def render_file(meta: dict, sections: dict) -> str:
    """Render a single indicator file with YAML front-matter."""
    n = meta["num"]
    slug = SLUGS[n]
    has_sous_traitance = bool(sections.get("Sous-traitance"))
    ponderation = "mineure ou majeure" if n in GRADUATED_INDICATORS else "majeure uniquement"
    nouveaux_entrants = "oui" if n in NOUVEAUX_ENTRANTS else "non"

    # YAML front-matter
    front = [
        "---",
        f"indicateur: {n}",
        f"critere: {meta['critere']}",
        f'critere_titre: "{meta["critere_title"]}"',
        f"slug: {slug}",
        f"ponderation: {ponderation}",
        f"nouveaux_entrants: {nouveaux_entrants}",
        f'sous_traitance: {"applicable" if has_sous_traitance else "non concerne"}',
        f'source: "{SOURCE_NOTE}"',
        "---",
        "",
    ]

    out = front[:]
    out.append(f"# Indicateur {n}")
    out.append("")
    out.append(f"> Critère {meta['critere']} — {meta['critere_title']}")
    out.append("")
    out.append("## Énoncé")
    out.append("")
    out.append(sections.get("_enonce", "").strip())
    out.append("")

    section_order = [
        "Niveau attendu",
        "Exemples de preuves",
        "Non-conformité",
        "Obligations spécifiques",
        "Sous-traitance",
    ]
    for name in section_order:
        if sections.get(name):
            out.append(f"## {name}")
            out.append("")
            out.append(sections[name].strip())
            out.append("")

    return "\n".join(out).rstrip() + "\n"

def render_index(indicators: list) -> str:
    """Render the INDEX.md grouped by critère."""
    out = []
    out.append("# Index des 32 indicateurs Qualiopi V9")
    out.append("")
    out.append("> Référentiel national qualité — Guide de lecture V9 du 8 janvier 2024.")
    out.append("> Chaque indicateur est dans son propre fichier, prêt à être indexé en RAG.")
    out.append("")
    out.append(f"**Source officielle** : [travail-emploi.gouv.fr](https://travail-emploi.gouv.fr/referentiel-national-qualite-guide-de-lecture-qualiopi)")
    out.append("")
    out.append("**Légende** :")
    out.append("- ⚖️ = pondération mineure ou majeure possible")
    out.append("- 🆕 = modalités d'audit adaptées pour les nouveaux entrants")
    out.append("- 🤝 = section Sous-traitance applicable")
    out.append("")

    # Group by critère
    by_crit = {}
    for ind in indicators:
        by_crit.setdefault(ind["critere"], []).append(ind)

    for crit_num in sorted(by_crit):
        first = by_crit[crit_num][0]
        out.append(f"## Critère {crit_num} — {first['critere_title']}")
        out.append("")
        for ind in sorted(by_crit[crit_num], key=lambda i: i["num"]):
            n = ind["num"]
            slug = SLUGS[n]
            badges = []
            if n in GRADUATED_INDICATORS:
                badges.append("⚖️")
            if n in NOUVEAUX_ENTRANTS:
                badges.append("🆕")
            if ind.get("_has_sous_traitance"):
                badges.append("🤝")
            badge_str = " " + " ".join(badges) if badges else ""
            # Short énoncé (first sentence, truncated)
            enonce = ind.get("_enonce", "").split(".")[0].strip()
            if len(enonce) > 140:
                enonce = enonce[:137] + "…"
            out.append(f"- **[Indicateur {n}]({n:02d}-{slug}.md)** — {enonce}.{badge_str}")
        out.append("")
    return "\n".join(out)

# --- main -----------------------------------------------------------------

def main():
    text = SOURCE.read_text(encoding="utf-8")
    OUT_DIR.mkdir(exist_ok=True)

    # Ignore everything from the Glossaire onwards (its "### Indicateur N"
    # headers would otherwise be parsed as new fiches).
    gloss = re.search(r"^## Glossaire\b", text, flags=re.MULTILINE)
    if gloss:
        text = text[:gloss.start()]

    indicators = list(parse_complete_md(text))
    assert len(indicators) == 32, f"Expected 32 indicators, got {len(indicators)}"

    enriched = []
    for meta in indicators:
        sections = extract_sections(meta["body"])
        meta["_enonce"] = sections.get("_enonce", "")
        meta["_has_sous_traitance"] = bool(sections.get("Sous-traitance"))
        enriched.append(meta)

        n = meta["num"]
        slug = SLUGS[n]
        filename = f"{n:02d}-{slug}.md"
        path = OUT_DIR / filename
        path.write_text(render_file(meta, sections), encoding="utf-8")
        print(f"  wrote {filename}")

    # INDEX
    index_path = OUT_DIR / "INDEX.md"
    index_path.write_text(render_index(enriched), encoding="utf-8")
    print(f"\nWrote INDEX.md")

    # Sanity report
    print(f"\nTotal files: {len(indicators) + 1}")
    print(f"Output dir: {OUT_DIR}")

if __name__ == "__main__":
    main()
