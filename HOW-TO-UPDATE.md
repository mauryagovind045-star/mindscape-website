# Mindscape Properties — website guide

A proper multi-page site, generated from one data file. You don't edit HTML by
hand — you edit **`data/listings.json`** and run **one build command**.

---

## The pages

| URL | File | What it is |
|-----|------|------------|
| `/` | `index.html` | Home — hero, approach, the **featured** listing, about, contact |
| `/properties/` | `properties/index.html` | All listings — grid with **filters + search** |
| `/properties/<slug>/` | `properties/<slug>/index.html` | One real page per property (clean URL, good for Google & WhatsApp) |

All three are **generated** — don't edit them directly, they get overwritten.

## How it's put together

```
data/listings.json          ← the ONLY thing you edit to add/change listings
tools/build_site.py         ← generates all the HTML pages
tools/optimize_images.py    ← shrinks big photos for the web
workflows/                  ← step-by-step SOPs (add_listing, build_site)
assets/css/site.css         ← all styling (edit here to change the look)
assets/js/site.js           ← nav, forms, gallery, animations
assets/js/listings.js       ← the filter + search logic
assets/properties/<slug>/   ← each property's photos
```

---

## Add a new listing (the short version)

1. Put photos in `assets/properties/<slug>/` (e.g. `pool.jpg`, `living.jpg`…).
   Shrink them if large: `python3 tools/optimize_images.py assets/properties/<slug>`
2. Copy the `casa-solis` block in `data/listings.json`, change every field.
   Set `featured: true` on the one you want on the home page (and `false` on the old one).
3. Build: `python3 tools/build_site.py`
4. Preview: `python3 -m http.server 8000` → open <http://localhost:8000>

Full detail (every field explained) is in **`workflows/add_listing.md`**.

> Easiest of all: **send me the proposal PDF + photos** and I'll do all of the above.

---

## Preview & publish

- **Preview:** always through a local server (clean URLs need it):
  `python3 -m http.server 8000` then <http://localhost:8000>.
  Double-clicking the file won't route `/properties/...` correctly.
- **Publish:** upload the whole folder to any static host (Netlify, GitHub
  Pages, Cloudflare Pages, or normal hosting). Clean URLs work automatically.
  **Don't upload** the source proposal PDFs in `assets/properties/*/` — reference only.

## Make the enquiry forms hit your inbox

In `assets/js/site.js`, set `FORM_ENDPOINT` to a free endpoint from
<https://web3forms.com> (or formspree.io). Until then, every form (home,
listings, and each property page) opens the visitor's email app pre-filled to
`hello@mindscapeproperties.in`. The property forms tag the enquiry with the
property name automatically.

---

## Brand quick-reference (already applied)

- **Gold** `#C9A96E` · **Black** `#0F0F0D` · **Ivory** `#F5F0E8`
- Headings: Cormorant Garamond · Body/UI: DM Sans
- Advisor: Govind · +91 89566 19967 · hello@mindscapeproperties.in
- Office: Off No. 508, 5th Floor, Gera Impremium Grand, Patto, Panjim, Goa
