# 🎯 Référentiel National Qualité (Qualiopi V10) en Markdown

Conversion open source du **Guide de lecture du Référentiel national qualité — Version 10 de novembre 2026** (Ministère du Travail et des Solidarités / DGEFP) en Markdown propre, structuré et prêt à indexer.

La V10 est en vigueur depuis le **1er novembre 2026** (décret n° 2026-728 du 1er août 2026). Elle compte **33 indicateurs** (contre 32 en V9). 👉 **[Ce qui change entre la V9 et la V10](NOUVEAUTES_V10.md)**

Maintenu par **[Levier IA](https://levier-ia.fr/)**, le centre de formation "AI-first".

> 🚀 **Vous voulez la même chose pour votre OF ?** [Réservez un diagnostic IA gratuit](https://cal.com/yoann-levier-ia/diagnostic-ia) — on audite votre conformité Qualiopi + AI Act en 45 min.

## 📦 Ce que contient le dépôt

```
qualiopi-markdown/
├── guide_de_lecture_qualiopi_v10_novembre_2026.md   # Document complet V10 en un fichier
├── NOUVEAUTES_V10.md                                # Synthèse des changements V9 → V10
├── indicateurs/
│   ├── INDEX.md                                     # Sommaire des 33 indicateurs
│   ├── 01-information-publique.md
│   ├── …
│   └── 33-evaluation-contenus-enseignements.md
├── v9/                                              # Archive de la version 9 (8 janvier 2024)
└── _scripts/                                        # Pipeline Python de conversion (pymupdf)
```

- **1 fichier global** pour la lecture humaine ou l'export.
- **33 fichiers** (un par indicateur) avec front-matter YAML pour le RAG, l'embedding, l'indexation dans un wiki ou un assistant LLM.
- **INDEX.md** avec liens, badges et énoncés courts.
- Les noms de fichiers des indicateurs 1 à 32 sont identiques à ceux de la V9 : les liens existants continuent de fonctionner et pointent désormais vers la V10.

## 🤖 Pourquoi un fichier par indicateur ?

Un chunk = un indicateur. Chaque fichier contient toutes les informations liées à un seul indicateur (énoncé, niveau attendu, exemples de preuves, non-conformité, obligations spécifiques, sous-traitance, définitions du glossaire), avec un front-matter YAML exploitable pour le filtrage :

```yaml
---
indicateur: 3
critere: 1
critere_titre: "Les conditions d’information du public…"
slug: taux-obtention-certification
type: specifique            # commun | specifique
categories: [OF, CFA, VAE]  # [toutes] pour un indicateur commun
ponderation: mineure ou majeure
nouveaux_entrants: oui
sous_traitance: applicable
version: V10
source: "Guide de lecture du Référentiel national qualité — V10 de novembre 2026, DGEFP, …"
# enonce_decret: "…"       # présent quand le guide diverge du décret (ind. 9, 20, 30, 31, 32)
# editorial_note: "…"      # présent quand un nettoyage ou une incohérence est signalé
---
```

Ça permet de :
1. **Indexer en RAG** : un chunk de 200-800 tokens par indicateur, sans overlap.
2. **Filtrer par métadonnée** : « tous les indicateurs spécifiques CFA », « tous les indicateurs avec sous-traitance applicable », etc.
3. **Citer la source** depuis le LLM avec le numéro et le titre exacts.

## 🛠️ Reproduire la conversion

```bash
pip install pymupdf
# placez le PDF officiel à la racine : guide-lecture-qualiopi-v10-nov2026.pdf
python _scripts/build_markdown.py        # PDF officiel → markdown global
python _scripts/split_indicators.py      # markdown global → 33 fichiers + INDEX.md
```

Le PDF source n'est pas versionné ([source officielle](https://travail-emploi.gouv.fr/referentiel-national-qualite-guide-de-lecture-qualiopi)). `build_markdown.py` accepte aussi un chemin en argument, et `--debug` affiche le découpage de chaque page.

Les scripts de la V9 sont conservés dans `_scripts/v9/`.

## ⚠️ Avertissement légal

Ce dépôt est un outil communautaire. **Seuls le décret et le PDF officiel du Ministère du Travail font foi légalement.**

- **Source officielle** : <https://travail-emploi.gouv.fr/referentiel-national-qualite-guide-de-lecture-qualiopi>
- **Version** : V.10 de novembre 2026, en application du décret n° 2026-728 du 1er août 2026 (JORF n° 180 du 4 août 2026)
- **Licence du contenu** : [Licence Ouverte / Open Licence 2.0 (Etalab)](https://www.etalab.gouv.fr/licence-ouverte-open-licence) — conforme à la réutilisation des informations publiques françaises (article L. 321-2 du CRPA).
- **Logo Qualiopi** : son usage est strictement réservé aux organismes effectivement certifiés (arrêté du 4 juin 2021). Il n'est ni inclus ni distribué dans ce dépôt.

## 🐛 Particularités du PDF officiel

### Encadrés en image

Sur chaque fiche indicateur, l'encadré bleu (type d'indicateur et énoncé) et l'encadré gris **« Niveau attendu »** sont des **images**, pas du texte. Aucun outil d'extraction ne peut les lire, ce qui explique pourquoi la conversion V9 n'avait pas de « Niveau attendu » pour la plupart des indicateurs.

Pour la V10 :
- l'**énoncé** est repris du sommaire (texte réel) et vérifié contre le décret ;
- le **niveau attendu** et le **type d'indicateur** ont été transcrits à la main depuis le rendu des pages et relus (`_scripts/raster_v10.py`). Quand le PDF superpose du texte réel dans l'encadré, c'est ce texte qui est utilisé.

### Calques masqués

Le PDF contient à certains endroits du **texte masqué** : d'anciennes versions de paragraphes recouvertes par une forme opaque, invisibles à l'écran mais extraites par toute conversion naïve. `build_markdown.py` les détecte via l'ordre de dessin de la page et les exclut. Les fichiers concernés portent un champ `editorial_note` :

- `indicateurs/23-veille-legale-reglementaire.md` — calque reproduisant du contenu de l'indicateur 5.
- `indicateurs/26-handicap-expertise-reseau.md` — ancienne version des exemples de preuves.
- `indicateurs/31-traitement-reclamations.md` — exemples de preuves dupliqués.

### Écarts guide / décret

Pour les indicateurs **9, 20, 30, 31 et 32**, l'énoncé imprimé dans le guide diffère du décret. Le texte du guide est conservé et la rédaction du décret, qui fait foi, est ajoutée (champ `enonce_decret` + encadré ⚖️). Détail dans [NOUVEAUTES_V10.md](NOUVEAUTES_V10.md#écarts-entre-le-guide-v10-et-le-décret).

### Incohérence nouveaux entrants

Le préambule V10 retire les indicateurs **22 et 32** de la liste des indicateurs à modalités adaptées pour les nouveaux entrants, mais leurs fiches conservent une obligation « Nouveaux entrants ». Le front-matter suit le préambule (`nouveaux_entrants: non`) et signale l'incohérence dans `editorial_note`.

---

*Proposé par [Levier IA](https://levier-ia.fr/) — Accélérez vos compétences grâce à l'Intelligence Artificielle.*
