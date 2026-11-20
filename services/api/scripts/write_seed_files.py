"""Write the Seed Recipe files from the product owner's recipes and the gated Claude
drafts (slice 4g, ADR 0028). Free: no API calls.

    uv run python -m scripts.write_seed_files

Reads `data/recipe-batches/clean/` (the recipes) and its `generated.json` (title, Quick
View steps, and any stage or ingredient fixes, all passed by the gate), and writes one
JSON file per batch into `app/data/recipes/`. Refuses to write if any draft isn't ok.
Only recipes with a picked photo are written (ADR 0029): the rest were removed in 4f.
"""

import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

from app.data.recipe_images import load_recipe_images
from app.data.recipes import DIR, SeedRecipe
from scripts.build_recipe_library import OUT, key, load_sources


def slugify(title: str) -> str:
    """ "Crème brûlée" → "creme-brulee"; "Shepherd's pie" → "shepherds-pie"."""
    text = title.lower().replace("'", "").replace("’", "")
    for letter, plain in {"æ": "ae", "ø": "o", "ı": "i", "ß": "ss", "œ": "oe"}.items():
        text = text.replace(letter, plain)
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")


def seed_from(source: dict[str, Any], draft: dict[str, Any]) -> SeedRecipe:
    title = draft["title"]
    return SeedRecipe.model_validate(
        {
            **{k: source[k] for k in ("course", "servings", "summary")},
            "cuisine": source["cuisine"].replace(" ", "-"),  # "middle-eastern", as before
            **{k: source[k] for k in ("prep_minutes", "cook_minutes", "difficulty")},
            "slug": slugify(title),
            "title": title,
            "ingredients": draft.get("ingredients") or source["ingredients"],
            "method": draft["quick_steps"],
            "stages": draft.get("stages") or source["stages"],
            "tips": source["tips"],
            "variations": source["variations"],
            "storage": source["storage"],
        }
    )


def main(out_dir: Path = DIR) -> int:
    drafts: dict[str, Any] = json.loads(OUT.read_text())
    by_file: dict[str, list[SeedRecipe]] = {}
    missing = []
    for file, source in load_sources():
        draft = drafts.get(key(file, source["title"]))
        if draft is None or draft["ok"] is not True:
            missing.append(key(file, source["title"]))
            continue
        by_file.setdefault(file, []).append(seed_from(source, draft))
    if missing:
        print(f"{len(missing)} recipes have no passing draft: {missing[:5]}")
        return 1
    photos = {image.slug for image in load_recipe_images()}
    by_file = {f: [s for s in seeds if s.slug in photos] for f, seeds in by_file.items()}
    by_file = {f: seeds for f, seeds in by_file.items() if seeds}

    for old in out_dir.glob("*.json"):
        old.unlink()
    for file, seeds in by_file.items():
        name = file.removeprefix("batch_")
        rows = [s.model_dump(mode="json", exclude_defaults=True) for s in seeds]
        (out_dir / name).write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n")
    print(f"{sum(map(len, by_file.values()))} Seed Recipes in {len(by_file)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
