"""Évalue la qualité de la recherche : l'article attendu est-il bien retrouvé ?"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from retriever import Recherche


def evaluer(recherche: Recherche, fichier: Path, k: int = 6) -> tuple[pd.DataFrame, dict]:
    lignes = []
    for l in fichier.read_text(encoding="utf-8").splitlines():
        if not l.strip():
            continue
        q = json.loads(l)
        attendus = {(t, a) for t, a in q["attendu"]}
        if not any(t in recherche.textes for t, _ in attendus):
            continue  # texte absent du corpus : question ignorée
        res = recherche.chercher(q["question"], k=k)
        rang = next((i + 1 for i, (p, _) in enumerate(res) if (p.texte, p.article) in attendus), None)
        lignes.append({"question": q["question"], "attendu": ", ".join(f"{t} art. {a}" for t, a in attendus),
                       "trouve_en_1er": res[0][0].reference if res else "-", "rang": rang})
    df = pd.DataFrame(lignes)
    if df.empty:
        return df, {}
    stats = {
        "nb_questions": len(df),
        "top1": round((df.rang == 1).mean(), 2),
        "top3": round((df.rang <= 3).mean(), 2),
        f"top{k}": round(df.rang.notna().mean(), 2),
        "mrr": round(df.rang.apply(lambda r: 1 / r if r else 0).mean(), 2),
    }
    return df, stats


if __name__ == "__main__":
    from ingest import charger_index
    racine = Path(__file__).resolve().parents[1]
    df, stats = evaluer(Recherche(charger_index(racine / "index" / "passages.jsonl")), racine / "eval" / "questions.jsonl")
    print(df.to_string(index=False))
    print(stats)
