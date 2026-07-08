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
import sys
import urllib.parse

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(ROOT_DIR, "data", "listings.json")

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
        "about": "#about" if on_home else f"{root}#about",
        "approach": "#approach" if on_home else f"{root}#approach",
        "contact": "#contact",
    }


# Bump ASSET_VER whenever site.css / site.js change, so browsers re-fetch
# them instead of serving a stale cached copy.
ASSET_VER = "5"


def head(title, desc, root, page_js=""):
    v = ASSET_VER
    extra = (f'<script defer src="{root}assets/js/{page_js}?v={v}"></script>' if page_js else "")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}" />
{FONTS}
<link rel="stylesheet" href="{root}assets/css/site.css?v={v}" />
<script defer src="{root}assets/js/site.js?v={v}"></script>
{extra}
</head>
<body>"""


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
            <div class="kf-title"><span class="diamond"></span>Why this villa</div>
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
    return (head(title, desc, root)
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
    return (head(title, desc, root, page_js="listings.js")
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
  {inspiration_block(l, root)}
  <div class="props-foot reveal"><a href="{lk['properties']}" class="btn"><span>Back to All Properties</span></a></div>
</div></section>"""

    title = f"{l['name']} — {l['location']}, Goa · {site['name']}"
    desc = l["short"]
    wa_text = (f"Hi Mindscape, I'm interested in {l['name']} (Ref {l['ref']}), "
               f"{l['location']}, {l['region']}. Please share more details.")
    return (head(title, desc, root)
            + nav(site, lk, root, active="properties", solid=True)
            + breadcrumb + body + LIGHTBOX
            + contact_section(site, property_name=l["name"]) + footer(site, lk, root)
            + whatsapp_fab(site, wa_text)
            + "\n</body>\n</html>\n")


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
    if not listings:
        sys.exit("No listings found in data/listings.json")

    print(f"Building {site['name']} — {len(listings)} listing(s):")
    write(os.path.join(ROOT_DIR, "index.html"), build_home(site, listings))
    write(os.path.join(ROOT_DIR, "properties", "index.html"), build_listings(site, listings))
    for l in listings:
        write(os.path.join(ROOT_DIR, "properties", l["slug"], "index.html"),
              build_detail(site, l, listings))
    print("Done.")


if __name__ == "__main__":
    main()
