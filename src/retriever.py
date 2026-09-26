"""Recherche lexicale BM25 adaptée au français (accents, mots vides, racinisation)
+ détection des références explicites (« article 33 du RGPD »)."""
from __future__ import annotations

import re
import unicodedata

import snowballstemmer
from rank_bm25 import BM25Okapi

from ingest import Passage

_STEM = snowballstemmer.stemmer("french")
MOTS_VIDES = set("""
a au aux avec ce ces cet cette dans de des du elle en et eux il ils je la le les leur leurs lui ma mais me
meme mes moi mon ne nos notre nous on ou par pas pour qu que qui sa se ses son sur ta te tes toi ton tu un une
vos votre vous c d j l m n s t y est sont ete etre avoir a ont fait faire quel quelle quels quelles
comment quoi dont doit doivent peut peuvent tout tous toute toutes plus moins si ainsi lorsque selon
article articles paragraphe presente present reglement
""".split())


def normaliser(texte: str) -> list[str]:
    t = unicodedata.normalize("NFKD", texte.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    mots = re.findall(r"[a-z0-9]+", t)
    return _STEM.stemWords([m for m in mots if m not in MOTS_VIDES and len(m) > 1])


RE_REF = re.compile(r"article\s+([lrd]?\s?\d+[\d\-]*)\s*(?:du|de la|de l'|des|de)?\s*([a-z]+)?", re.I)


class Recherche:
    def __init__(self, passages: list[Passage]):
        if not passages:
            raise ValueError("Aucun passage à indexer : le corpus est vide ou n'a pas pu être découpé.")
        self.passages = passages
        docs = [normaliser(f"{p.titre} {p.titre} {p.contenu}") for p in passages]
        self.bm25 = BM25Okapi(docs, k1=1.4, b=0.6)
        self.textes = sorted({p.texte for p in passages})

    def references_explicites(self, question: str) -> set[tuple[str | None, str]]:
        refs = set()
        for num, texte in RE_REF.findall(question):
            code = texte.upper() if texte and texte.upper() in self.textes else None
            refs.add((code, num.replace(" ", "").upper()))
        return refs

    def chercher(self, question: str, k: int = 6, textes: list[str] | None = None) -> list[tuple[Passage, float]]:
        scores = self.bm25.get_scores(normaliser(question))
        refs = self.references_explicites(question)
        resultats = []
        for p, s in zip(self.passages, scores):
            if textes and p.texte not in textes:
                continue
            for code, num in refs:  # une référence explicite passe en tête
                if p.article.upper() == num and (code is None or code == p.texte):
                    s += 100
            resultats.append((p, float(s)))
        resultats.sort(key=lambda x: -x[1])
        return [r for r in resultats[:k] if r[1] > 0]
