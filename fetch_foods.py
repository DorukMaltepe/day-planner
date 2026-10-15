"""Append Edeka/REWE/Lidl products from Open Food Facts to foods.csv. Re-run any time; existing names are kept.

    python fetch_foods.py
"""
import csv
import json
import os
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(HERE, "foods.csv")
API = "https://search.openfoodfacts.org/search"
UA = "day-planner/1.0 (personal food log)"
DE = ' AND countries_tags:"en:germany"'
NOT_GRADED = " AND NOT nutrition_grades:(a OR b OR c OR d OR e)"

# Edeka first. The search API stops at 10,000 hits per query, so REWE's store tag is split by Nutri-Score.
QUERIES = (
    ["stores:edeka" + DE]
    + [f'brands_tags:"{b}"' for b in ("gut-gunstig", "edeka", "edeka-bio", "edeka-herzstucke", "gut-bio")]
    + [f"stores:rewe{DE} AND nutrition_grades:{g}" for g in "abcde"] + ["stores:rewe" + DE + NOT_GRADED]
    + [f'brands_tags:"{b}"' for b in ("ja", "rewe", "rewe-bio", "rewe-beste-wahl")]
    + ["stores:lidl" + DE]
    + [f'brands_tags:"{b}"{DE}' for b in ("milbona", "pilos", "freeway", "crownfield", "vitasia", "chef-select",
                                          "combino", "solevita", "alesto", "deluxe", "favorina", "snack-day")]
)


def get(q, page):
    params = urllib.parse.urlencode({"q": q, "page": page, "page_size": 100,
                                     "fields": "product_name,brands,nutriments"})
    req = urllib.request.Request(f"{API}?{params}", headers={"User-Agent": UA})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception as e:  # flaky public API: back off and retry
            print(f"  retry {attempt + 1} ({e})")
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"giving up on {q!r} page {page}")


def to_row(p):
    """Product -> csv row, or None when it lacks usable per-100 g values."""
    name = " ".join(str(p.get("product_name") or "").split())
    n = p.get("nutriments") or {}
    kcal = n.get("energy-kcal_100g")
    if kcal is None and n.get("energy-kj_100g") is not None:
        kcal = n["energy-kj_100g"] / 4.184
    try:
        kcal, protein, carbs, fat = (float(v) for v in (kcal, n["proteins_100g"], n["carbohydrates_100g"], n["fat_100g"]))
        fiber = float(n.get("fiber_100g") or 0)
    except (KeyError, TypeError, ValueError):
        return None
    # drop obvious data-entry errors (per-portion values, wrong units)
    if not name or not 0 <= kcal <= 900 or min(protein, carbs, fat, fiber) < 0 or protein + carbs + fat > 105:
        return None
    brand = (p.get("brands") or [""])[0].strip()
    if brand and brand.lower() not in name.lower():
        name = f"{name} ({brand})"
    return {"name": name, "kcal": round(kcal), "protein": round(protein, 1), "carbs": round(carbs, 1),
            "fat": round(fat, 1), "fiber": round(fiber, 1)}


def main():
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    seen = {r["name"].lower() for r in rows}  # foods.name is UNIQUE COLLATE NOCASE
    start = len(rows)
    for q in QUERIES:
        page, pages = 1, 1
        while page <= pages:
            d = get(q, page)
            pages = d.get("page_count") or 0
            for row in filter(None, map(to_row, d["hits"])):
                if row["name"].lower() not in seen:
                    seen.add(row["name"].lower())
                    rows.append(row)
            page += 1
        print(f"{q}: {len(rows) - start} new so far")
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["name", "kcal", "protein", "carbs", "fat", "fiber"], lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"added {len(rows) - start}, total {len(rows)}")


if __name__ == "__main__":
    main()
