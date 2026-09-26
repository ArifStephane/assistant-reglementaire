"""Découpe les textes réglementaires en passages « un article = une unité »,
avec leurs métadonnées (texte, numéro et titre d'article, lien)."""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from bs4 import BeautifulSoup

from sources import TEXTES_EURLEX, url_eurlex

TAILLE_MAX = 2200  # caractères par passage ; au-delà, l'article est subdivisé


@dataclass
class Passage:
    id: str
    texte: str          # code du texte (DORA, RGPD, CMF...)
    article: str        # ex. "19", "L561-15"
    titre: str          # intitulé de l'article
    contenu: str
    url: str
    partie: int = 1

    @property
    def reference(self) -> str:
        suffixe = f" (partie {self.partie})" if self.partie > 1 else ""
        return f"{self.texte}, article {self.article}{suffixe}"


RE_NUM_ART = re.compile(r"Article\s+(premier|[A-Z]?\s?\d+[\w\-]*)", re.I)


def _num(texte: str) -> str:
    m = RE_NUM_ART.search(texte)
    if not m:
        return texte.strip()
    n = m.group(1).replace(" ", "")
    return "1" if n.lower() == "premier" else n


def _classes(tag) -> str:
    return " ".join(tag.get("class") or [])


def parser_eurlex(html: str, code: str, url: str) -> list[dict]:
    """Gère les deux formats d'EUR-Lex (classes « ti-art » et « oj-ti-art »)."""
    soup = BeautifulSoup(html, "html.parser")
    articles, courant = [], None
    for p in soup.find_all("p"):
        cls = _classes(p)
        txt = " ".join(p.get_text(" ", strip=True).split())
        if not txt:
            continue
        if re.search(r"(^|\s)(oj-)?ti-art(\s|$)", cls):
            courant = {"article": _num(txt), "titre": "", "lignes": []}
            articles.append(courant)
        elif re.search(r"(^|\s)(oj-)?sti-art(\s|$)", cls) and courant is not None and not courant["titre"]:
            courant["titre"] = txt
        elif re.search(r"doc-ti|ti-section|ti-grseq", cls):
            courant = None  # titre de chapitre ou d'annexe : fin de l'article en cours
        elif courant is not None:
            courant["lignes"].append(txt)
    return [{"texte": code, "url": url, "article": a["article"], "titre": a["titre"],
             "contenu": "\n".join(a["lignes"])} for a in articles if a["lignes"]]


RE_ART_TEXTE = re.compile(r"^[ \t]*Article[ \t]+((?:premier)|(?:[LRD]\.?[ \t]?)?\d+[\d\-]*)\b[ \t]*[:.\-–]?[ \t]*([^\n]*)$",
                          re.M)


def parser_texte_brut(txt: str, code: str, url: str = "") -> list[dict]:
    """Pour les PDF / .txt (ex. Code monétaire et financier exporté de Légifrance)."""
    positions = list(RE_ART_TEXTE.finditer(txt))
    out = []
    for i, m in enumerate(positions):
        fin = positions[i + 1].start() if i + 1 < len(positions) else len(txt)
        corps = txt[m.end():fin].strip()
        if len(corps) < 40:
            continue
        num = m.group(1).replace(" ", "").replace(".", "")
        out.append({"texte": code, "url": url, "article": "1" if num.lower() == "premier" else num,
                    "titre": m.group(2).strip()[:120], "contenu": " ".join(corps.split())})
    return out


def lire_pdf(chemin: Path) -> str:
    from pypdf import PdfReader
    return "\n".join((p.extract_text() or "") for p in PdfReader(str(chemin)).pages)


def decouper(article: dict) -> list[Passage]:
    base_id = f"{article['texte']}-{article['article']}"
    contenu = article["contenu"]
    if len(contenu) <= TAILLE_MAX:
        morceaux = [contenu]
    else:  # on coupe aux paragraphes, sans casser une phrase
        paras, morceaux, buf = re.split(r"\n+|(?<=[.;:])\s+(?=\d+\.\s)", contenu), [], ""
        for para in paras:
            if len(buf) + len(para) > TAILLE_MAX and buf:
                morceaux.append(buf.strip()); buf = ""
            buf += para + "\n"
        if buf.strip():
            morceaux.append(buf.strip())
    return [Passage(id=f"{base_id}#{i + 1}", texte=article["texte"], article=article["article"],
                    titre=article["titre"], contenu=m, url=article["url"], partie=i + 1)
            for i, m in enumerate(morceaux)]


EXTENSIONS = {".html", ".htm", ".pdf", ".txt", ".md"}


def fichiers_corpus(dossier: Path) -> list[Path]:
    return sorted(f for f in dossier.iterdir() if f.suffix.lower() in EXTENSIONS and not f.name.startswith("."))


def construire_index(dossier_corpus: Path, fichier_sortie: Path) -> list[Passage]:
    passages: list[Passage] = []
    for f in fichiers_corpus(dossier_corpus):
        code = f.stem.upper()
        info = TEXTES_EURLEX.get(code)
        url = url_eurlex(info["celex"]) if info else ""
        if f.suffix.lower() in {".html", ".htm"}:
            html = f.read_text(encoding="utf-8", errors="ignore")
            arts = parser_eurlex(html, code, url)
            if not arts:  # page enregistrée depuis un navigateur ou format EUR-Lex modifié
                arts = parser_texte_brut(BeautifulSoup(html, "html.parser").get_text("\n"), code, url)
        elif f.suffix.lower() == ".pdf":
            arts = parser_texte_brut(lire_pdf(f), code, url)
        elif f.suffix.lower() in {".txt", ".md"}:
            arts = parser_texte_brut(f.read_text(encoding="utf-8", errors="ignore"), code, url)
        else:
            continue
        print(f"  {f.name}: {len(arts)} articles" + ("  ⚠️ aucun article reconnu : vérifie le contenu du fichier" if not arts else ""))
        for a in arts:
            passages.extend(decouper(a))
    fichier_sortie.parent.mkdir(exist_ok=True, parents=True)
    with fichier_sortie.open("w", encoding="utf-8") as out:
        for p in passages:
            out.write(json.dumps(asdict(p), ensure_ascii=False) + "\n")
    return passages


def charger_index(fichier: Path) -> list[Passage]:
    with fichier.open(encoding="utf-8") as f:
        return [Passage(**json.loads(l)) for l in f if l.strip()]


if __name__ == "__main__":
    racine = Path(__file__).resolve().parents[1]
    ps = construire_index(racine / "corpus", racine / "index" / "passages.jsonl")
    print(f"{len(ps)} passages indexés -> index/passages.jsonl")
