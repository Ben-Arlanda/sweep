"""Find and pick Recipe Images for the Seed Recipes from Unsplash (slice 4f, ADR 0029).

    uv run python -m scripts.recipe_images search   # free; slow (50 searches an hour)
    uv run python -m scripts.recipe_images review   # http://127.0.0.1:8765, pick by eye
    uv run python -m scripts.recipe_images apply    # credits file + Unsplash download notices

search keeps up to four options per recipe, dropping any whose description names a meat
or fish the recipe doesn't have. No model looks at Unsplash photos: their API terms send
AI use to a separate agreement. The first option is picked unless the product owner
changes it (or picks none) on the review page, which shows the photos from Unsplash itself
(hotlinked, as their terms require). apply tells Unsplash each picked photo was used
(their "download" event) and writes `app/data/recipe_images.json`. Every step is
resumable.
"""

import argparse
import html
import json
import re
import sys
import time
from collections.abc import Sequence
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel

from app.config import settings
from app.data.recipe_images import RECORDS, RecipeImage, sized
from app.data.recipes import SeedRecipe, load_seed_recipes
from app.services.recipe_image_check import title_clash

WORK = Path(__file__).parents[1] / "data" / "recipe-images"
OPTIONS = WORK / "unsplash.json"  # slug -> {"queries": [...], "options": [...]}
CHOICES = WORK / "choices.json"  # slug -> photo id, or null for no photo
NOTIFIED = WORK / "notified.json"  # photo ids Unsplash was told about
API = "https://api.unsplash.com"
MOST = 4
PACE = 75  # seconds between requests: demo mode allows 50 an hour


class Option(BaseModel):
    photo_id: str
    raw_url: str
    author: str
    author_url: str
    photo_url: str
    download_location: str
    description: str
    width: int
    height: int


FILLER = {
    *("classic", "fluffy", "creamy", "crispy", "easy", "quick", "simple", "homemade"),
    *("hearty", "sticky", "golden", "best", "perfect", "rustic", "healthy"),
}


def queries(title: str) -> list[str]:
    """The title, then shorter forms: a long title finds little, since every word must match."""
    plain = re.sub(r"\s*\(.*?\)", "", title).strip()
    words = [w for w in plain.split() if w.lower() not in FILLER]
    core = re.split(r"\s+(?:with|in|on)\s+", " ".join(words), maxsplit=1)[0]
    tries = [plain, " ".join(words), core, " ".join(core.split()[-2:])]
    return list(dict.fromkeys(q for q in tries if q))


def option(result: dict[str, Any], recipe: SeedRecipe) -> Option | None:
    """An Unsplash search result as an option, or None if code rules it out."""
    words = " ".join(filter(None, [result.get("description"), result.get("alt_description")]))
    if title_clash(recipe, words) or min(result["width"], result["height"]) < 1200:
        return None
    user = result["user"]
    return Option(
        photo_id=result["id"],
        raw_url=result["urls"]["raw"],
        author=" ".join((user.get("name") or user["username"]).split()),
        author_url=user["links"]["html"],
        photo_url=result["links"]["html"],
        download_location=result["links"]["download_location"],
        description=words[:300],
        width=result["width"],
        height=result["height"],
    )


def _load(path: Path) -> Any:
    return json.loads(path.read_text()) if path.exists() else {}


def _save(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False, sort_keys=True) + "\n")


def _client() -> httpx.Client:
    if settings.unsplash_access_key is None:
        sys.exit("UNSPLASH_ACCESS_KEY is not set in services/api/.env")
    key = settings.unsplash_access_key.get_secret_value()
    headers = {"Authorization": f"Client-ID {key}", "Accept-Version": "v1"}
    return httpx.Client(base_url=API, headers=headers, timeout=30)


def _get(client: httpx.Client, path: str, params: dict[str, str] | None = None) -> Any:
    while True:
        try:
            response = client.get(path, params=params)
        except httpx.TransportError as error:  # a dropped connection: try again shortly
            print(f"  network error ({error}): retrying in a minute", flush=True)
            time.sleep(60)
            continue
        if response.status_code in (403, 429) and "Rate Limit" in response.text:
            print("  hourly limit reached: waiting 10 minutes", flush=True)
            time.sleep(600)
            continue
        response.raise_for_status()
        time.sleep(PACE)
        return response.json()


def search(recipes: Sequence[SeedRecipe]) -> None:
    found = _load(OPTIONS)
    with _client() as client:
        for n, recipe in enumerate(recipes, 1):
            if recipe.slug in found:
                continue
            row: dict[str, Any] = {"queries": [], "options": []}
            for query in queries(recipe.title):
                params = {
                    "query": query,
                    "per_page": "10",
                    "orientation": "landscape",
                    "content_filter": "high",
                }
                results = _get(client, "/search/photos", params)["results"]
                row["queries"].append(query)
                ids = {o["photo_id"] for o in row["options"]}
                for result in results:
                    if (o := option(result, recipe)) and o.photo_id not in ids:
                        row["options"].append(o.model_dump())
                        ids.add(o.photo_id)
                if len(row["options"]) >= MOST:
                    break
            row["options"] = row["options"][:MOST]
            found[recipe.slug] = row
            _save(OPTIONS, found)
            print(f"{n:3} {recipe.slug:40} {len(row['options'])} options", flush=True)
    print(f"{len(found)} recipes searched")


# --- review ---------------------------------------------------------------------------

PAGE = """<!doctype html><meta charset="utf-8"><title>Pick recipe photos</title>
<style>
body{font:15px system-ui,sans-serif;margin:0;background:#f6f8f1;color:#17233d}
header{position:sticky;top:0;background:#17233d;color:#fff;padding:12px 20px;z-index:2}
main{padding:16px 20px;display:grid;gap:18px}
section{background:#fff;border:1px solid #dfe4d6;border-radius:10px;padding:12px}
h2{font-size:16px;margin:0 0 2px} p{margin:0 0 10px;color:#5b6577;font-size:13px}
.row{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px}
button{border:3px solid transparent;border-radius:8px;padding:0;background:#eef1e8;
cursor:pointer;font:inherit;color:inherit;min-height:60px}
button img{width:100%;aspect-ratio:4/3;display:block;border-radius:5px}
button[aria-pressed=true]{border-color:#7aa80f;box-shadow:0 0 0 2px #c6f05a}
button.none{font-weight:600}
section.done{opacity:.75} section.done:hover{opacity:1}
small{display:block;color:#5b6577;font-size:11px;padding:3px}
</style>
<header><b>The first photo is picked for you.</b> Click only to change it, or "No photo".
Changes save as you click.
<span id=count></span>
<label><input type=checkbox id=todo> Hide recipes I've changed</label>
</header><main id=main>__SECTIONS__</main>
<script>
const total = document.querySelectorAll('section').length;
function count(){document.getElementById('count').textContent =
  ` ${document.querySelectorAll('section.done').length} of ${total} changed by hand.`}
function filter(){const on = document.getElementById('todo').checked;
  document.querySelectorAll('section').forEach(s =>
    s.hidden = on && s.classList.contains('done'))}
document.querySelectorAll('section').forEach(sec =>
  sec.querySelectorAll('button').forEach(b => b.onclick = async () => {
    const r = await fetch('/choice', {method: 'POST', body: JSON.stringify(
      {slug: sec.dataset.slug, photo_id: b.dataset.id || null})});
    if (!r.ok) { b.textContent = 'Not saved: is the review server running?'; return; }
    sec.querySelectorAll('button').forEach(x => x.setAttribute('aria-pressed', x === b));
    sec.classList.add('done'); count(); filter();
  }));
document.getElementById('todo').onchange = filter; count();
</script>"""


def picked(slug: str, found: dict[str, Any], chosen: dict[str, Any]) -> str | None:
    """The product owner's pick, or else the first option: they review by exception."""
    if slug in chosen:
        return str(chosen[slug]) if chosen[slug] else None
    options = found.get(slug, {}).get("options", [])
    return str(options[0]["photo_id"]) if options else None


def review_page(recipes: Sequence[SeedRecipe]) -> str:
    found, chosen = _load(OPTIONS), _load(CHOICES)
    sections = []
    for recipe in sorted(recipes, key=lambda r: r.title.lower()):
        if recipe.slug not in found:
            continue  # not searched yet: reload the page later
        rows = found[recipe.slug]["options"]
        pick = picked(recipe.slug, found, chosen)
        buttons = [
            f'<button data-id="{o.photo_id}" aria-pressed="{str(pick == o.photo_id).lower()}">'
            f'<img loading=lazy alt="" src="{html.escape(sized(o.raw_url, 360))}">'
            f"<small>{html.escape(o.description[:90])}</small></button>"
            for o in (Option.model_validate(row) for row in rows)
        ]
        buttons.append(
            f'<button class=none aria-pressed="{str(pick is None).lower()}">No photo</button>'
        )
        done = " class=done" if recipe.slug in chosen else ""
        sections.append(
            f'<section data-slug="{recipe.slug}"{done}><h2>{html.escape(recipe.title)}</h2>'
            f"<p>{recipe.course.value} · {html.escape(recipe.summary)}</p>"
            f"<div class=row>{''.join(buttons)}</div></section>"
        )
    return PAGE.replace("__SECTIONS__", "\n".join(sections))


def review(recipes: Sequence[SeedRecipe]) -> None:
    slugs = {r.slug for r in recipes}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            body = review_page(recipes).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:
            data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            slug, photo = data.get("slug"), data.get("photo_id")
            row = _load(OPTIONS).get(slug)  # read now: the search may still be adding
            ids = {o["photo_id"] for o in row["options"]} if row else set()
            if slug not in slugs or row is None or (photo is not None and photo not in ids):
                self.send_response(400)
                self.end_headers()
                return
            chosen = _load(CHOICES)
            chosen[slug] = photo
            _save(CHOICES, chosen)
            self.send_response(204)
            self.end_headers()

        def log_message(self, *args: Any) -> None:
            pass

    print("Review at http://127.0.0.1:8765 (Ctrl-C to stop)")
    HTTPServer(("127.0.0.1", 8765), Handler).serve_forever()


# --- apply ----------------------------------------------------------------------------


def apply(recipes: Sequence[SeedRecipe]) -> None:
    found, chosen = _load(OPTIONS), _load(CHOICES)
    notified = set(_load(NOTIFIED) or [])
    records: list[RecipeImage] = []
    with _client() as client:
        for recipe in recipes:
            photo = picked(recipe.slug, found, chosen)
            rows = found.get(recipe.slug, {}).get("options", [])
            options = {row["photo_id"]: Option.model_validate(row) for row in rows}
            if photo is None or photo not in options:
                continue
            o = options[photo]
            if photo not in notified:  # Unsplash's "download" event, once per photo
                _get(client, o.download_location.removeprefix(API))
                notified.add(photo)
                _save(NOTIFIED, sorted(notified))
            records.append(
                RecipeImage(
                    slug=recipe.slug,
                    source="unsplash",
                    photo_id=photo,
                    raw_url=o.raw_url,
                    author=o.author,
                    author_url=o.author_url,
                    photo_url=o.photo_url,
                )
            )
    RECORDS.write_text(
        json.dumps([r.model_dump() for r in records], indent=1, ensure_ascii=False) + "\n"
    )
    print(f"{len(records)} Recipe Images written to {RECORDS}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("step", choices=["search", "review", "apply"])
    parser.add_argument("--only", nargs="*", help="these slugs only")
    args = parser.parse_args()
    recipes = [r for r in load_seed_recipes() if not args.only or r.slug in args.only]
    {"search": search, "review": review, "apply": apply}[args.step](recipes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
