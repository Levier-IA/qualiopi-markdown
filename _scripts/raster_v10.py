"""Manual transcriptions of content that is only present as raster images in the
official V10 PDF (guide de lecture, novembre 2026).

On every indicator page, the blue "INDICATEUR …" box and the grey
"NIVEAU ATTENDU" box are bitmaps inherited from the V9 template. No text
extraction (pymupdf, pdftotext…) can see them, which is why the V9 Markdown
was missing most "Niveau attendu" sections.

These strings were transcribed by hand from renders of the PDF pages and
proofread against them. When the PDF does carry a text layer inside the box
(V10 additions overlaid on the image), `build_markdown.py` uses that text and
these transcriptions only serve as a cross-check.
"""

# Indicator type, as printed in the blue box:
#   ("commun", [])  or  ("specifique", [categories])
INDICATOR_TYPES = {
    1: ("commun", []),
    2: ("commun", []),
    3: ("specifique", ["OF", "CFA", "VAE"]),
    4: ("commun", []),
    5: ("commun", []),
    6: ("commun", []),
    7: ("specifique", ["OF", "CFA"]),
    8: ("specifique", ["OF", "CFA"]),
    9: ("commun", []),
    10: ("commun", []),
    11: ("commun", []),
    12: ("commun", []),
    13: ("specifique", ["OF", "CFA"]),
    14: ("specifique", ["CFA"]),
    15: ("specifique", ["CFA"]),
    16: ("specifique", ["OF", "CFA", "VAE"]),
    17: ("commun", []),
    18: ("commun", []),
    19: ("commun", []),
    20: ("specifique", ["CFA"]),
    21: ("commun", []),
    22: ("commun", []),
    23: ("commun", []),
    24: ("commun", []),
    25: ("commun", []),
    26: ("commun", []),
    27: ("commun", []),
    28: ("specifique", ["OF", "CFA"]),
    29: ("specifique", ["CFA"]),
    30: ("commun", []),
    31: ("commun", []),
    32: ("commun", []),
    33: ("specifique", ["CFA"]),
}

NIVEAU_ATTENDU_RASTER = {
    1: "Donner une information accessible, exhaustive sur la prestation, c’est-à-dire sur son contenu et sur l’intégralité des items mentionnés. Cette information doit être à jour.",
    2: "Donner une information chiffrée permettant de suivre les résultats de la prestation au regard des objectifs en précisant sa méthode de calcul.",
    3: "Donner au public une information accessible, exhaustive (c’est-à-dire sur l’intégralité des items mentionnés) et actualisée (informations à jour).",
    4: "Démontrer comment le besoin du bénéficiaire est analysé en fonction de la finalité de la prestation.",
    5: "Démontrer que les objectifs spécifiques à la prestation ont été définis et peuvent faire l’objet d’une évaluation.",
    6: "Démontrer que les contenus et modalités de mise en œuvre des prestations sont adaptés aux objectifs définis en fonction des bénéficiaires.",
    7: "Démontrer l’adéquation du contenu aux compétences ciblées et aux épreuves d’évaluation de la certification.",
    8: "Démontrer l’existence de procédures de positionnement et d’évaluation des acquis à l’entrée de la prestation adaptée aux publics et modalités de formations.",
    9: "Les modalités d’accueil et les conditions de déroulement de la prestation sont formalisées et diffusées.",
    10: "La prestation est adaptée aux situations et profils des bénéficiaires, lorsque l’analyse du besoin en établit la nécessité : contenus (outils et méthodes), accompagnement, suivi (durées, emplois du temps, adaptation des rythmes).",
    11: "Démontrer qu’un processus d’évaluation existe, est formalisé et mis en œuvre. Il permet d’apprécier l’atteinte des objectifs.",
    12: "Démontrer que des mesures formalisées existent et sont mises en œuvre.",
    13: "Démontrer que les principes de la pédagogie de l’alternance sont mis en œuvre, grâce à un processus formalisé d’articulation itératif des apprentissages entre le centre de formation et l’entreprise.",
    14: "Démontrer que l’accompagnement de l’apprenant est formalisé et mis en œuvre par la mise en place de projets spécifiques.",
    15: "Démontrer que les apprentis sont informés des droits et devoirs des salariés/apprentis et sur les règles applicables en matière de santé et de sécurité en milieu professionnel.",
    16: "Le prestataire respecte les exigences formelles de l’autorité de certification lorsqu’il présente des candidats à la certification qu’il propose.",
    17: "Démontrer que les locaux, les équipements, les moyens humains sont en adéquation avec les objectifs de la ou des prestation(s).",
    18: "Le prestataire identifie, selon les fonctions nécessaires aux prestations, les intervenants dont il assure la coordination.",
    19: "Démontrer que les ressources pédagogiques sont cohérentes avec les objectifs des prestations, sont disponibles et que des dispositions sont mises en place afin de permettre aux bénéficiaires de se les approprier.",
    20: "Le prestataire présente :\n\n- la liste des membres du conseil de perfectionnement, le dernier compte-rendu et/ou procès-verbal ;\n- la liste des personnes dédiées à la mobilité (nationale et internationale) et les actions mises en œuvre en faveur de la mobilité ;\n- le nom et le contact du référent handicap et les actions qu’il met en œuvre pour accompagner les publics en situation de handicap ;\n- une méthode de supervision renforcée lorsque la proportion d’heures de formation réalisées par des intervenants permanents est inférieure au seuil.",
    21: "Démontrer que les compétences requises pour réaliser les prestations ont été définies en amont et sont adaptées aux prestations.\n\nLa maîtrise de ces compétences par les intervenants est vérifiée par le prestataire.",
    22: "Démontrer la mobilisation des différents leviers de formation et de professionnalisation pour l’ensemble de son personnel.",
    23: "Démontrer la mise en place d’une veille légale et réglementaire, sa prise en compte par le prestataire et sa communication en interne.",
    24: "Démontrer la mise en place d’une veille sur les thèmes de l’indicateur et son impact éventuel sur les prestations.",
    25: "Démontrer la mise en place d’une veille sur les thèmes de l’indicateur et son impact éventuel sur les prestations.",
    26: "Démontrer l’identification d’un réseau de partenaires/experts/acteurs du champ du handicap, mobilisable par les personnels. Dans le cas d’accueil de personnes en situation de handicap, préciser les modalités de recours à ce réseau et les mesures spécifiques d’accompagnement ou d’orientation mises en œuvre.",
    27: "Démontrer les dispositions mises en place pour vérifier le respect de la conformité au présent référentiel par le sous-traitant ou le salarié porté.",
    28: "Démontrer l’existence d’un réseau de partenaires socio-économiques mobilisé tout au long de la prestation.",
    29: "Démontrer l’existence d’actions qui concourent à l’insertion professionnelle ou à la poursuite d’études.",
    30: "Démontrer la sollicitation des appréciations à une fréquence pertinente, incluant des dispositifs de relance et permettant une libre expression.",
    31: "Démontrer la mise en place de modalités de traitement des aléas, difficultés et réclamations.",
    32: "Démontrer la mise en place d’une démarche d’amélioration continue.",
    33: "Démontrer la mise en place d’un processus de recueil en continu des évaluations des contenus et enseignement dans une démarche d’amélioration continue.",
}
