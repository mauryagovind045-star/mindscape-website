# Workflow — Build & preview the website

**Objective:** Regenerate the site from data and view it locally before publishing.

## Build
The whole site is generated from `data/listings.json` by one script:
```
python3 tools/build_site.py
```
Outputs (all safe to overwrite, all committed):
- `index.html` — home page (uses the `featured` listing)
- `properties/index.html` — listings grid with filters + search
- `properties/<slug>/index.html` — one page per listing (clean URL)

Shared assets are **not** generated — edit them directly if needed:
`assets/css/site.css`, `assets/js/site.js`, `assets/js/listings.js`.

## Preview locally
Because the site uses clean folder URLs (`/properties/casa-solis/`), preview it
through a local server, **not** by double-clicking the file:
```
cd "$(dirname "$0")"          # the project root
python3 -m http.server 8000
```
Then open <http://localhost:8000>. Stop the server with `Ctrl + C`.

Check:
- Home → "Explore Properties" and "View All Properties" reach the grid
- Grid → Search + Location/Price/Bedrooms filters narrow results; "Reset" clears
- Each card → "View details" opens the property page
- Property page → gallery lightbox, "Arrange a Viewing", "Call", enquiry form

## Publish
Upload the whole project folder to any static host (Netlify, GitHub Pages,
Cloudflare Pages, or normal web hosting). The clean URLs work automatically.
**Do not upload** the source proposal PDFs in `assets/properties/*/` — they're
reference only. Everything else (`index.html`, `properties/`, `assets/`) ships.

## Turn the enquiry form into real inbox delivery
In `assets/js/site.js`, set `FORM_ENDPOINT` to a free endpoint from
web3forms.com or formspree.io. Until then, the form opens the visitor's email
app pre-filled to `hello@mindscapeproperties.in`.
