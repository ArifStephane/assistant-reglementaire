"""Télécharge les textes officiels depuis EUR-Lex dans le dossier corpus/.

Usage : python download_corpus.py            (tous les textes)
        python download_corpus.py DORA RGPD  (sélection)

Pour le droit français (ex. Code monétaire et financier, articles L561-1 et
suivants sur la LCB-FT), enregistre les pages Légifrance en PDF ou en .txt dans
corpus/ : elles seront découpées automatiquement par article.
"""
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent / "src"))
from sources import TEXTES_EURLEX, url_eurlex  # noqa: E402

DOSSIER = Path(__file__).parent / "corpus"


def main(codes):
    DOSSIER.mkdir(exist_ok=True)
    for code in codes:
        info = TEXTES_EURLEX[code]
        url = url_eurlex(info["celex"])
        print(f"Téléchargement {code} ... ", end="", flush=True)
        r = requests.get(url, timeout=60, headers={"User-Agent": "assistant-reglementaire/1.0 (projet pédagogique)"})
        r.raise_for_status()
        if "ti-art" not in r.text:
            print("⚠️ contenu inattendu (page de consentement ou format modifié) — enregistre la page à la main")
            continue
        (DOSSIER / f"{code}.html").write_text(r.text, encoding="utf-8")
        print(f"ok ({len(r.text) // 1024} Ko)")
        time.sleep(1)


if __name__ == "__main__":
    main(sys.argv[1:] or list(TEXTES_EURLEX))
