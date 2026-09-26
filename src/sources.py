"""Textes officiels intégrés par défaut (versions françaises sur EUR-Lex)."""

TEXTES_EURLEX = {
    "DORA": {
        "celex": "32022R2554",
        "titre": "Règlement (UE) 2022/2554 sur la résilience opérationnelle numérique du secteur financier (DORA)",
    },
    "RGPD": {
        "celex": "32016R0679",
        "titre": "Règlement (UE) 2016/679 relatif à la protection des données (RGPD)",
    },
    "AMLR": {
        "celex": "32024R1624",
        "titre": "Règlement (UE) 2024/1624 relatif à la prévention de l'utilisation du système financier "
                 "aux fins du blanchiment de capitaux ou du financement du terrorisme (AMLR)",
    },
}


def url_eurlex(celex: str) -> str:
    return f"https://eur-lex.europa.eu/legal-content/FR/TXT/HTML/?uri=CELEX:{celex}"
