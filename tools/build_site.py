#!/usr/bin/env python3
"""
build_site.py — Mindscape Properties static-site generator.

Reads data/listings.json (the single source of truth) and writes:
  index.html                          the home page (featured listing)
  properties/index.html               the listings grid (filters + search)
  properties/<slug>/index.html        one real page per property (clean URL)

Shared CSS/JS live in assets/css/site.css and assets/js/*.js — this script
only writes HTML, so re-running it is safe and deterministic.

Usage:
    python3 tools/build_site.py
"""

import html
import json
import os
import re
import sys
import urllib.parse

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(ROOT_DIR, "data", "listings.json")
BLOG_FILE = os.path.join(ROOT_DIR, "data", "blog.json")

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com" />\n'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />\n'
         '<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:'
         'ital,wght@0,300;0,400;0,500;0,600;1,300;1,400&family=DM+Sans:wght@300;400;500'
         '&display=swap" rel="stylesheet" />')

PRICE_BANDS = [
    ("", "Any price"),
    ("0-20000000", "Under ₹2 Cr"),
    ("20000000-50000000", "₹2 – 5 Cr"),
    ("50000000-100000000", "₹5 – 10 Cr"),
    ("100000000-", "₹10 Cr +"),
]
BED_BANDS = [("", "Any"), ("2", "2+"), ("3", "3+"), ("4", "4+"), ("5", "5+")]


def e(s):
    """Escape plain text for safe HTML output."""
    return html.escape(str(s), quote=True)


def img_path(root, slug, stem):
    return f"{root}assets/properties/{slug}/{stem}.jpg"


WA_SVG = ('<svg width="28" height="28" viewBox="0 0 24 24" aria-hidden="true"><path d="M17.472 14.382c-.297-.149'
          '-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164'
          '-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761'
          '-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198'
          '-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242'
          '-.579-.487-.5-.669-.51l-.57-.01c-.198 0-.52.074-.792.372-.272.297-1.04 1.016'
          '-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.71.306'
          ' 1.263.489 1.694.625.712.227 1.36.195 1.872.118.571-.085 1.758-.719 2.006-1.413'
          '.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87'
          ' 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51'
          '-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0'
          ' 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 '
          '0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305'
          '-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821'
          ' 11.821 0 00-3.48-8.413z"/></svg>')

WA_GENERIC = "Hi Mindscape, I'd like to know more about your Goa properties."


def wa_digits(site):
    return "".join(c for c in site["phone_href"] if c.isdigit())


def wa_link(site, text):
    return f"https://wa.me/{wa_digits(site)}?text={urllib.parse.quote(text)}"


def whatsapp_fab(site, text):
    return (f'\n<a class="wa-fab" href="{wa_link(site, text)}" target="_blank" rel="noopener" '
            f'aria-label="Chat with us on WhatsApp"><span class="ic">{WA_SVG}</span>'
            f'<span class="lbl">Chat on WhatsApp</span></a>')


# --------------------------------------------------------------------------- #
#  Shared chrome                                                              #
# --------------------------------------------------------------------------- #
def links(root, on_home):
    home = root if root else "./"
    return {
        "home": home,
        "properties": f"{root}properties/",
        "journal": f"{root}journal/",
        "about": "#about" if on_home else f"{root}#about",
        "approach": "#approach" if on_home else f"{root}#approach",
        "contact": "#contact",
    }


def abs_url(site, path=""):
    """Absolute canonical URL from a root-relative path (no leading slash)."""
    return site["website_url"].rstrip("/") + "/" + path.lstrip("/")


def seo_tags(site, canonical_path, title, desc, image_abs, og_type="website"):
    """Canonical + Open Graph + Twitter card tags for a page."""
    canon = abs_url(site, canonical_path)
    return (
        f'<link rel="canonical" href="{e(canon)}" />\n'
        f'<meta property="og:type" content="{og_type}" />\n'
        f'<meta property="og:site_name" content="{e(site["name"])}" />\n'
        f'<meta property="og:title" content="{e(title)}" />\n'
        f'<meta property="og:description" content="{e(desc)}" />\n'
        f'<meta property="og:url" content="{e(canon)}" />\n'
        f'<meta property="og:image" content="{e(image_abs)}" />\n'
        f'<meta name="twitter:card" content="summary_large_image" />\n'
        f'<meta name="twitter:title" content="{e(title)}" />\n'
        f'<meta name="twitter:description" content="{e(desc)}" />\n'
        f'<meta name="twitter:image" content="{e(image_abs)}" />'
    )


def jsonld(obj):
    """Render a JSON-LD structured-data script tag."""
    return ('<script type="application/ld+json">'
            + json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
            + "</script>")


# Bump ASSET_VER whenever site.css / site.js change, so browsers re-fetch
# them instead of serving a stale cached copy.
ASSET_VER = "7"
GA_ID = ""  # GA4 Measurement ID (G-XXXXXXXXXX); set from site["ga_id"] at build time
GTM_ID = ""  # Google Tag Manager container ID (GTM-XXXXXXX); set from site["gtm_id"] at build time


def ga_snippet():
    """Google Analytics 4 (gtag.js). Renders only when a Measurement ID is configured."""
    if not GA_ID:
        return ""
    return (
        '<!-- Google Analytics (GA4) -->\n'
        '<script async src="https://www.googletagmanager.com/gtag/js?id=' + GA_ID + '"></script>\n'
        '<script>window.dataLayer=window.dataLayer||[];'
        'function gtag(){dataLayer.push(arguments);}'
        "gtag('js',new Date());"
        "gtag('config','" + GA_ID + "');</script>"
    )


def gtm_head():
    """Google Tag Manager head snippet. Renders only when a container ID is configured.
    Placed as high in <head> as possible, per Google's install guidance."""
    if not GTM_ID:
        return ""
    return (
        "<!-- Google Tag Manager -->\n"
        "<script>(function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':\n"
        "new Date().getTime(),event:'gtm.js'});var f=d.getElementsByTagName(s)[0],\n"
        "j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=\n"
        "'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);\n"
        "})(window,document,'script','dataLayer','" + GTM_ID + "');</script>\n"
        "<!-- End Google Tag Manager -->"
    )


def gtm_noscript():
    """Google Tag Manager <noscript> fallback. Goes immediately after <body>."""
    if not GTM_ID:
        return ""
    return (
        '<!-- Google Tag Manager (noscript) -->\n'
        '<noscript><iframe src="https://www.googletagmanager.com/ns.html?id=' + GTM_ID + '"\n'
        'height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript>\n'
        '<!-- End Google Tag Manager (noscript) -->'
    )


def head(title, desc, root, page_js="", extra_head=""):
    v = ASSET_VER
    extra = (f'<script defer src="{root}assets/js/{page_js}?v={v}"></script>' if page_js else "")
    seo = f"\n{extra_head}" if extra_head else ""
    ga = ga_snippet()
    ga = f"{ga}\n" if ga else ""
    gtm = gtm_head()
    gtm = f"{gtm}\n" if gtm else ""
    gtm_ns = gtm_noscript()
    gtm_ns = f"\n{gtm_ns}" if gtm_ns else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
{gtm}{ga}<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}" />{seo}
{FONTS}
<link rel="stylesheet" href="{root}assets/css/site.css?v={v}" />
<script defer src="{root}assets/js/site.js?v={v}"></script>
{extra}
</head>
<body>{gtm_ns}"""


def nav(site, lk, root, active, solid=False):
    def cls(name):
        return ' class="active"' if name == active else ""
    solid_cls = " solid" if solid else ""
    return f"""
<header id="header" class="{solid_cls.strip()}">
  <div class="wrap nav">
    <a href="{lk['home']}" class="nav-logo" aria-label="{e(site['name'])} home">
      <img src="{root}assets/mindscape-logo-dark-600x200.png" alt="{e(site['name'])}" />
    </a>
    <nav class="nav-links" id="navLinks">
      <a href="{lk['properties']}"{cls('properties')}>Properties</a>
      <a href="{lk['journal']}"{cls('journal')}>Journal</a>
      <a href="{lk['about']}"{cls('about')}>About</a>
      <a href="{lk['approach']}"{cls('approach')}>Our Approach</a>
      <a href="{lk['contact']}"{cls('contact')}>Contact</a>
    </nav>
    <div class="nav-cta"><a href="{lk['contact']}" class="btn"><span>Get in Touch</span></a></div>
    <button class="burger" id="burger" aria-label="Menu"><span></span><span></span><span></span></button>
  </div>
</header>"""


def contact_section(site, property_name=""):
    data_attr = f' data-property="{e(property_name)}"' if property_name else ""
    intro = ("Ask us anything about this property — a private viewing, floor plans, "
             "or the title documents." if property_name else
             "Tell us what you're looking for. We'll bring you the few properties "
             "genuinely worth your time — no noise, no pressure.")
    heading = "Enquire about this home." if property_name else "Find your place<br>on this coast."
    return f"""
<section class="contact" id="contact">
  <div class="contact-glow"></div>
  <div class="wrap">
    <div class="contact-grid">
      <div class="contact-info reveal">
        <span class="eyebrow">Let's Begin</span>
        <h2>{heading}</h2>
        <p class="intro">{e(intro)}</p>
        <div class="contact-rows">
          <div class="crow"><span class="diamond"></span><div>
            <div class="k">Your Advisor</div>
            <div class="v">{e(site['advisor'])} — {e(site['name'])}<br><a href="tel:{e(site['phone_href'])}">{e(site['phone_display'])}</a></div>
          </div></div>
          <div class="crow"><span class="diamond"></span><div>
            <div class="k">Email</div>
            <div class="v"><a href="mailto:{e(site['email'])}">{e(site['email'])}</a></div>
          </div></div>
          <div class="crow"><span class="diamond"></span><div>
            <div class="k">Visit</div>
            <div class="v">{site['address_html']}</div>
          </div></div>
        </div>
      </div>
      <div class="form-shell reveal d1">
        <span class="diamond"></span>
        <h3>Enquire with us</h3>
        <p class="sub">Share a few details and your dedicated advisor will be in touch within one business day.</p>
        <form id="enquiryForm" novalidate{data_attr}>
          <div class="field row2">
            <div><label for="name">Full Name <span class="req">*</span></label>
              <input type="text" id="name" name="name" placeholder="Your name" required /></div>
            <div><label for="phone">Phone</label>
              <input type="tel" id="phone" name="phone" placeholder="+91" /></div>
          </div>
          <div class="field"><label for="email">Email <span class="req">*</span></label>
            <input type="email" id="email" name="email" placeholder="you@email.com" required /></div>
          <div class="field row2">
            <div><label for="intent">I'm interested in</label>
              <select id="intent" name="intent">
                <option>Buying a property</option><option>Selling a property</option>
                <option>Renting / leasing</option><option>Just exploring</option>
              </select></div>
            <div><label for="budget">Budget</label>
              <select id="budget" name="budget">
                <option>Under ₹2 Cr</option><option>₹2 – 5 Cr</option><option>₹5 – 10 Cr</option>
                <option>₹10 Cr +</option><option>Not sure yet</option>
              </select></div>
          </div>
          <div class="field"><label for="message">Message</label>
            <textarea id="message" name="message" placeholder="Tell us about the home you're looking for — location, style, timeline…"></textarea></div>
          <input type="checkbox" name="botcheck" class="hpot" tabindex="-1" autocomplete="off" aria-hidden="true" />
          <button type="submit" class="btn solid"><span>Send Enquiry</span></button>
          <div class="form-status" id="formStatus" role="status" aria-live="polite"></div>
          <p class="form-note">Your details stay private and are used only to respond to your enquiry.</p>
        </form>
      </div>
    </div>
  </div>
</section>"""


def footer(site, lk, root):
    return f"""
<footer>
  <div class="wrap">
    <div class="foot-grid">
      <div class="foot-brand foot-logo">
        <img src="{root}assets/mindscape-logo-dark-600x200.png" alt="{e(site['name'])}" />
        <p>A premium boutique real estate brokerage in Panjim, Goa. Engineer-led, client-first — where luxury meets the Arabian Sea.</p>
      </div>
      <div class="foot-col"><h4>Explore</h4>
        <a href="{lk['properties']}">Properties</a>
        <a href="{lk['journal']}">Journal</a>
        <a href="{lk['about']}">About Us</a>
        <a href="{lk['approach']}">Our Approach</a>
        <a href="{lk['contact']}">Contact</a>
      </div>
      <div class="foot-col"><h4>Connect</h4>
        <a href="tel:{e(site['phone_href'])}">{e(site['phone_display'])}</a>
        <a href="mailto:{e(site['email'])}">Email Us</a>
        <a href="{e(site['website_url'])}">Website</a>
        <a href="{lk['contact']}">Book a Viewing</a>
      </div>
      <div class="foot-col"><h4>Visit</h4>
        <p>{site['address_html']}</p>
        <a href="mailto:{e(site['email'])}">{e(site['email'])}</a>
      </div>
    </div>
    <div class="foot-bottom">
      <p>© 2026 {e(site['name'])}. All rights reserved.</p>
      <div class="foot-social">
        <a href="{e(site['instagram'])}">Instagram</a>
        <a href="{e(site['linkedin'])}">LinkedIn</a>
        <a href="{e(site['website_url'])}">{e(site['website_display'])}</a>
      </div>
    </div>
  </div>
</footer>"""


LIGHTBOX = """
<div class="lightbox" id="lightbox" role="dialog" aria-label="Photo viewer">
  <span class="lb-close" id="lbClose" aria-label="Close">&times;</span>
  <span class="lb-nav lb-prev" id="lbPrev" aria-label="Previous">&#8249;</span>
  <img id="lbImg" src="" alt="Property photo" />
  <span class="lb-nav lb-next" id="lbNext" aria-label="Next">&#8250;</span>
</div>"""


# --------------------------------------------------------------------------- #
#  Property blocks                                                            #
# --------------------------------------------------------------------------- #
def feature_block(l, root, site, mode, detail_href=""):
    slug = l["slug"]
    badges = "".join(f'<span class="fbadge">{e(b)}</span>' for b in l["badges"])
    specs = "".join(f'<div class="spec"><b>{e(s["v"])}</b><small>{e(s["l"])}</small></div>' for s in l["specs"])
    desc = "".join(f"<p>{e(p)}</p>" for p in l["description"])
    gallery = ""
    for g in l["gallery"]:
        src = img_path(root, slug, g["img"])
        wide = " wide" if g.get("wide") else ""
        gallery += (f'<a class="{wide.strip()}" data-full="{src}" '
                    f'style="background-image:url(\'{src}\')" aria-label="{e(g["label"])}"></a>')
    features = "".join(f'<li><span class="diamond"></span>{e(f)}</li>' for f in l["features"])
    loc_rows = "".join(
        f'<div class="loc-row"><span class="place">{e(p["place"])}</span>'
        f'<span class="time">{e(p["time"])}</span></div>' for p in l["location_points"])

    if mode == "home":
        cta = (f'<a href="{detail_href}" class="btn solid"><span>View Full Details</span></a>'
               f'<a href="#contact" class="btn"><span>Arrange a Viewing</span></a>')
    else:
        wa_text = (f"Hi Mindscape, I'm interested in {l['name']} (Ref {l['ref']}), "
                   f"{l['location']}, {l['region']}. Please share more details.")
        cta = (f'<a href="#contact" class="btn solid"><span>Arrange a Viewing</span></a>'
               f'<a href="{wa_link(site, wa_text)}" target="_blank" rel="noopener" class="btn"><span>WhatsApp Us</span></a>'
               f'<a href="tel:{e(site["phone_href"])}" class="btn"><span>Call {e(site["phone_display"])}</span></a>')

    hero = img_path(root, slug, l["hero_image"])
    return f"""
    <article class="feature reveal">
      <div class="feature-hero">
        <div class="feature-hero-img" style="background-image:url('{hero}')"></div>
        <div class="feature-badges">{badges}</div>
        <div class="feature-caption">
          <div>
            <div class="loc"><span class="diamond" style="width:6px;height:6px"></span>{e(l['location'])} · {e(l['region'])}</div>
            <h3>{e(l['name'])}</h3>
            <div class="ref">Ref · {e(l['ref'])}</div>
          </div>
          <div class="feature-price">
            <div class="amt">{e(l['price_display'])}</div>
            <div class="note">{e(l['price_note'])}</div>
          </div>
        </div>
      </div>
      <div class="feature-body">
        <div class="feature-lead">
          <div>{desc}</div>
          <div class="spec-grid">{specs}</div>
        </div>
        <div class="gallery">{gallery}</div>
        <div class="feature-split">
          <div>
            <div class="kf-title"><span class="diamond"></span>{e(l.get('feature_heading', 'Why this villa'))}</div>
            <ul class="kf-list">{features}</ul>
          </div>
          <div>
            <div class="loc-title"><span class="diamond"></span>{e(l['location_label'])}</div>
            <div class="loc-list">{loc_rows}</div>
            <p class="loc-note">{e(l['location_note'])}</p>
          </div>
        </div>
        <div class="feature-cta">
          {cta}
          <div class="brokerage">Brokerage {e(site['brokerage'])}<br>{e(l['brokerage_note'])}</div>
        </div>
      </div>
    </article>"""


def inspiration_block(l, root):
    """Design-inspiration band — reference visuals, clearly not the actual home.
    Rendered on the detail page only, and kept out of the photo lightbox."""
    insp = l.get("inspiration")
    if not insp:
        return ""
    slug = l["slug"]
    tiles = ""
    for g in insp["images"]:
        src = img_path(root, slug, g["img"])
        tiles += (f'<figure><div class="inspo-img" style="background-image:url(\'{src}\')"></div>'
                  f'<figcaption>{e(g["label"])}</figcaption></figure>')
    return f"""
      <div class="inspo reveal">
        <div class="inspo-head">
          <div class="kf-title"><span class="diamond"></span>Design Inspiration</div>
          <p class="inspo-note">{e(insp["note"])}</p>
        </div>
        <div class="inspo-grid">{tiles}</div>
      </div>"""


def amenities_block(l, root):
    """Full amenities showcase — this project's core USP. Data-driven; renders only
    when the listing defines an 'amenities' list of {group, items} categories."""
    ams = l.get("amenities")
    if not ams:
        return ""
    cols, total = "", 0
    for cat in ams:
        items = "".join(f'<li><span class="diamond"></span>{e(it)}</li>' for it in cat["items"])
        total += len(cat["items"])
        cols += f'<div class="am-col"><h4>{e(cat["group"])}</h4><ul>{items}</ul></div>'
    intro = e(l.get("amenities_note", ""))
    return f"""
      <div class="amenities reveal">
        <div class="am-head">
          <div class="kf-title"><span class="diamond"></span>The Amenities · {total} Reasons to Never Leave</div>
          {f'<p class="am-note">{intro}</p>' if intro else ''}
        </div>
        <div class="am-grid">{cols}</div>
      </div>"""


def sizes_block(l, root):
    """Unit-size variants table. Data-driven via optional 'sizes' field:
    {label, note, rows: [{v, l}]} — reuses the rental/ry-stat styling."""
    s = l.get("sizes")
    if not s:
        return ""
    tiles = "".join(f'<div class="ry-stat"><b>{e(r["v"])}</b><small>{e(r["l"])}</small></div>'
                    for r in s.get("rows", []))
    note = e(s.get("note", ""))
    return f"""
      <div class="rental reveal">
        <div class="ry-head">
          <div class="kf-title"><span class="diamond"></span>{e(s.get("label", "Villa Sizes"))}</div>
          {f'<h3>{e(s["headline"])}</h3>' if s.get("headline") else ''}
        </div>
        <div class="ry-stats">{tiles}</div>
        {f'<p class="ry-note">{note}</p>' if note else ''}
      </div>"""


def rental_block(l, root):
    """Rental-yield / investment case. Data-driven via optional 'rental' field."""
    r = l.get("rental")
    if not r:
        return ""
    stats = "".join(f'<div class="ry-stat"><b>{e(s["v"])}</b><small>{e(s["l"])}</small></div>'
                    for s in r.get("stats", []))
    return f"""
      <div class="rental reveal">
        <div class="ry-head">
          <div class="kf-title"><span class="diamond"></span>{e(r.get("label", "The Investment Case"))}</div>
          <h3>{e(r["headline"])}</h3>
        </div>
        <div class="ry-stats">{stats}</div>
        <p class="ry-note">{e(r["note"])}</p>
      </div>"""


def property_card(l, root):
    slug = l["slug"]
    img = img_path(root, slug, l["card_image"])
    specs = "".join(f'<div class="s"><b>{e(s["v"])}</b><small>{e(s["l"])}</small></div>' for s in l["specs"][:3])
    text = f"{l['name']} {l['location']} {l['region']} {l['short']}".lower()
    return f"""
      <article class="pcard" data-location="{e(l['location'].lower())}" data-price="{l['price_value']}" data-beds="{l['beds_value']}" data-text="{e(text)}">
        <a href="{root}properties/{slug}/" class="pcard-imgwrap">
          <div class="pcard-img" style="background-image:url('{img}')"></div>
          <span class="pcard-tag">{e(l['status'])}</span>
          <span class="pcard-loc"><span class="diamond" style="width:5px;height:5px"></span>{e(l['location'])}</span>
        </a>
        <div class="pcard-body">
          <h3>{e(l['name'])}</h3>
          <div class="pcard-price">{e(l['price_display'])} <small>{e(l['price_note'])}</small></div>
          <p class="pcard-desc">{e(l['short'])}</p>
          <div class="pcard-specs">{specs}</div>
          <a href="{root}properties/{slug}/" class="btn-arrow">View details →</a>
        </div>
      </article>"""


# --------------------------------------------------------------------------- #
#  Journal / blog blocks                                                      #
# --------------------------------------------------------------------------- #
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")


def inline(text, root=""):
    """Escape text, then re-enable a tiny safe subset of inline markup:
    **bold** and [label](href). Internal links (starting '/') are rooted."""
    out = e(text)

    def link(m):
        label, href = m.group(1), m.group(2)
        if href.startswith("/"):
            href = root + href.lstrip("/")
        return f'<a href="{href}">{label}</a>'

    out = _LINK_RE.sub(link, out)
    out = _BOLD_RE.sub(r"<strong>\1</strong>", out)
    return out


def blog_img(root, img):
    return f"{root}assets/blog/{img}.jpg"


def render_block(b, root):
    t = b.get("type")
    if t == "h2":
        return f'<h2 class="post-h2"><span class="diamond"></span>{inline(b["text"], root)}</h2>'
    if t == "h3":
        return f'<h3 class="post-h3">{inline(b["text"], root)}</h3>'
    if t == "p":
        return f"<p>{inline(b['text'], root)}</p>"
    if t == "ul":
        items = "".join(f'<li><span class="diamond"></span><span>{inline(i, root)}</span></li>'
                        for i in b["items"])
        return f'<ul class="post-list">{items}</ul>'
    if t == "quote":
        cite = f'<cite>{inline(b["cite"], root)}</cite>' if b.get("cite") else ""
        return f'<blockquote class="post-quote">{inline(b["text"], root)}{cite}</blockquote>'
    if t == "img":
        cap = f'<figcaption>{inline(b["label"], root)}</figcaption>' if b.get("label") else ""
        return (f'<figure class="post-fig"><div class="post-fig-img" '
                f'style="background-image:url(\'{blog_img(root, b["img"])}\')"></div>{cap}</figure>')
    if t == "cta":
        href = b["href"]
        if href.startswith("/"):
            href = root + href.lstrip("/")
        return (f'<div class="post-cta"><p>{inline(b["text"], root)}</p>'
                f'<a href="{href}" class="btn solid"><span>{e(b["label"])}</span></a></div>')
    return ""


def blog_card(p, root, featured=False):
    href = f"{root}journal/{p['slug']}/"
    img = blog_img(root, p["hero_image"])
    cls = "bcard feat" if featured else "bcard"
    return f"""
      <article class="{cls}">
        <a href="{href}" class="bcard-imgwrap">
          <div class="bcard-img" style="background-image:url('{img}')"></div>
          <span class="bcard-cat">{e(p['category'])}</span>
        </a>
        <div class="bcard-body">
          <div class="bcard-meta">{e(p['date_display'])}<span class="dot">·</span>{e(p['read_time'])}</div>
          <h3><a href="{href}">{e(p['title'])}</a></h3>
          <p>{e(p['excerpt'])}</p>
          <a href="{href}" class="btn-arrow">Read article →</a>
        </div>
      </article>"""


# --------------------------------------------------------------------------- #
#  Pages                                                                      #
# --------------------------------------------------------------------------- #
def build_home(site, listings):
    root = ""
    lk = links(root, on_home=True)
    featured = next((l for l in listings if l.get("featured")), listings[0])
    hero_img = img_path(root, featured["slug"], featured["card_image"])
    detail_href = f"{root}properties/{featured['slug']}/"

    strip = """
<div class="strip"><div class="wrap">
  <div class="stat reveal"><span class="num">Engineer</span><span class="lbl">Led by civil engineers</span></div>
  <div class="stat reveal d1"><span class="num">1&nbsp;:&nbsp;1</span><span class="lbl">Boutique advisory</span></div>
  <div class="stat reveal d2"><span class="num">Curated</span><span class="lbl">Signature listings only</span></div>
  <div class="stat reveal d3"><span class="num">North&nbsp;Goa</span><span class="lbl">Prime addresses</span></div>
</div></div>"""

    pillars = """
<section class="sec pillars" id="approach"><div class="wrap">
  <div class="sec-head"><div>
    <div class="lead-mark reveal"><span class="diamond"></span><span class="coord">01 · Our Approach</span></div>
    <h2 class="reveal d1">Three things every<br>client can count on.</h2>
  </div><p class="reveal d2">We exist at the intersection of luxury, trust, and local expertise — the warmth of a boutique with the rigour of an engineering firm.</p></div>
</div><div class="wrap"><div class="pillar-grid">
  <div class="pillar reveal"><span class="idx">i</span><span class="diamond"></span><h3>Premium</h3><p>Curated luxury properties only. We take on a select few listings so each one gets the attention it deserves.</p></div>
  <div class="pillar reveal d1"><span class="idx">ii</span><span class="diamond"></span><h3>Expert</h3><p>Engineer-led technical insight. We assess structure, land, and legality before we ever discuss price.</p></div>
  <div class="pillar reveal d2"><span class="idx">iii</span><span class="diamond"></span><h3>Personal</h3><p>Boutique service, every client. One dedicated advisor from first viewing to final signature.</p></div>
</div></div></section>"""

    featured_section = f"""
<section class="sec props" id="properties"><div class="wrap">
  <div class="sec-head"><div>
    <div class="lead-mark reveal"><span class="diamond"></span><span class="coord">02 · Signature Collection</span></div>
    <h2 class="reveal d1">This month's<br>featured residence.</h2>
  </div><p class="reveal d2">Personally inspected and engineer-verified — structure, title, and land assessed before we ever list it.</p></div>
  {feature_block(featured, root, site, mode='home', detail_href=detail_href)}
  <div class="props-foot reveal">
    <a href="{lk['properties']}" class="btn"><span>View All Properties</span></a>
    <div>More residences from the Signature Collection are added regularly.</div>
  </div>
</div></section>"""

    about_img = img_path(root, featured["slug"], "living")
    about = f"""
<section class="sec about" id="about"><div class="wrap"><div class="about-grid">
  <div class="about-visual reveal">
    <div class="about-img" style="background-image:url('{about_img}')"></div>
    <div class="about-badge"><span class="diamond"></span><p>“Founded by engineers, powered by passion.”</p></div>
  </div>
  <div>
    <div class="lead-mark reveal"><span class="diamond"></span><span class="coord">03 · Who We Are</span></div>
    <h2 class="reveal d1">Goa's most trusted premium real estate partner.</h2>
    <p class="body reveal d2">{e(site['name'])} is a premium boutique brokerage based in Panjim, Goa. Founded and led by licensed civil engineers, we bring a rare combination of technical expertise and deep market intelligence to every transaction.</p>
    <p class="body reveal d2">Where others sell a view, we understand the foundation beneath it — the soil, the title, the structure, and the true worth of a home. That precision is why our clients trust us with Goa's finest properties.</p>
    <div class="about-sign reveal d3"><span class="diamond" style="width:14px;height:14px"></span><div>
      <div class="name">{e(site['name'])}</div><div class="role">Engineer-Led · Panjim, Goa</div>
    </div></div>
  </div>
</div></div></section>"""

    values = """
<section class="sec values"><div class="wrap">
  <div class="lead-mark reveal"><span class="diamond"></span><span class="coord">04 · What Guides Us</span></div>
  <div class="val-grid">
    <div class="val reveal"><span class="n">01</span><h3>Integrity</h3></div>
    <div class="val reveal d1"><span class="n">02</span><h3>Expertise</h3></div>
    <div class="val reveal d2"><span class="n">03</span><h3>Excellence</h3></div>
    <div class="val reveal"><span class="n">04</span><h3>Transparency</h3></div>
    <div class="val reveal d1"><span class="n">05</span><h3>Local Knowledge</h3></div>
    <div class="val reveal d2"><span class="n">06</span><h3>Client-First</h3></div>
  </div>
</div></section>"""

    quote = f"""
<section class="quote"><div class="wrap reveal">
  <span class="mark">”</span>
  <blockquote>{e(featured['short'])}</blockquote>
  <cite>{e(featured['name'])} · {e(featured['collection'])}</cite>
</div></section>"""

    hero = f"""
<section class="hero" id="top">
  <div class="hero-bg" data-img="{hero_img}"></div>
  <div class="hero-veil"></div>
  <span class="frame-tick ft-tl"></span><span class="frame-tick ft-tr"></span>
  <div class="hero-top"><div class="wrap"><div class="hero-inner">
    <span class="eyebrow reveal in">15.49°N · 73.83°E — Panjim, Goa</span>
    <h1 class="reveal in d1">Where luxury meets<br>the <em>Arabian Sea.</em></h1>
    <p class="hero-sub reveal in d2">A boutique brokerage for Goa's finest homes — curated by licensed civil engineers who read a property in blueprints before they sell it in brochures.</p>
    <div class="hero-actions reveal in d3">
      <a href="{lk['properties']}" class="btn solid"><span>Explore Properties</span></a>
      <a href="#contact" class="btn"><span>Schedule a Viewing</span></a>
    </div>
  </div></div></div>
  <div class="hero-scroll"><span>Scroll</span><span class="line"></span></div>
</section>"""

    title = f"{site['name']} — {site['tagline']}"
    desc = ("Mindscape Properties is a premium boutique real estate brokerage in Panjim, Goa. "
            "Engineer-led, curated luxury villas. Where luxury meets the Arabian Sea.")
    org_ld = jsonld({
        "@context": "https://schema.org", "@type": "RealEstateAgent",
        "name": site["name"], "url": abs_url(site),
        "image": abs_url(site, hero_img), "priceRange": "₹₹₹",
        "logo": abs_url(site, "assets/mindscape-logo-dark-600x200.png"),
        "telephone": site["phone_display"], "email": site["email"],
        "areaServed": "Goa, India",
        "address": {"@type": "PostalAddress", "addressLocality": "Panjim",
                    "addressRegion": "Goa", "addressCountry": "IN"},
    })
    seo = seo_tags(site, "", title, desc, abs_url(site, hero_img)) + "\n" + org_ld
    return (head(title, desc, root, extra_head=seo)
            + nav(site, lk, root, active="home")
            + hero + strip + pillars + featured_section + LIGHTBOX
            + about + values + quote + contact_section(site) + footer(site, lk, root)
            + whatsapp_fab(site, WA_GENERIC)
            + "\n</body>\n</html>\n")


def build_listings(site, listings):
    root = "../"
    lk = links(root, on_home=False)

    locs = sorted({l["location"] for l in listings})
    loc_opts = '<option value="">All locations</option>' + "".join(
        f'<option value="{e(x.lower())}">{e(x)}</option>' for x in locs)
    price_opts = "".join(f'<option value="{v}">{e(t)}</option>' for v, t in PRICE_BANDS)
    bed_opts = "".join(f'<option value="{v}">{e(t)}</option>' for v, t in BED_BANDS)
    cards = "".join(property_card(l, root) for l in listings)

    header_block = f"""
<section class="page-header"><div class="glow"></div><div class="wrap">
  <div class="breadcrumb reveal in"><a href="{lk['home']}">Home</a><span class="sep">/</span><span>Properties</span></div>
  <span class="eyebrow reveal in">Signature Collection</span>
  <h1 class="reveal in d1">The <em>Collection.</em></h1>
  <p class="reveal in d2">Every home is personally inspected and engineer-verified — structure, title, and land assessed before it earns a place here.</p>
</div></section>"""

    listings_block = f"""
<section class="listings"><div class="wrap">
  <div class="filters">
    <div class="filter-field grow">
      <label for="f-search">Search</label>
      <input type="search" id="f-search" placeholder="Villa name, area…" autocomplete="off" />
    </div>
    <div class="filter-field"><label for="f-location">Location</label><select id="f-location">{loc_opts}</select></div>
    <div class="filter-field"><label for="f-price">Price</label><select id="f-price">{price_opts}</select></div>
    <div class="filter-field"><label for="f-beds">Bedrooms</label><select id="f-beds">{bed_opts}</select></div>
    <button class="filter-reset" id="f-reset">Reset</button>
  </div>
  <div class="results-count" id="resultsCount"></div>
  <div class="listings-grid" id="listingsGrid">{cards}</div>
  <div class="no-results" id="noResults">
    <h3>No matches — yet.</h3>
    <p>Try widening your filters, or tell us what you're after and we'll source it for you.</p>
  </div>
</div></section>"""

    title = f"Properties — {site['name']}"
    desc = "Browse Mindscape Properties' curated collection of premium villas and homes across Goa. Filter by location, price and bedrooms."
    og_img = abs_url(site, img_path("", listings[0]["slug"], listings[0]["card_image"]))
    seo = seo_tags(site, "properties/", title, desc, og_img)
    return (head(title, desc, root, page_js="listings.js", extra_head=seo)
            + nav(site, lk, root, active="properties", solid=True)
            + header_block + listings_block + contact_section(site) + footer(site, lk, root)
            + whatsapp_fab(site, WA_GENERIC)
            + "\n</body>\n</html>\n")


def build_detail(site, l, listings):
    root = "../../"
    lk = links(root, on_home=False)

    breadcrumb = f"""
<section class="page-header" style="padding-bottom:34px"><div class="glow"></div><div class="wrap">
  <div class="breadcrumb reveal in">
    <a href="{lk['home']}">Home</a><span class="sep">/</span>
    <a href="{lk['properties']}">Properties</a><span class="sep">/</span><span>{e(l['name'])}</span>
  </div>
  <span class="eyebrow reveal in">{e(l['status'])} · {e(l['location'])}, {e(l['region'])}</span>
  <h1 class="reveal in d1">{e(l['name'])}</h1>
  <p class="reveal in d2">{e(l['short'])}</p>
</div></section>"""

    body = f"""
<section class="props" style="padding:70px 0 110px;border-top:0"><div class="wrap">
  {feature_block(l, root, site, mode='detail')}
  {sizes_block(l, root)}
  {amenities_block(l, root)}
  {rental_block(l, root)}
  {inspiration_block(l, root)}
  <div class="props-foot reveal"><a href="{lk['properties']}" class="btn"><span>Back to All Properties</span></a></div>
</div></section>"""

    title = f"{l['name']} — {l['location']}, Goa · {site['name']}"
    desc = l["short"]
    wa_text = (f"Hi Mindscape, I'm interested in {l['name']} (Ref {l['ref']}), "
               f"{l['location']}, {l['region']}. Please share more details.")
    canon = f"properties/{l['slug']}/"
    og_img = abs_url(site, img_path("", l["slug"], l["hero_image"]))
    prod_ld = jsonld({
        "@context": "https://schema.org", "@type": "Residence",
        "name": l["name"], "url": abs_url(site, canon), "image": og_img,
        "description": l["short"],
        "address": {"@type": "PostalAddress", "addressLocality": l["location"],
                    "addressRegion": l["region"], "addressCountry": "IN"},
    })
    seo = seo_tags(site, canon, title, desc, og_img, og_type="article") + "\n" + prod_ld
    return (head(title, desc, root, extra_head=seo)
            + nav(site, lk, root, active="properties", solid=True)
            + breadcrumb + body + LIGHTBOX
            + contact_section(site, property_name=l["name"]) + footer(site, lk, root)
            + whatsapp_fab(site, wa_text)
            + "\n</body>\n</html>\n")


def build_blog_index(site, posts):
    root = "../"
    lk = links(root, on_home=False)

    ordered = sorted(posts, key=lambda p: p["date"], reverse=True)
    featured = next((p for p in ordered if p.get("featured")), ordered[0])
    rest = [p for p in ordered if p["slug"] != featured["slug"]]

    lead = blog_card(featured, root, featured=True)
    cards = "".join(blog_card(p, root) for p in rest)

    header_block = f"""
<section class="page-header"><div class="glow"></div><div class="wrap">
  <div class="breadcrumb reveal in"><a href="{lk['home']}">Home</a><span class="sep">/</span><span>Journal</span></div>
  <span class="eyebrow reveal in">The Journal</span>
  <h1 class="reveal in d1">Notes on buying<br>well <em>in Goa.</em></h1>
  <p class="reveal in d2">Guides, area intelligence and hard-won due-diligence lessons from an engineer-led brokerage — so you buy on this coast with clarity, not guesswork.</p>
</div></section>"""

    body = f"""
<section class="journal"><div class="wrap">
  <div class="journal-lead reveal">{lead}</div>
  <div class="journal-grid">{cards}</div>
</div></section>"""

    title = f"Journal — Goa Property Guides & Insights · {site['name']}"
    desc = ("Expert guides on buying property in Goa — NRI eligibility, RERA, title and "
            "due diligence, North vs South Goa, and choosing villas, apartments or plots.")
    breadcrumbs = jsonld({
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": abs_url(site)},
            {"@type": "ListItem", "position": 2, "name": "Journal", "item": abs_url(site, "journal/")},
        ],
    })
    blog_ld = jsonld({
        "@context": "https://schema.org", "@type": "Blog",
        "name": f"{site['name']} Journal", "url": abs_url(site, "journal/"),
        "description": desc,
        "blogPost": [{
            "@type": "BlogPosting", "headline": p["title"],
            "url": abs_url(site, f"journal/{p['slug']}/"),
            "datePublished": p["date"], "description": p["excerpt"],
        } for p in ordered],
    })
    seo = seo_tags(site, "journal/", title, desc,
                   abs_url(site, blog_img("", featured["hero_image"]))) + "\n" + breadcrumbs + "\n" + blog_ld
    return (head(title, desc, root, extra_head=seo)
            + nav(site, lk, root, active="journal", solid=True)
            + header_block + body + contact_section(site) + footer(site, lk, root)
            + whatsapp_fab(site, WA_GENERIC)
            + "\n</body>\n</html>\n")


def build_post(site, post, posts):
    root = "../../"
    lk = links(root, on_home=False)
    slug = post["slug"]

    article = "".join(render_block(b, root) for b in post["body"])

    takeaways = ""
    if post.get("key_takeaways"):
        items = "".join(f'<li><span class="diamond"></span><span>{inline(t, root)}</span></li>'
                        for t in post["key_takeaways"])
        takeaways = f"""
      <aside class="post-takeaways">
        <div class="kf-title"><span class="diamond"></span>Key Takeaways</div>
        <ul>{items}</ul>
      </aside>"""

    faqs_html = ""
    if post.get("faqs"):
        rows = "".join(
            f'<div class="faq"><h3>{inline(f["q"], root)}</h3><p>{inline(f["a"], root)}</p></div>'
            for f in post["faqs"])
        faqs_html = f"""
      <div class="post-faqs">
        <div class="kf-title"><span class="diamond"></span>Frequently Asked</div>
        {rows}
      </div>"""

    # Up to two related posts (most recent others)
    others = [p for p in sorted(posts, key=lambda p: p["date"], reverse=True) if p["slug"] != slug][:2]
    related = ""
    if others:
        related = f"""
<section class="journal related"><div class="wrap">
  <div class="lead-mark reveal"><span class="diamond"></span><span class="coord">More from the Journal</span></div>
  <div class="journal-grid">{"".join(blog_card(p, root) for p in others)}</div>
</div></section>"""

    hero = blog_img(root, post["hero_image"])
    breadcrumb = f"""
<section class="page-header post-header"><div class="glow"></div><div class="wrap">
  <div class="breadcrumb reveal in">
    <a href="{lk['home']}">Home</a><span class="sep">/</span>
    <a href="{lk['journal']}">Journal</a><span class="sep">/</span><span>{e(post['category'])}</span>
  </div>
  <span class="eyebrow reveal in">{e(post['category'])}</span>
  <h1 class="reveal in d1">{e(post['title'])}</h1>
  <div class="post-meta reveal in d2">
    <span>{e(post['date_display'])}</span><span class="dot">·</span><span>{e(post['read_time'])}</span>
    <span class="dot">·</span><span>{e(site['name'])}</span>
  </div>
</div></section>"""

    body = f"""
<section class="post"><div class="wrap">
  <div class="post-hero reveal" style="background-image:url('{hero}')"></div>
  <div class="post-shell">
    <article class="post-body reveal">
      <p class="post-lede">{inline(post['excerpt'], root)}</p>
      {takeaways}
      {article}
      {faqs_html}
      <div class="post-sign">
        <span class="diamond"></span>
        <div><div class="name">{e(site['name'])}</div>
        <div class="role">Engineer-led advisory · Panjim, Goa</div></div>
      </div>
    </article>
  </div>
</div></section>
{related}"""

    title = f"{post['title']} · {site['name']}"
    desc = post["excerpt"]
    img_abs = abs_url(site, blog_img("", post["hero_image"]))
    posting = {
        "@context": "https://schema.org", "@type": "BlogPosting",
        "headline": post["title"], "description": desc,
        "image": img_abs, "datePublished": post["date"], "dateModified": post["date"],
        "articleSection": post["category"],
        "keywords": post.get("keywords", ""),
        "mainEntityOfPage": abs_url(site, f"journal/{slug}/"),
        "author": {"@type": "Organization", "name": site["name"]},
        "publisher": {"@type": "Organization", "name": site["name"],
                      "logo": {"@type": "ImageObject",
                               "url": abs_url(site, "assets/mindscape-logo-dark-600x200.png")}},
    }
    crumbs = {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": abs_url(site)},
            {"@type": "ListItem", "position": 2, "name": "Journal", "item": abs_url(site, "journal/")},
            {"@type": "ListItem", "position": 3, "name": post["title"],
             "item": abs_url(site, f"journal/{slug}/")},
        ],
    }
    ld = jsonld(posting) + "\n" + jsonld(crumbs)
    if post.get("faqs"):
        faq_ld = {
            "@context": "https://schema.org", "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": f["q"],
                            "acceptedAnswer": {"@type": "Answer", "text": f["a"]}}
                           for f in post["faqs"]],
        }
        ld += "\n" + jsonld(faq_ld)
    seo = seo_tags(site, f"journal/{slug}/", title, desc, img_abs, og_type="article") + "\n" + ld
    return (head(title, desc, root, extra_head=seo)
            + nav(site, lk, root, active="journal", solid=True)
            + breadcrumb + body + contact_section(site) + footer(site, lk, root)
            + whatsapp_fab(site, WA_GENERIC)
            + "\n</body>\n</html>\n")


def build_sitemap(site, listings, posts):
    urls = ["", "properties/", "journal/"]
    urls += [f"properties/{l['slug']}/" for l in listings]
    urls += [f"journal/{p['slug']}/" for p in posts]
    body = "".join(f"  <url><loc>{e(abs_url(site, u))}</loc></url>\n" for u in urls)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f"{body}</urlset>\n")


def build_robots(site):
    return ("User-agent: *\n"
            "Allow: /\n\n"
            f"Sitemap: {abs_url(site, 'sitemap.xml')}\n")


# --------------------------------------------------------------------------- #
def write(path, content):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  ✓ {os.path.relpath(path, ROOT_DIR)}")


def main():
    with open(DATA_FILE, encoding="utf-8") as f:
        data = json.load(f)
    site, listings = data["site"], data["listings"]
    global GA_ID, GTM_ID
    GA_ID = site.get("ga_id", "")
    GTM_ID = site.get("gtm_id", "")
    if not listings:
        sys.exit("No listings found in data/listings.json")

    posts = []
    if os.path.exists(BLOG_FILE):
        with open(BLOG_FILE, encoding="utf-8") as f:
            posts = json.load(f).get("posts", [])

    print(f"Building {site['name']} — {len(listings)} listing(s), {len(posts)} post(s):")
    write(os.path.join(ROOT_DIR, "index.html"), build_home(site, listings))
    write(os.path.join(ROOT_DIR, "properties", "index.html"), build_listings(site, listings))
    for l in listings:
        write(os.path.join(ROOT_DIR, "properties", l["slug"], "index.html"),
              build_detail(site, l, listings))

    if posts:
        write(os.path.join(ROOT_DIR, "journal", "index.html"), build_blog_index(site, posts))
        for p in posts:
            write(os.path.join(ROOT_DIR, "journal", p["slug"], "index.html"),
                  build_post(site, p, posts))

    write(os.path.join(ROOT_DIR, "sitemap.xml"), build_sitemap(site, listings, posts))
    write(os.path.join(ROOT_DIR, "robots.txt"), build_robots(site))
    print("Done.")


if __name__ == "__main__":
    main()
