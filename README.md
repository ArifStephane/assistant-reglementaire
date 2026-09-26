# Assistant réglementaire (RAG) — DORA, RGPD, LCB-FT

Assistant qui répond aux questions de conformité **à partir des textes officiels uniquement** et
**cite les articles** utilisés. Il repose sur une architecture RAG (*Retrieval-Augmented Generation*) :

1. **Ingestion** : les règlements (EUR-Lex) et le droit français (PDF / texte Légifrance) sont découpés
   **article par article**, avec leurs métadonnées (texte, numéro, intitulé, lien officiel).
2. **Recherche** : BM25 adapté au français (accents, mots vides, racinisation). Une référence explicite
   (« article 33 du RGPD ») fait passer l'article demandé en tête.
3. **Génération** : un LLM rédige la réponse **uniquement** à partir des extraits numérotés, et doit citer
   chaque affirmation `[n]`.
4. **Contrôle** : l'application vérifie les citations. Une réponse sans source, ou qui cite un extrait
   inexistant, est signalée comme possible hallucination.

> Outil d'aide à la recherche : il ne remplace ni un juriste ni le responsable conformité.

## Points forts pour un usage en conformité

- **Traçabilité** : chaque réponse renvoie aux articles sources, avec un lien vers le texte officiel.
- **Plusieurs fournisseurs de LLM** : Claude (Anthropic), Mistral, OpenAI ou **Ollama en local**. Le mode
  local permet qu'aucune donnée ne sorte du poste, ce qui compte pour la confidentialité et le RGPD.
- **Mode sans LLM** : sans clé API, l'outil affiche les passages les plus pertinents. Si le LLM est
  indisponible, il bascule automatiquement sur ce mode.
- **Protection contre l'injection de prompt** : le prompt système impose de traiter les extraits comme des
  données, et jamais comme des instructions.
- **Évaluation mesurable** : un jeu de questions annotées (`eval/questions.jsonl`) mesure si le bon article
  est retrouvé (top 1, top 3, MRR).

## Installation

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python download_corpus.py      # DORA, RGPD et AMLR depuis EUR-Lex -> corpus/
python src/ingest.py           # découpage par article -> index/passages.jsonl
python src/evaluate.py         # qualité de la recherche sur les questions annotées
streamlit run app.py           # interface sur http://localhost:8501
pytest -q                      # tests
```

Si EUR-Lex bloque le téléchargement automatique, ouvre la page du texte dans ton navigateur, puis fais
« Enregistrer sous… » en HTML dans `corpus/`, sous le nom `DORA.html`, `RGPD.html` ou `AMLR.html`.

**Ajouter le droit français LCB-FT** : exporte depuis Légifrance les articles L561-1 et suivants du Code
monétaire et financier, en PDF ou en `.txt`. Place le fichier dans `corpus/CMF.pdf` : il sera découpé
automatiquement par article (`Article L561-15`, etc.).

## Configurer un LLM

Copie `.env.example` en `.env`, puis choisis un fournisseur :

```bash
LLM_PROVIDER=mistral                 # ou anthropic | openai | ollama | none
LLM_MODEL=mistral-small-latest       # nom du modèle chez ce fournisseur
MISTRAL_API_KEY=...
```

Pour du 100 % local : installe [Ollama](https://ollama.com), lance `ollama pull llama3.1`, puis
`LLM_PROVIDER=ollama`.

## Résultats

<!-- À compléter après `python src/evaluate.py` sur le corpus réel -->
| Métrique (18 questions DORA / RGPD) | Valeur |
|---|---|
| Bon article en 1re position | à compléter |
| Bon article dans le top 3 | à compléter |
| MRR | à compléter |

## Structure

```
├── app.py                 # interface Streamlit (questions + évaluation)
├── download_corpus.py     # récupération des textes EUR-Lex
├── src/
│   ├── sources.py         # textes intégrés (CELEX)
│   ├── ingest.py          # parsing EUR-Lex (2 formats), PDF, texte -> passages par article
│   ├── retriever.py       # BM25 français + références explicites
│   ├── llm.py             # Anthropic, Mistral, OpenAI, Ollama via une interface unique
│   ├── assistant.py       # prompt, génération sourcée, vérification des citations
│   └── evaluate.py        # top-k / MRR sur eval/questions.jsonl
├── eval/questions.jsonl   # questions annotées avec l'article attendu
└── tests/                 # tests sur des textes fictifs (fixtures)
```

## Limites et pistes d'amélioration

- **Recherche hybride** : ajouter des embeddings (recherche sémantique) au BM25, pour les questions formulées
  sans les mots du texte.
- **Considérants et annexes** : ils ne sont pas indexés pour l'instant (choix de précision).
- **Actes délégués** : ajouter les RTS / ITS de DORA (classification des incidents, registre d'informations)
  et les lignes directrices de l'ACPR.
- **Versions** : suivre les versions consolidées pour garantir qu'on interroge le texte en vigueur.
- **Évaluation de la génération** : mesurer aussi la fidélité des réponses (LLM-as-a-judge + relecture
  humaine), pas seulement la recherche.

## Contexte

Projet personnel réalisé par **Stéphane Hounkpatin** (Ingénieur Cybersécurité & GRC, MSc Risk Management,
Contrôle & Compliance – INSEEC). Il sert à explorer l'usage des LLM en conformité, de façon maîtrisée et
traçable.
# assistant-reglementaire
