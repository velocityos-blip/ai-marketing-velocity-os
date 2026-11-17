"""VOS-owned marketing workflows, shared by the library and campaign agents."""
import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "skills"
DEFAULTS = {"CMO":"product-marketing", "Digital Marketing":"content-strategy",
            "Content":"social", "Analyst":"analytics"}


@lru_cache(maxsize=1)
def catalog():
    result = {}
    for path in sorted(ROOT.glob("*/SKILL.md")):
        _, fields, body = path.read_text(encoding="utf-8").split("---", 2)
        meta = dict(line.split(": ", 1) for line in fields.strip().splitlines())
        sections = re.split(r"^## (?:Method|Deliverable|Review)\s*$", body.strip(), flags=re.M)
        title, method, deliverable, review = [part.strip() for part in sections]
        slug = meta["name"]
        if slug != path.parent.name or meta["role"] not in DEFAULTS:
            raise ValueError(f"Invalid playbook: {path}")
        result[slug] = dict(slug=slug, title=title.removeprefix("# "), role=meta["role"], collection=meta.get("collection","Marketing"),
                            terms=[term.strip().lower() for term in meta["triggers"].split(",")],
                            method=method, deliverable=deliverable, review=review)
    return result


def select(role, brief):
    library = catalog()
    if brief.get("assignment"):
        return library[brief["assignment"]["skill"]]
    if brief.get("skill"):
        return library[brief["skill"]]
    text = " ".join(str(brief.get(k, "")) for k in ("goal","offer","audience")).lower()
    def score(skill):
        return sum(len(term.split()) for term in skill["terms"]
                   if re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", text))
    choices = [s for s in library.values() if s["role"] == role]
    best = max(choices, key=score)
    return best if score(best) else library[DEFAULTS[role]]
