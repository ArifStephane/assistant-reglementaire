"""Assistant réglementaire (RAG) — lancer : streamlit run app.py"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st

RACINE = Path(__file__).resolve().parent
sys.path.insert(0, str(RACINE / "src"))

try:  # chargement facultatif du fichier .env
    from dotenv import load_dotenv
    load_dotenv(RACINE / ".env")
except ImportError:
    pass

import llm  # noqa: E402
from assistant import Assistant  # noqa: E402
from evaluate import evaluer  # noqa: E402
from ingest import charger_index, construire_index, fichiers_corpus  # noqa: E402

INDEX = RACINE / "index" / "passages.jsonl"
EXEMPLES = [
    "Dans quel délai notifier un incident majeur lié aux TIC ?",
    "Que doit prévoir un contrat avec un prestataire cloud selon DORA ?",
    "Quand une analyse d'impact (AIPD) est-elle obligatoire ?",
    "Quelles mesures de vigilance renforcée envers un client à risque élevé ?",
]

st.set_page_config(page_title="Assistant réglementaire", page_icon="⚖️", layout="wide")


@st.cache_resource
def charger_assistant():
    if not INDEX.exists():
        construire_index(RACINE / "corpus", INDEX)
    passages = charger_index(INDEX)
    if not passages:
        INDEX.unlink(missing_ok=True)  # ne pas garder un index vide en cache
        return None, []
    return Assistant(passages), passages


fichiers = fichiers_corpus(RACINE / "corpus")
if not fichiers:
    st.error("Le dossier `corpus/` ne contient aucun texte (HTML, PDF ou TXT). En local : lance "
             "`python download_corpus.py`. En ligne : vérifie que les fichiers `corpus/*.html` sont bien "
             "envoyés sur GitHub (`git add corpus/*.html`).")
    st.stop()

assistant, passages = charger_assistant()
if assistant is None:
    st.error("Aucun article n'a pu être extrait des fichiers du corpus : "
             + ", ".join(f"`{f.name}` ({f.stat().st_size // 1024} Ko)" for f in fichiers)
             + ". Un fichier de quelques Ko est souvent une page d'erreur ou de vérification d'EUR-Lex au lieu du "
               "texte : ouvre-le pour vérifier, puis enregistre la page du règlement depuis ton navigateur.")
    st.stop()

with st.sidebar:
    st.header("⚙️ Réglages")
    st.markdown(f"**LLM** : `{llm.fournisseur()}` {('— ' + llm.modele()) if llm.modele() else ''}")
    if llm.fournisseur() == "none":
        st.caption("Mode recherche seule. Configure LLM_PROVIDER dans .env pour des réponses rédigées.")
    textes = st.multiselect("Textes interrogés", assistant.recherche.textes, default=assistant.recherche.textes)
    k = st.slider("Nombre d'extraits transmis", 3, 10, 6)
    st.caption(f"{len(passages)} passages indexés")

st.title("⚖️ Assistant réglementaire — DORA, RGPD, LCB-FT")
st.caption("Réponses fondées uniquement sur les textes officiels indexés, avec citation des articles. "
           "Outil d'aide : ne remplace pas l'analyse d'un juriste ou du responsable conformité.")

onglet_q, onglet_eval = st.tabs(["Poser une question", "Évaluation de la recherche"])

with onglet_q:
    cols = st.columns(len(EXEMPLES))
    for c, ex in zip(cols, EXEMPLES):
        if c.button(ex, use_container_width=True):
            st.session_state["question"] = ex
    question = st.text_input("Ta question", key="question", placeholder="Ex. : quelles obligations de sauvegarde selon DORA ?")
    if question:
        with st.spinner("Recherche des articles et rédaction de la réponse…"):
            rep = assistant.repondre(question, k=k, textes=textes or None)
        for a in rep.avertissements:
            st.warning(a)
        st.markdown(rep.texte)
        st.markdown("#### Sources")
        for i, (p, score) in enumerate(rep.sources, 1):
            with st.expander(f"[{i}] {p.reference} — {p.titre}  (score {score:.1f})"):
                st.write(p.contenu)
                if p.url:
                    st.markdown(f"[Texte officiel]({p.url})")

with onglet_eval:
    st.write("Pour chaque question de `eval/questions.jsonl`, on vérifie si l'article attendu est retrouvé "
             "et à quel rang. C'est la métrique clé d'un RAG : sans le bon article, pas de bonne réponse.")
    if st.button("Lancer l'évaluation"):
        df, stats = evaluer(assistant.recherche, RACINE / "eval" / "questions.jsonl", k=k)
        if df.empty:
            st.info("Aucune question ne porte sur les textes présents dans le corpus.")
        else:
            c = st.columns(4)
            c[0].metric("Questions", stats["nb_questions"])
            c[1].metric("Bon article en 1er", f"{stats['top1']:.0%}")
            c[2].metric("Dans le top 3", f"{stats['top3']:.0%}")
            c[3].metric("MRR", stats["mrr"])
            st.dataframe(df, hide_index=True, use_container_width=True)
