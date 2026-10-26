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


def texte(payload, key, limit, requis=True):
    value = payload.get(key) or ""
    if not isinstance(value, str) or len(value) > limit or (requis and not value.strip()):
        raise ValueError(f"{key}: text, {limit} characters max")
    return value.strip()


def adresse(value, key):
    if value and not re.fullmatch(r"https?://[^\s\"'<>\\]+", value):
        raise ValueError(f"{key}: expected an HTTP or HTTPS address")
    return value


def main(payload):
    titre = " ".join(texte(payload, "titre", 120).split())
    url = adresse(texte(payload, "url", 500), "url")
    par = {
        "pseudo": " ".join(texte(payload, "pseudo", 60, requis=False).split()),
        "github": re.sub(r"^(@|https?://github\.com/)", "", texte(payload, "github", 100, requis=False)).strip("/"),
        "site": adresse(texte(payload, "site_perso", 500, requis=False), "site_perso"),
    }
    if par["github"] and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}", par["github"]):
        raise ValueError("github: invalid username")
    par = "".join(f"    {key}: {json.dumps(value, ensure_ascii=False)}\n" for key, value in par.items() if value)
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
        + (f"  propose_par:\n{par}" if par else "")
        + "taxonomies:\n"
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
