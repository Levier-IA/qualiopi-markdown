"""Split the complete V10 Markdown guide into one file per indicator + INDEX.md.

Usage:
    python _scripts/split_indicators.py

Reads:  guide_de_lecture_qualiopi_v10_novembre_2026.md
Writes: indicateurs/NN-slug.md  (33 files)
        indicateurs/INDEX.md

Metadata (pondération, nouveaux entrants) is parsed from the guide's own
preamble rather than hard-coded, so it follows the source document.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "guide_de_lecture_qualiopi_v10_novembre_2026.md"
OUT_DIR = ROOT / "indicateurs"
N_INDICATORS = 33

# Slugs are kept identical to V9 for indicators 1-32 so that links survive.
SLUGS = {
    1: "information-publique",
    2: "indicateurs-resultats",
    3: "taux-obtention-certification",
    4: "analyse-besoin-beneficiaire",
    5: "objectifs-operationnels",
    6: "contenus-modalites",
    7: "adequation-contenus-certification",
    8: "positionnement-evaluation-entree",
    9: "conditions-deroulement",
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
    33: "evaluation-contenus-enseignements",
}

SOURCE_NOTE = ("Guide de lecture du Référentiel national qualité — V10 de novembre 2026, "
               "DGEFP, Ministère du Travail et des Solidarités.")

SECTION_ORDER = [
    "Précision",
    "Niveau attendu",
    "Exemples de preuves",
    "Non-conformité",
    "Obligations spécifiques",
    "Sous-traitance",
]

# Per-indicator editorial notes for known divergences from a raw extraction.
EDITORIAL_NOTES = {
    23: ("Le PDF officiel contient sous les exemples de preuves un calque masqué "
         "reproduisant du contenu de l'indicateur 5 ; il est invisible à l'écran "
         "et a été exclu de la conversion."),
    26: ("Le PDF officiel contient un calque masqué (ancienne version des exemples "
         "de preuves) ; il est invisible à l'écran et a été exclu de la conversion."),
    31: ("Le PDF officiel contient un calque masqué dupliquant les exemples de "
         "preuves ; il est invisible à l'écran et a été exclu de la conversion."),
    22: ("Incohérence du guide officiel : le préambule V10 ne cite plus cet "
         "indicateur parmi ceux à modalités adaptées pour les nouveaux entrants "
         "(champ nouveaux_entrants: non), mais la fiche conserve une obligation "
         "spécifique « Nouveaux entrants »."),
    32: ("Incohérence du guide officiel : le préambule V10 ne cite plus cet "
         "indicateur parmi ceux à modalités adaptées pour les nouveaux entrants "
         "(champ nouveaux_entrants: non), mais la fiche conserve une obligation "
         "spécifique « Nouveaux entrants »."),
}

# Statements whose wording in the guide differs (beyond punctuation) from the
# legally binding text: annexe of the code du travail as amended by décret
# n° 2026-728 du 1er août 2026 (JORF n° 180 du 4 août 2026, texte 11).
DECREE_WORDING = {
    9: "Le prestataire informe les publics bénéficiaires sur les conditions de déroulement de la prestation.",
    20: "Le prestataire dispose d’un personnel dédié à l’appui à la mobilité nationale et internationale, d’un référent handicap et d’un conseil de perfectionnement. Il s’assure de la qualité du pilotage de la formation, de la participation des apprentis, formateurs et entreprises à sa gouvernance. Lorsque la proportion d’heures d’enseignement réalisées par des intervenants permanents est inférieure à un seuil fixé par arrêté du ministre chargé de la formation professionnelle, le prestataire s’assure de la mise en œuvre de modalités renforcées de supervision pédagogique et de contrôle de la qualité des interventions.",
    30: "Le prestataire recueille les appréciations des parties prenantes : bénéficiaires, financeurs (le cas échéant), équipes pédagogiques et entreprises concernées.",
    31: "Le prestataire met en œuvre des modalités de traitement des difficultés rencontrées par les parties prenantes, des réclamations exprimées par ces dernières ainsi que des aléas survenus en cours de prestation.",
    32: "Le prestataire met en place une démarche d’amélioration continue à partir de l’analyse des appréciations et des réclamations, ainsi qu’une analyse des risques sur la qualité des formations délivrées.",
}

# --- parsing ----------------------------------------------------------------

def parse_number_list(sentence: str) -> set:
    return {int(n) for n in re.findall(r"\d{1,2}", sentence)}


def parse_preamble_sets(text: str):
    grad = re.search(r"gradation mineure ou majeure sont les suivants :([^.]+)\.", text)
    ne = re.search(r"les indicateurs ([\d ,et]+) du référentiel font l’objet de modalités d’audit adaptées", text)
    assert grad and ne, "preamble lists not found — has the guide wording changed?"
    return parse_number_list(grad.group(1)), parse_number_list(ne.group(1))


def parse_glossary(text: str) -> dict:
    m = re.search(r"^## Glossaire\s*$(.+?)^---\s*$", text, flags=re.MULTILINE | re.DOTALL)
    out = {}
    if not m:
        return out
    parts = re.split(r"^### Indicateur (\d+)\s*$", m.group(1), flags=re.MULTILINE)
    for i in range(1, len(parts), 2):
        out[int(parts[i])] = parts[i + 1].strip()
    return out


def parse_indicators(text: str):
    body = text[:re.search(r"^## Glossaire\b", text, flags=re.MULTILINE).start()]
    crits = list(re.finditer(r"^## Critère (\d+) — (.+?)$", body, flags=re.MULTILINE))
    for ci, cm in enumerate(crits):
        block = body[cm.end(): crits[ci + 1].start() if ci + 1 < len(crits) else len(body)]
        inds = list(re.finditer(r"^### Indicateur (\d+)\s*$", block, flags=re.MULTILINE))
        for ii, im in enumerate(inds):
            yield {
                "num": int(im.group(1)),
                "critere": int(cm.group(1)),
                "critere_title": cm.group(2).strip(),
                "body": block[im.end(): inds[ii + 1].start() if ii + 1 < len(inds) else len(block)].strip(),
            }


def extract_sections(body: str) -> dict:
    """{'_type': '...', '_enonce': '...', '<Section>': '...'}"""
    sec = re.compile(r"^\*\*([^*]+)\*\*\s*$", flags=re.MULTILINE)
    first = sec.search(body)
    head = body[:first.start()].strip() if first else body
    type_m = re.match(r"^\*(Indicateur [^*]+)\*\s*\n+", head)
    out = {"_type": type_m.group(1) if type_m else "",
           "_enonce": head[type_m.end():].strip() if type_m else head}
    if first:
        parts = sec.split(body[first.start():])
        for i in range(1, len(parts), 2):
            out[parts[i].strip()] = parts[i + 1].strip()
    return out


def type_meta(type_label: str):
    m = re.search(r"\(([^)]+)\)", type_label)
    cats = [c.strip() for c in m.group(1).split(",")] if m else []
    return ("specifique" if "spécifique" in type_label else "commun"), cats

# --- rendering --------------------------------------------------------------

def yaml_str(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def render_file(meta, sections, graduated, new_entrants, glossary) -> str:
    n = meta["num"]
    kind, cats = type_meta(sections["_type"])
    front = [
        "---",
        f"indicateur: {n}",
        f"critere: {meta['critere']}",
        f"critere_titre: {yaml_str(meta['critere_title'])}",
        f"slug: {SLUGS[n]}",
        f"type: {kind}",
        f"categories: [{', '.join(cats)}]" if cats else "categories: [toutes]",
        f"ponderation: {'mineure ou majeure' if n in graduated else 'majeure uniquement'}",
        f"nouveaux_entrants: {'oui' if n in new_entrants else 'non'}",
        f"sous_traitance: {'applicable' if sections.get('Sous-traitance') else 'non concerne'}",
        "version: V10",
        f"source: {yaml_str(SOURCE_NOTE)}",
    ]
    if n in DECREE_WORDING:
        front.append(f"enonce_decret: {yaml_str(DECREE_WORDING[n])}")
    if n in EDITORIAL_NOTES:
        front.append(f"editorial_note: {yaml_str(EDITORIAL_NOTES[n])}")
    front += ["---", ""]

    out = front + [
        f"# Indicateur {n}",
        "",
        f"> Critère {meta['critere']} — {meta['critere_title']}",
        f">",
        f"> *{sections['_type']}*",
        "",
        "## Énoncé",
        "",
        sections["_enonce"],
        "",
    ]
    if n in DECREE_WORDING:
        out += [
            "> ⚖️ **Rédaction du décret n° 2026-728** (texte qui fait foi, différent du guide) :",
            f"> {DECREE_WORDING[n]}",
            "",
        ]
    for name in SECTION_ORDER:
        if sections.get(name):
            out += [f"## {name}", "", sections[name], ""]
    if glossary.get(n):
        out += ["## Glossaire", "", glossary[n], ""]
    return "\n".join(out).rstrip() + "\n"


def short_statement(enonce: str) -> str:
    first = re.split(r"(?<=\.)\s", enonce, maxsplit=1)[0].rstrip(".")
    return first if len(first) <= 140 else first[:137].rstrip() + "…"


def render_index(indicators, graduated, new_entrants) -> str:
    out = [
        f"# Index des {N_INDICATORS} indicateurs Qualiopi V10",
        "",
        "> Référentiel national qualité — Guide de lecture V10 de novembre 2026 (en vigueur au 1er novembre 2026).",
        "> Chaque indicateur est dans son propre fichier, prêt à être indexé en RAG.",
        "",
        "**Source officielle** : [travail-emploi.gouv.fr](https://travail-emploi.gouv.fr/referentiel-national-qualite-guide-de-lecture-qualiopi)",
        "",
        "**Légende** :",
        "- 🎯 = indicateur spécifique (catégories concernées entre parenthèses)",
        "- ⚖️ = pondération mineure ou majeure possible",
        "- 🆕 = modalités d'audit adaptées pour les nouveaux entrants",
        "- 🤝 = section Sous-traitance applicable",
        "",
    ]
    by_crit = {}
    for ind in indicators:
        by_crit.setdefault(ind["critere"], []).append(ind)
    for crit in sorted(by_crit):
        out += [f"## Critère {crit} — {by_crit[crit][0]['critere_title']}", ""]
        for ind in sorted(by_crit[crit], key=lambda i: i["num"]):
            n = ind["num"]
            kind, cats = type_meta(ind["_sections"]["_type"])
            badges = []
            if kind == "specifique":
                badges.append(f"🎯 ({', '.join(cats)})")
            if n in graduated:
                badges.append("⚖️")
            if n in new_entrants:
                badges.append("🆕")
            if ind["_sections"].get("Sous-traitance"):
                badges.append("🤝")
            badge_str = (" " + " ".join(badges)) if badges else ""
            short = short_statement(ind["_sections"]["_enonce"])
            short += "" if short.endswith("…") else "."
            out.append(f"- **[Indicateur {n}]({n:02d}-{SLUGS[n]}.md)** — {short}{badge_str}")
        out.append("")
    return "\n".join(out)


def main():
    text = SOURCE.read_text(encoding="utf-8")
    graduated, new_entrants = parse_preamble_sets(text)
    glossary = parse_glossary(text)
    indicators = list(parse_indicators(text))
    assert [i["num"] for i in indicators] == list(range(1, N_INDICATORS + 1)), \
        f"expected indicators 1..{N_INDICATORS}"

    OUT_DIR.mkdir(exist_ok=True)
    for old in OUT_DIR.glob("[0-9][0-9]-*.md"):
        old.unlink()
    for ind in indicators:
        ind["_sections"] = extract_sections(ind["body"])
        path = OUT_DIR / f"{ind['num']:02d}-{SLUGS[ind['num']]}.md"
        path.write_text(render_file(ind, ind["_sections"], graduated, new_entrants, glossary),
                        encoding="utf-8")
    (OUT_DIR / "INDEX.md").write_text(render_index(indicators, graduated, new_entrants),
                                      encoding="utf-8")
    print(f"Wrote {len(indicators)} indicator files + INDEX.md to {OUT_DIR}")
    print(f"  pondération mineure/majeure: {sorted(graduated)}")
    print(f"  nouveaux entrants:           {sorted(new_entrants)}")


if __name__ == "__main__":
    main()
