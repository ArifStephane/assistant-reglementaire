import shutil
import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "src"))

import assistant as A  # noqa: E402
import llm  # noqa: E402
from ingest import construire_index  # noqa: E402
from retriever import Recherche  # noqa: E402


@pytest.fixture(scope="module")
def passages(tmp_path_factory):
    d = tmp_path_factory.mktemp("corpus")
    for f in (RACINE / "tests" / "fixtures").iterdir():
        shutil.copy(f, d / f.name)
    return construire_index(d, d / "passages.jsonl")


def test_parsing_formats_eurlex_et_texte(passages):
    refs = {(p.texte, p.article) for p in passages}
    assert refs == {("TEST_OJ", "1"), ("TEST_OJ", "2"), ("TEST_OLD", "7"), ("TEST_OLD", "8"),
                    ("TEST_CMF", "L561-15"), ("TEST_CMF", "L561-12"), ("TEST_NAV", "3")}
    art2 = next(p for p in passages if p.article == "2")
    assert art2.titre == "Notification des incidents"
    assert "quatre heures" in art2.contenu and "annexe" not in art2.contenu.lower()
    assert not any("considérant" in p.contenu for p in passages)


def test_recherche_semantique_et_reference_explicite(passages):
    r = Recherche(passages)
    assert r.chercher("délai pour notifier un incident majeur")[0][0].article == "2"
    assert r.chercher("combien de temps conserver les documents d'identité des clients")[0][0].article == "L561-12"
    assert r.chercher("que dit l'article 8 ?")[0][0].article == "8"


def test_mode_recherche_sans_llm(passages, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "none")
    rep = A.Assistant(passages).repondre("notification d'un incident majeur")
    assert rep.mode == "recherche" and "[1]" in rep.texte


def test_verification_des_citations(passages, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mistral")
    monkeypatch.setattr(llm, "generer", lambda s, m, **k: "Délai de quatre heures [1]. Voir aussi [9].")
    rep = A.Assistant(passages).repondre("notification d'un incident majeur", k=3)
    assert rep.mode == "llm"
    assert any("inexistantes" in a for a in rep.avertissements)


def test_bascule_si_llm_indisponible(passages, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("LLM_MODEL", "x")
    rep = A.Assistant(passages).repondre("registre des traitements")
    assert rep.mode == "recherche" and "indisponible" in rep.avertissements[0]


def test_corpus_vide(tmp_path):
    (tmp_path / ".gitkeep").write_text("")
    assert construire_index(tmp_path, tmp_path / "p.jsonl") == []
    with pytest.raises(ValueError):
        Recherche([])
