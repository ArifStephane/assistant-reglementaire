"""Accès à plusieurs fournisseurs de LLM via une interface unique.

Configuration par variables d'environnement (voir .env.example) :
  LLM_PROVIDER = none | anthropic | mistral | openai | ollama
  LLM_MODEL    = nom du modèle chez le fournisseur choisi
  ANTHROPIC_API_KEY / MISTRAL_API_KEY / OPENAI_API_KEY
  OLLAMA_URL   = http://localhost:11434 (par défaut)
"""
from __future__ import annotations

import os

import requests

MODELES_PAR_DEFAUT = {"mistral": "mistral-small-latest", "ollama": "llama3.1"}


class ErreurLLM(RuntimeError):
    pass


def fournisseur() -> str:
    return os.getenv("LLM_PROVIDER", "none").lower()


def modele() -> str:
    return os.getenv("LLM_MODEL") or MODELES_PAR_DEFAUT.get(fournisseur(), "")


def generer(systeme: str, message: str, temperature: float = 0.0, max_tokens: int = 1200) -> str:
    f, m = fournisseur(), modele()
    if f == "none":
        raise ErreurLLM("Aucun LLM configuré (LLM_PROVIDER=none).")
    if not m:
        raise ErreurLLM(f"Précise le modèle à utiliser avec LLM_MODEL pour le fournisseur « {f} ».")
    try:
        if f == "anthropic":
            r = requests.post("https://api.anthropic.com/v1/messages", timeout=120, headers={
                "x-api-key": _cle("ANTHROPIC_API_KEY"), "anthropic-version": "2023-06-01",
                "content-type": "application/json"},
                json={"model": m, "max_tokens": max_tokens, "temperature": temperature, "system": systeme,
                      "messages": [{"role": "user", "content": message}]})
            r.raise_for_status()
            return "".join(b.get("text", "") for b in r.json()["content"])

        urls = {"mistral": "https://api.mistral.ai/v1", "openai": "https://api.openai.com/v1",
                "ollama": os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/") + "/v1"}
        if f not in urls:
            raise ErreurLLM(f"Fournisseur inconnu : {f}")
        entetes = {"content-type": "application/json"}
        if f != "ollama":
            entetes["authorization"] = f"Bearer {_cle(f.upper() + '_API_KEY')}"
        r = requests.post(f"{urls[f]}/chat/completions", timeout=180, headers=entetes, json={
            "model": m, "temperature": temperature, "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": systeme}, {"role": "user", "content": message}]})
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except requests.RequestException as e:
        detail = getattr(e.response, "text", "")[:300] if getattr(e, "response", None) is not None else ""
        raise ErreurLLM(f"Appel au LLM ({f}) impossible : {e} {detail}") from e


def _cle(nom: str) -> str:
    v = os.getenv(nom)
    if not v:
        raise ErreurLLM(f"Variable d'environnement {nom} manquante.")
    return v
