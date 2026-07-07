# Workflow — Add or update a property listing

**Objective:** Put a new property on the website (or update an existing one),
end to end.

## Inputs required
- The property proposal (PDF is ideal — it has price, specs, features, location)
- Photos (either inside the PDF or as separate image files)

## Steps

1. **Pick a slug** — a short, url-safe id, lowercase with hyphens.
   e.g. `casa-solis`, `villa-marigold`, `dona-paula-heights`.

2. **Add the photos** to `assets/properties/<slug>/` with these stems
   (only the ones you have; the gallery adapts):
   - `exterior.jpg` — used on the listing-grid card
   - `pool.jpg` — the big hero image on the detail page
   - `living.jpg`, `dining.jpg`, `primary.jpg`, `bedroom.jpg`,
     `kitchen.jpg`, `bath.jpg`, `aerial.jpg`, `location.jpg` — gallery
   Keep each **1400–1900px wide, `.jpg`, under ~500 KB**. Optimise big files:
   ```
   python3 tools/optimize_images.py assets/properties/<slug>
   ```
   (see `tools/optimize_images.py`; run only if photos are large.)

3. **Add a listing object** to the `listings` array in `data/listings.json`.
   Copy the `casa-solis` block and edit every field. Key fields:
   - `slug` — must match the folder name in step 2
   - `featured` — set `true` on the ONE listing you want on the home page
     (set the previous featured listing to `false`)
   - `price_value` — the price in **rupees as a plain number** (₹6.5 Cr =
     `65000000`). This drives the price filter — get it right.
   - `beds_value` — highest bedroom count as a number (drives the beds filter)
   - `area_value` — built-up sq ft as a number
   - `location` — the area name (e.g. `Siolim`); becomes a filter option
   - `hero_image` / `card_image` / `gallery[].img` — the photo **stems** from
     step 2 (no `.jpg`, no path)

4. **Rebuild the site:**
   ```
   python3 tools/build_site.py
   ```
   It regenerates `index.html`, `properties/index.html`, and one
   `properties/<slug>/index.html` per listing.

5. **Preview** (see `workflows/build_site.md`) and confirm the new card appears,
   filters work, and the detail page looks right.

## Notes & gotchas
- The generator is deterministic — safe to re-run any time. It only writes HTML;
  it never touches your photos or data.
- To **remove** a listing: delete its object from `listings.json` (and optionally
  its photo folder), then rebuild.
- If a listing has fewer photos, just shorten its `gallery` array — the layout
  reflows. The first `wide` image spans two columns.
