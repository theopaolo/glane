"""Write a signet sent from the /proposer/ form, for the proposition workflow."""

import json
import os
import re
import sys
import tomllib
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIGNETS = ROOT / "content/signets"
CATEGORIES = set(tomllib.loads((ROOT / "config.toml").read_text())["extra"]["categories"]) - {"francophone"}


def slug(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60].strip("-")


def cle(url):
    return re.sub(r"^https?://(www\.)?", "", url.strip().lower()).rstrip("/")


def texte(payload, key, limit):
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"{key}: required text, {limit} characters max")
    return value.strip()


def main(payload):
    titre = " ".join(texte(payload, "titre", 120).split())
    url = texte(payload, "url", 500)
    if not re.fullmatch(r"https?://[^\s\"'<>\\]+", url):
        raise ValueError("url: expected an HTTP or HTTPS address")
    # Pas de HTML brut dans la fiche : Zola le rendrait tel quel.
    description = texte(payload, "description", 2000).replace("\r\n", "\n").replace("<", "&lt;")
    categorie = payload.get("categorie")
    if categorie not in CATEGORIES:
        raise ValueError("categorie: unknown category")
    categories = [categorie, "francophone"] if payload.get("francophone") is True else [categorie]
    tags = payload.get("tags")
    if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
        raise ValueError("tags: expected a list of strings")
    tags = list(dict.fromkeys(filter(None, map(slug, tags))))

    for fiche in SIGNETS.glob("*.md"):
        existing = re.search(r"(?m)^  url:\s*[\"']?(https?://[^\s\"']+)", fiche.read_text())
        if existing and cle(existing.group(1)) == cle(url):
            raise ValueError(f"url: already in {fiche.name}")

    nom = slug(titre) or "signet"
    fiche, n = SIGNETS / f"{nom}.md", 2
    while fiche.exists():
        fiche, n = SIGNETS / f"{nom}-{n}.md", n + 1
    fiche.write_text(
        "---\n"
        f"title: {json.dumps(titre, ensure_ascii=False)}\n"
        "extra:\n"
        f"  url: {json.dumps(url)}\n"
        "taxonomies:\n"
        f"  category: [{', '.join(categories)}]\n"
        f"  tags: [{', '.join(map(json.dumps, tags))}]\n"
        "---\n\n"
        f"{description}\n"
    )
    # Lignes lues par le workflow dans $GITHUB_OUTPUT.
    print(f"fiche={fiche.relative_to(ROOT)}")
    print(f"titre={titre}")


if __name__ == "__main__":
    try:
        main(json.loads(os.environ["PAYLOAD"]))
    except (KeyError, ValueError) as error:
        sys.exit(str(error))
