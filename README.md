# 🎯 Référentiel National Qualité (Qualiopi V9) en Markdown

Conversion open source du **Guide de lecture du Référentiel national qualité — Version 9 du 8 janvier 2024** (Ministère du Travail / DGEFP) en Markdown propre, structuré et prêt à indexer.

Maintenu par **[Levier IA](https://levier-ia.fr/)**, le centre de formation "AI-first".

## 📦 Ce que contient le dépôt

```
qualiopi-markdown/
├── guide_de_lecture_qualiopi_v9_du_8_janvier_2024.md   # Document complet en un fichier
├── indicateurs/
│   ├── INDEX.md                                        # Sommaire des 32 indicateurs
│   ├── 01-information-publique.md
│   ├── 02-indicateurs-resultats.md
│   ├── …
│   └── 32-mesures-amelioration.md
└── _scripts/                                           # Pipeline Python de conversion (pymupdf)
```

- **1 fichier global** pour la lecture humaine ou l'export.
- **32 fichiers** (un par indicateur) avec front-matter YAML pour le RAG, l'embedding, l'indexation dans un wiki ou un assistant LLM.
- **INDEX.md** avec liens, badges et énoncés courts.

## 🤖 Pourquoi un fichier par indicateur ?

Un chunk = un indicateur. Chaque fichier contient toutes les informations liées à un seul indicateur (énoncé, niveau attendu, exemples de preuves, non-conformité, obligations spécifiques, sous-traitance), avec un front-matter YAML exploitable pour le filtrage :

```yaml
---
indicateur: 2
critere: 1
critere_titre: "Les conditions d'information du public…"
slug: indicateurs-resultats
ponderation: mineure ou majeure
nouveaux_entrants: oui
sous_traitance: applicable
source: "Guide de lecture du Référentiel national qualité — V9 du 8 janvier 2024, DGEFP, Ministère du Travail."
---
```

Ça permet de :
1. **Indexer en RAG** : un chunk de 200-800 tokens par indicateur, sans overlap.
2. **Filtrer par métadonnée** : « tous les indicateurs avec sous-traitance applicable », « tous les indicateurs pondérés mineure ou majeure », etc.
3. **Citer la source** depuis le LLM avec le numéro et le titre exacts.

## 🛠️ Reproduire la conversion

```bash
pip install pymupdf
python _scripts/build_markdown.py        # PDF officiel → markdown global
python _scripts/split_indicators.py      # markdown global → 32 fichiers + INDEX.md
```

Le PDF source n'est pas versionné ([source officielle](https://travail-emploi.gouv.fr/referentiel-national-qualite-guide-de-lecture-qualiopi)) — placez-le à la racine pour rejouer le pipeline.

## ⚠️ Avertissement légal

Ce dépôt est un outil communautaire. **Seul le PDF officiel du Ministère du Travail fait foi légalement.**

- **Source officielle** : <https://travail-emploi.gouv.fr/referentiel-national-qualite-guide-de-lecture-qualiopi>
- **Version** : V.9 du 08/01/2024 (intégrant les évolutions sous-traitance)
- **Licence du contenu** : [Licence Ouverte / Open Licence 2.0 (Etalab)](https://www.etalab.gouv.fr/licence-ouverte-open-licence) — conforme à la réutilisation des informations publiques françaises (article L. 321-2 du CRPA).
- **Logo Qualiopi** : son usage est strictement réservé aux organismes effectivement certifiés (arrêté du 4 juin 2021). Il n'est ni inclus ni distribué dans ce dépôt.

## 🐛 Particularités du PDF officiel — nettoyages éditoriaux

Le PDF officiel du Ministère contient à certains endroits des **calques résiduels** : du texte d'un indicateur réapparaît sur la fiche d'un autre indicateur. Ce sont des bugs de mise en page du document source, invisibles à l'œil nu mais extraits par toute conversion automatique.

Quand une telle pollution a été détectée, elle a été **retirée manuellement** et le fichier concerné porte un champ `editorial_note` dans son front-matter YAML pour le signaler explicitement :

- `indicateurs/23-veille-legale-reglementaire.md` — 2 paragraphes parasites de l'indicateur 5 retirés.

Le mécanisme est documenté dans `_scripts/split_indicators.py` (dict `EDITORIAL_NOTES`).

---

*Proposé par [Levier IA](https://levier-ia.fr/) — Accélérez vos compétences grâce à l'Intelligence Artificielle.*
