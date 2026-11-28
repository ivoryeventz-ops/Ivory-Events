#!/usr/bin/env python3
"""Ivory Events - "New A" site generator.

Run from anywhere:
    python3 "New A/generate.py"          rebuild everything (parts, root page, every client)
    python3 "New A/generate.py" Navin    rebuild only that client

Inputs
    ../A/packages.html, ../A/checklist.html     the existing pages (kept as they are)
    <Client>/data.json                          name, wedding_date (ISO), venue, quotes[{id, created, url?}],
                                                timeline{url}, payment{url} (the last two are optional extra tabs)
    quotes/<Client>/<YYMMDD>.json               optional spec-driven quotes (test client only)
    templates/quote.css, complimentary.html     Abraham quote theme (standing style rule)

Outputs
    parts/packages.html, parts/checklist.html   embed-ready copies of the A pages
    index.html                                  generic page (Intro / Packages / Checklist)
    client-shell.html                           template the Quote Builder app copies for new clients
    <Client>/index.html                         the ONE link for that client; reads data.json, so
                                                newest quote tab first, older ones (by date) next,
                                                then Intro, Packages, Checklist
    packages/<Client>/<YYMMDD>.html             standalone copy of every quote
"""
import datetime
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
A_DIR = ROOT.parent / "A"
SITE = "https://ivory-events.pages.dev/New%20A"
WA_NUM = "919846116300"


# ---------------------------------------------------------------- helpers
def esc(s):
    return html.escape(s, quote=False)


def inr(n):
    s = str(int(n))
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    head = re.sub(r"(\d)(?=(\d\d)+$)", r"\1,", head)
    return head + "," + tail


def short_date(iso):
    d = datetime.date.fromisoformat(iso)
    return f"{d.day} {d.strftime('%b %Y')}"


def long_date(iso):
    d = datetime.date.fromisoformat(iso)
    return f"{d.day} {d.strftime('%B %Y')}"


# ---------------------------------------------------------------- parts (A pages made embeddable)
EMBED_CSS = (
    "<style>/* embedded inside the New A tabs: the tab bar replaces the header/nav/footer */\n"
    ".site-header,.ivory-nav,footer{display:none!important}\n"
    "main{padding-top:1.1rem}</style>"
)
EMBED_JS = (
    "<script>document.addEventListener('click',function(e){var a=e.target.closest('a[data-tab]');"
    "if(a){e.preventDefault();parent.postMessage({ivoryTab:a.getAttribute('data-tab')},'*');}});</script>"
)


# Event types offered when a new enquiry is entered in the Enquiries app.
#   key -> (label, source folder of the package/checklist pages, parts sub-folder, wording swaps)
# Marthoma, Orthodox and CSI use the original parts/ files (built from ../A), as does the older "christian" type.
# The others live in parts/<sub>/. Pentecost uses the P items inside the same New A look. The rest use the E items;
# both receptions share one folder, and Hindu - Mandap also gets the pooja items after Sofa.
POOJA_ITEMS = ["Vilakku 5", "Para", "Nellu", "Kindi", "Korandi", "Thorthu", "Vazha ila", "Vetta, paak, coin",
               "Thalam", "Ashtamangalyam, tulsi", "Kai villaku", "Peedom", "Mandap", "Fruit thalam",
               "Ganapathy orukkam items (aval, malar, sharkara, sambrani, kalabam, panineer, rose petals or arali)"]
POOJA_HTML = ("      <li>Sofa</li>\n      <li>Pooja items:\n        <ul>\n"
              + "".join(f"          <li>{i}</li>\n" for i in POOJA_ITEMS)
              + "        </ul>\n        (<strong>Without</strong> Chotta/Thenginpukola)\n      </li>\n")


def titled(name):
    return [("Engagement Package", name + " Package")]


# Pentecost: the P pages, with this stage decoration list in place of the P one.
P_INCLUSIONS = ['White flex or carpet on stage', 'Sofa', 'Welcome drink for couple', 'Single layer fresh cream cake', 'Fresh leaves on stage', 'Stage floral settings artificial', 'Stage lights and facelights', 'Stage sound system', 'Centre carpet along aisle', 'Hall entrance arch artificial', 'Wedding car decoration fresh', 'Greeting bouquet - 2 nos. - fresh flowers', 'Wedding signage board', '2 welcome hostesses']
PENTECOST_INCLUSIONS = ['White flex or carpet on stage', 'Table for Pastors', 'Chairs for Pastors', 'Podium', 'Sofa', 'Single layer fresh cream cake', 'Fresh leaves on stage', 'Stage floral settings artificial', 'Stage lights and facelights', 'Centre carpet along aisle', 'Hall entrance arch artificial', 'Wedding car decoration fresh', 'Greeting bouquet - 2 nos. - fresh flowers', 'Wedding signage board', '2 welcome hostesses']


def li_lines(items):
    return "".join(f"      <li>{i}</li>\n" for i in items)


TYPES = {
    "marthoma": ("Marthoma", "A", "", []),
    "orthodox": ("Orthodox", "A", "", []),
    "pentecost": ("Pentecost", "P", "pentecost",
                  [(li_lines(P_INCLUSIONS), li_lines(PENTECOST_INCLUSIONS))]),
    "csi": ("CSI", "A", "", []),
    "engagement": ("Engagement", "E", "engagement", []),
    "mylanchi": ("Maduramveppu / Mylanchi", "E", "mylanchi", titled("Maduramveppu / Mylanchi")),
    "creception": ("Christian - Reception", "E", "hindu", titled("Reception")),
    "hindumandap": ("Hindu - Mandap", "E", "hindumandap",
                    titled("Hindu Mandap") + [("      <li>Sofa</li>\n", POOJA_HTML)]),
    "hindu": ("Hindu - Reception", "E", "hindu", titled("Reception")),
}


# Extra client sites. Each has its own general page, client-shell.html and client folders, and works like New A.
# The Packages / Checklist pages are shared from New A/parts/, so changing a client's event type never changes their link.
#   folder -> the parts sub-folder its general page shows
EXTRA_SITES = {"New E": "engagement", "New P": "pentecost"}
PARTS_URL = "/New%20A/parts/"


def build_site(folder):
    default = EXTRA_SITES[folder] + "/"
    out = ROOT.parent / folder
    out.mkdir(exist_ok=True)
    (out / "logo.png").write_bytes((ROOT / "logo.png").read_bytes())
    for mode, fname in (("root", "index.html"), ("client", "client-shell.html")):
        page = build_page(mode).replace(SITE, SITE.replace("New%20A", folder.replace(" ", "%20")))
        prefix = "../" if mode == "client" else ""
        for part in ("packages", "checklist"):
            page = page.replace(f'data-src="{prefix}parts/{part}.html"', f'data-src="{PARTS_URL}{default}{part}.html"')
        page = page.replace("fr.setAttribute('data-src', '../parts/' + PT + k + '.html');",
                            f"fr.setAttribute('data-src', '{PARTS_URL}' + (d.type ? PT : '{default}') + k + '.html');")
        (out / fname).write_text(page, encoding="utf-8")


def build_part(name, src_folder="A", sub="", swaps=()):
    src = (ROOT.parent / src_folder / f"{name}.html").read_text(encoding="utf-8")
    for old, new in swaps:
        src = src.replace(old, new)
    src = src.replace("<head>", f'<head>\n<base href="/{src_folder}/">', 1)
    src = src.replace("</head>", EMBED_CSS + "\n</head>", 1)
    if name == "packages":   # tick-list view (no photos, no rates) for clients switched to it
        src = src.replace("</head>", '<script src="/New%20A/parts/listview.js"></script>\n</head>', 1)
    for page, tab in (("packages", "packages"), ("checklist", "checklist"), ("index", "intro"),
                      ("reviews", "intro"), ("gallery", "intro")):
        src = src.replace(f'href="{page}.html"', f'href="#" data-tab="{tab}"')
    src = src.replace("</body>", EMBED_JS + "\n</body>", 1)
    out = ROOT / "parts" / sub / f"{name}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(src, encoding="utf-8")


# ---------------------------------------------------------------- quote page (Abraham theme)
def item_box(it):
    h = ['        <div class="line-item-box">', '          <div class="line-item-info">',
         f'            <div class="line-item-name">{esc(it["name"])}</div>']
    if it.get("subs"):
        h.append('            <ul class="line-item-sublist">')
        h += [f"              <li>{esc(s)}</li>" for s in it["subs"]]
        h.append("            </ul>")
    if it.get("note"):
        h.append(f'            <div class="line-item-note">{esc(it["note"])}</div>')
    h += ["          </div>", f'          <div class="line-item-price">&#8377; {inr(it["price"])}</div>', "        </div>"]
    return "\n".join(h)


def section(title, body):
    return (f'    <div class="section-card">\n      <div class="section-header">\n'
            f'        <span class="section-title">{title}</span>\n      </div>\n{body}\n    </div>\n')


def build_quote(client, spec):
    qid = spec["id"]
    name = esc(client["name"])
    desc = (f'Ivory Events wedding decor quote - {client["wedding_date"]}, {client["venue"]}')
    css = (ROOT / "templates" / "quote.css").read_text(encoding="utf-8")
    comp = (ROOT / "templates" / "complimentary.html").read_text(encoding="utf-8")

    stage = "\n".join(f"        <li>{esc(i)}</li>" for i in spec["stage_inclusions"])
    options = "\n".join(
        f'        <div class="line-item-box">\n          <div class="line-item-info">\n'
        f'            <div class="line-item-name">{esc(n)}</div>\n          </div>\n'
        f'          <div class="line-item-price">&#8377; {inr(p)}</div>\n        </div>'
        for n, p in spec["decor_options"])
    other = "\n".join(item_box(i) for i in spec["other_items"])
    extra = "\n".join(item_box(i) for i in spec["additional_items"])

    body = []
    body.append(f'''    <div class="header-card">
      <h1 class="brand-title">Decor Quote</h1>
      <p class="sub-title">Wedding Decor</p>
      <div class="draft-note">Quote dated {long_date(spec["created"])}</div>

      <div class="info-grid">
        <div class="info-item">
          <div class="info-label">Name</div>
          <div class="info-value">{name}</div>
        </div>
        <div class="info-item">
          <div class="info-label">Date</div>
          <div class="info-value">{esc(client["wedding_date"])}</div>
        </div>
        <div class="info-item">
          <div class="info-label">Venue</div>
          <div class="info-value">{esc(client["venue"])}</div>
        </div>
      </div>
    </div>
''')
    body.append(f'''    <div class="image-card">
      <div class="image-title">Stage Design Concept &amp; Reference</div>
      <div class="image-wrapper">
        <img src="{spec["stage_image"]}" alt="Reference photograph of the proposed wedding stage design - {name}" loading="lazy" decoding="async" />
      </div>
    </div>
''')
    body.append(section("Stage Decoration", f'      <ul class="item-list">\n{stage}\n      </ul>'))
    body.append(section("Stage Decor Options", f'      <div class="line-item-group">\n{options}\n      </div>'))
    body.append(section("Other Items", f'      <div class="line-item-group">\n{other}\n      </div>'))
    body.append(section("Additional Items", f'      <div class="line-item-group">\n{extra}\n      </div>'))
    body.append(comp.rstrip("\n") + "\n")

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Decor Quote - {name}</title>
  <meta property="og:type" content="website" />
  <meta property="og:site_name" content="Ivory Events" />
  <meta property="og:title" content="Decor Quote - {name}" />
  <meta property="og:description" content="{esc(desc)}" />
  <meta property="og:image" content="{SITE}/logo.png" />
  <meta property="og:image:alt" content="Ivory Events logo" />
  <meta name="twitter:card" content="summary" />
  <meta name="twitter:image" content="{SITE}/logo.png" />
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@600;700&family=Montserrat:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
{css}
  </style>
</head>
<body>

  <div class="container">
{"".join(body)}  </div>

</body>
</html>
'''


# ---------------------------------------------------------------- tabbed page
PAGE_CSS = r"""
:root{--bg:#faf8f4;--card:#fff;--ink:#2a2623;--mute:#6b625b;--gold:#b08d57;--gold-hover:#9a7846;--gold-deep:#8f6f3d;--gold-tint:#f6f1e8;--gold-soft:#e6d6b8;--line:#e9e2d6;--on:#fff;--serif:'Cormorant Garamond','Georgia',serif;--sans:'Montserrat',-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;--shadow:0 4px 18px rgba(60,45,20,.05)}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;height:100vh;height:100dvh;display:flex;flex-direction:column;overflow:hidden;background:var(--bg);color:var(--ink);font-family:var(--sans);line-height:1.65;-webkit-font-smoothing:antialiased}

/* top bar + tabs */
.topbar{flex:0 0 auto;background:#fff;border-bottom:1px solid var(--line);box-shadow:0 2px 10px rgba(60,45,20,.04);z-index:10}
.brand{display:flex;align-items:center;gap:.7rem;padding:.55rem 1rem .3rem;max-width:1100px;margin:0 auto}
.brand img{width:34px;height:34px;border-radius:50%;box-shadow:0 0 0 2px #fff,0 0 0 3px var(--gold-soft)}
.brand b{font-family:var(--serif);font-size:1.35rem;font-weight:600;line-height:1}
.brand .for{margin-left:auto;font-size:.72rem;color:var(--mute);text-align:right;line-height:1.3}
.brand .for strong{color:var(--gold-deep);font-weight:600}
.tabs{display:flex;gap:.45rem;overflow-x:auto;padding:.3rem 1rem .65rem;max-width:1100px;margin:0 auto;scrollbar-width:none;-webkit-overflow-scrolling:touch}
.tabs::-webkit-scrollbar{display:none}
.tab{flex:0 0 auto;display:inline-flex;align-items:center;gap:.45rem;padding:.55rem 1.1rem;border-radius:999px;border:1px solid var(--gold-soft);background:#fff;color:var(--gold-deep);font:600 .8rem var(--sans);letter-spacing:.05em;text-transform:uppercase;cursor:pointer;white-space:nowrap;transition:all .2s ease}
.tab .badge{font-size:.6rem;letter-spacing:.1em;padding:.1rem .45rem;border-radius:20px;background:var(--gold);color:#fff}
.tab.active{background:var(--gold);border-color:var(--gold);color:var(--on);box-shadow:0 4px 12px rgba(176,141,87,.28)}
.tab.active .badge{background:#fff;color:var(--gold-deep)}
@media (hover:hover){.tab:not(.active):hover{background:var(--gold-tint);border-color:var(--gold)}}
.tab:focus-visible,.sub-btn:focus-visible,.btn:focus-visible{outline:2px solid var(--gold-deep);outline-offset:2px}

/* panels */
.panels{flex:1 1 auto;position:relative;min-height:0}
.panel{position:absolute;inset:0;display:none;overflow-y:auto;-webkit-overflow-scrolling:touch}
.panel.active{display:block}
.panel iframe{display:block;width:100%;height:100%;border:0;background:var(--bg)}

/* intro tab */
.site-header{text-align:center;padding:2.25rem 1rem 1.6rem;background:linear-gradient(180deg,#fff 0%,#fdfbf7 100%);border-bottom:1px solid var(--line)}
.logo{width:84px;height:84px;border-radius:50%;display:block;margin:0 auto 1rem;box-shadow:0 0 0 3px #fff,0 0 0 4px var(--gold-soft)}
.header-badge,.feature-badge{display:inline-block;background:var(--gold-tint);color:var(--gold-deep);padding:.3rem 1.1rem;border-radius:20px;font-size:.72rem;font-weight:600;text-transform:uppercase;letter-spacing:.18em;border:1px solid var(--gold-soft)}
.header-badge{margin-bottom:.8rem}
.site-header h1{font-family:var(--serif);margin:0;font-size:clamp(2rem,5.5vw,2.8rem);line-height:1.15;font-weight:600}
.site-header p{margin:.6rem auto 0;max-width:560px;color:var(--mute);font-size:.92rem}
.orn{display:flex;align-items:center;justify-content:center;gap:.8rem;margin:1rem auto 0;color:var(--gold);font-size:.8rem;letter-spacing:.4em}
.orn::before,.orn::after{content:"";height:1px;width:56px;background:linear-gradient(90deg,transparent,var(--gold-soft))}
.orn::after{transform:scaleX(-1)}

.client-card{max-width:820px;margin:1.25rem auto 0;padding:0 1rem}
.client-inner{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:1rem 1.1rem 1.1rem;box-shadow:var(--shadow)}
.client-label{font-family:var(--serif);text-transform:uppercase;letter-spacing:.28em;font-size:.8rem;color:var(--gold-deep);font-weight:700;text-align:center;margin:0 0 .7rem}
.info-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:10px}
.info-item{background:#faf7f2;padding:10px 14px;border-radius:6px;border-left:3px solid #c5a059}
.info-label{font-size:.68rem;text-transform:uppercase;font-weight:600;color:#777}
.info-value{font-size:.95rem;font-weight:600}

.subnav{position:sticky;top:0;z-index:5;display:flex;flex-wrap:wrap;justify-content:center;gap:.5rem;padding:.6rem 1rem;margin-top:1.1rem;background:rgba(250,248,244,.96);-webkit-backdrop-filter:blur(6px);backdrop-filter:blur(6px);border-bottom:1px solid var(--line)}
.sub-btn{display:inline-flex;align-items:center;justify-content:center;padding:.5rem 1.2rem;border-radius:999px;border:1px solid var(--gold-soft);background:#fff;color:var(--gold-deep);font:600 .78rem var(--sans);letter-spacing:.06em;text-transform:uppercase;cursor:pointer;transition:all .2s ease}
.sub-btn.active{background:var(--gold);border-color:var(--gold);color:var(--on)}
@media (hover:hover){.sub-btn:not(.active):hover{background:var(--gold-tint);border-color:var(--gold)}}

main{max-width:820px;margin:0 auto;padding:1.25rem 1rem .5rem}
section.block{scroll-margin-top:64px;padding-bottom:1.25rem}
.sec-head{text-align:center;margin:.5rem 0 1.1rem}
.sec-head h2{font-family:var(--serif);font-size:clamp(1.8rem,5vw,2.3rem);font-weight:600;line-height:1.2;margin:.7rem 0 .25rem}
.sec-head p{margin:0;color:var(--mute);font-size:.9rem}
.card{background:var(--card);border:1px solid var(--line);border-left:3px solid var(--gold);border-radius:12px;padding:1.6rem 1.6rem 1.5rem;margin-bottom:1.1rem;box-shadow:var(--shadow)}
.card h2{font-family:var(--serif);font-size:1.55rem;font-weight:600;margin:0 0 .5rem}
.card p{margin:0 0 .6rem;color:var(--mute);font-size:.94rem}
.card p:last-child{margin-bottom:0}
.tick-list{list-style:none;padding:0;margin:.6rem 0 0;display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:.55rem 1rem}
.tick-list li{display:flex;align-items:baseline;gap:.6rem;font-size:.92rem;color:var(--mute)}
.tick-list li::before{content:"\2714";color:var(--gold);font-size:.8rem;font-weight:bold}

.feature-card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:2.75rem 2rem;box-shadow:var(--shadow);display:flex;flex-direction:column;align-items:center;text-align:center}
.feature-title{font-family:var(--serif);font-size:clamp(1.6rem,5vw,2.2rem);font-weight:600;line-height:1.2;margin:0 0 1.25rem}
.g-business-thumb{display:flex;align-items:center;gap:12px;background:#fff;border:1px solid var(--line);padding:10px 18px;border-radius:50px;margin-bottom:1.4rem;box-shadow:0 2px 8px rgba(0,0,0,.04)}
.g-logo{width:24px;height:24px;flex-shrink:0}
.g-thumb-info{text-align:left;line-height:1.25}
.g-thumb-name{font-size:.88rem;font-weight:700}
.g-thumb-meta{font-size:.75rem;color:var(--mute)}
.rating-highlight-box{background:linear-gradient(180deg,#fdfbf7 0%,var(--gold-tint) 100%);border:1px solid var(--gold);border-radius:14px;padding:1.1rem 2rem;margin-bottom:1.5rem;display:flex;flex-direction:column;align-items:center;gap:4px;box-shadow:0 4px 14px rgba(176,141,87,.12)}
.rating-number-stars{display:flex;align-items:center;gap:10px}
.rating-score{font-family:var(--serif);font-size:2.6rem;font-weight:700;line-height:1}
.stars{color:#f5a623;font-size:1.4rem;letter-spacing:2px;line-height:1}
.rating-tag{font-size:.76rem;font-weight:600;color:var(--gold-deep);text-transform:uppercase;letter-spacing:.12em}
.feature-desc{color:var(--mute);font-size:.98rem;max-width:560px;margin:0 0 1.8rem}
.feature-btn{display:inline-flex;align-items:center;gap:.75rem;max-width:100%;background:var(--gold);color:#fff;text-decoration:none;font-weight:600;font-size:.98rem;padding:.95rem 1.9rem;border-radius:8px;box-shadow:0 5px 14px rgba(176,141,87,.28);transition:all .2s ease}
@media (hover:hover){.feature-btn:hover{background:var(--gold-hover);transform:translateY(-2px);box-shadow:0 8px 18px rgba(176,141,87,.34)}}
@media (max-width:520px){.feature-card{padding:2rem 1.25rem}.feature-btn{padding:.9rem 1.25rem}.card{padding:1.3rem 1.2rem}}
.gallery-icon{color:var(--gold);font-size:1.3rem;margin-bottom:1.1rem;letter-spacing:.5em}
.gallery-note{margin-top:1.4rem;font-size:.8rem;color:var(--mute)}
.to-top{display:block;margin:.4rem auto 0;background:none;border:0;color:var(--gold-deep);font:600 .75rem var(--sans);letter-spacing:.1em;text-transform:uppercase;cursor:pointer;padding:.4rem .8rem}
.to-top:hover{text-decoration:underline}
footer{text-align:center;padding:2rem 1rem 2.5rem;color:var(--mute);font-size:.78rem;letter-spacing:.06em}
footer .orn{margin-bottom:.9rem}
.social{display:flex;justify-content:center;gap:1.4rem;margin:0 0 .9rem;flex-wrap:wrap}.social a{color:var(--gold-deep);text-decoration:none;font-weight:600;letter-spacing:.1em;text-transform:uppercase;font-size:.74rem;display:inline-flex;align-items:center;gap:.45rem;padding:.35rem .5rem}.social a:hover{text-decoration:underline}.social svg{width:1.15rem;height:1.15rem;fill:currentColor}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
"""

GOOGLE_G = '''<svg class="g-logo" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
        <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
        <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
        <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" fill="#FBBC05"/>
        <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" fill="#EA4335"/>
      </svg>'''

PAGE_JS = r"""
(function () {
  var body = document.body;
  var DEFAULT = body.getAttribute('data-default');
  var CLIENT = body.getAttribute('data-client') === '1';
  var tabsEl = document.querySelector('.tabs');
  var panelsEl = document.querySelector('.panels');
  var tabs = [];
  var panels = {};
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function show(id, push) {
    if (!panels[id]) id = DEFAULT;
    tabs.forEach(function (t) {
      var on = t.getAttribute('data-tab') === id;
      t.classList.toggle('active', on);
      t.setAttribute('aria-selected', on ? 'true' : 'false');
      if (on && t.scrollIntoView) { try { t.scrollIntoView({ inline: 'center', block: 'nearest' }); } catch (e) {} }
    });
    Object.keys(panels).forEach(function (k) { panels[k].classList.toggle('active', k === id); });
    var f = panels[id].querySelector('iframe[data-src]');
    if (f) { f.src = f.getAttribute('data-src'); f.removeAttribute('data-src'); }
    if (push !== false) { try { history.replaceState(null, '', '#' + id); } catch (e) {} }
  }
  function registerTab(t) {
    tabs.push(t);
    t.addEventListener('click', function () { show(t.getAttribute('data-tab')); });
  }
  [].forEach.call(document.querySelectorAll('.tab'), registerTab);
  [].forEach.call(document.querySelectorAll('.panel'), function (p) { panels[p.getAttribute('data-tab')] = p; });

  [].forEach.call(document.querySelectorAll('[data-open-tab]'), function (a) {
    a.addEventListener('click', function (e) { e.preventDefault(); show(a.getAttribute('data-open-tab')); });
  });
  window.addEventListener('message', function (e) {
    if (e.data && e.data.ivoryTab) show(e.data.ivoryTab);
  });
  window.addEventListener('hashchange', function () { show(location.hash.slice(1), false); });

  /* Intro tab: one page, buttons scroll down to each section and back up */
  var intro = panels.intro;
  var behavior = reduce ? 'auto' : 'smooth';
  var subBtns = [].slice.call(document.querySelectorAll('.sub-btn'));
  function goTo(id) {
    if (id === 'top') { intro.scrollTo({ top: 0, behavior: behavior }); return; }
    var el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: behavior, block: 'start' });
  }
  [].forEach.call(document.querySelectorAll('[data-go]'), function (b) {
    b.addEventListener('click', function (e) { e.preventDefault(); goTo(b.getAttribute('data-go')); });
  });
  function mark(id) {
    subBtns.forEach(function (b) { b.classList.toggle('active', b.getAttribute('data-go') === id); });
  }
  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) { if (en.isIntersecting) mark(en.target.id); });
    }, { root: intro, rootMargin: '-25% 0px -65% 0px', threshold: 0 });
    [].forEach.call(document.querySelectorAll('section.block'), function (s) { io.observe(s); });
  }
  mark('sec-intro');

  /* Client page: name/date/venue and the quote tabs come from data.json next to this page.
     The Quote Builder app edits data.json, so the same link keeps gaining tabs. */
  function fmt(iso, long) {
    var p = String(iso || '').split('-');
    if (p.length !== 3) return iso || '';
    var d = new Date(+p[0], +p[1] - 1, +p[2]);
    return d.toLocaleDateString('en-GB', long ? { day: 'numeric', month: 'long', year: 'numeric' } : { day: 'numeric', month: 'short', year: 'numeric' });
  }
  function el(tag, cls, txt) { var n = document.createElement(tag); if (cls) n.className = cls; if (txt) n.textContent = txt; return n; }

  function loadClient(done) {
    if (!CLIENT) { done(); return; }
    fetch('data.json?t=' + Date.now(), { cache: 'no-store' })
      .then(function (r) { if (!r.ok) throw new Error('data'); return r.json(); })
      .then(function (d) {
        /* event type picks which Packages / Checklist pages load (none, Marthoma, Orthodox or CSI = the original pages) */
        var PT = { pentecost: 'pentecost/', engagement: 'engagement/', mylanchi: 'mylanchi/', creception: 'hindu/', hindumandap: 'hindumandap/', hindu: 'hindu/' }[d.type] || '';
        ['packages', 'checklist'].forEach(function (k) {
          var fr = panels[k] && panels[k].querySelector('iframe[data-src]');
          if (fr) fr.setAttribute('data-src', '../parts/' + PT + k + '.html');
        });
        document.getElementById('cName').textContent = d.name || '';
        document.getElementById('cDate').textContent = fmt(d.wedding_date, true);
        document.getElementById('cVenue').textContent = d.venue || '';
        document.getElementById('clientCard').hidden = false;
        var bf = document.getElementById('brandFor');
        bf.appendChild(document.createTextNode('Prepared for '));
        bf.appendChild(el('strong', '', d.name || ''));
        bf.appendChild(document.createElement('br'));
        bf.appendChild(document.createTextNode(fmt(d.wedding_date, true) + ' · ' + (d.venue || '')));

        var qs = (d.quotes || []).slice().sort(function (a, b) {
          if (a.created !== b.created) return a.created < b.created ? 1 : -1;
          return a.id < b.id ? 1 : -1;
        });
        var perDate = {}, seen = {};
        qs.forEach(function (q) { perDate[q.created] = (perDate[q.created] || 0) + 1; });
        var first = tabsEl.firstChild, latestBtn = null;
        qs.forEach(function (q, i) {
          var tid = 'q' + q.id;
          var label = fmt(q.created, false);
          if (perDate[q.created] > 1) {
            seen[q.created] = (seen[q.created] || 0) + 1;
            label += ' (' + (perDate[q.created] - seen[q.created] + 1) + ')';
          }
          var b = el('button', 'tab', label);
          b.type = 'button'; b.setAttribute('role', 'tab'); b.setAttribute('data-tab', tid);
          b.title = 'Quote prepared on ' + fmt(q.created, true);
          if (i === 0) b.appendChild(el('span', 'badge', 'Latest'));
          tabsEl.insertBefore(b, first);
          registerTab(b);
          var p = el('section', 'panel'); p.id = 'panel-' + tid; p.setAttribute('data-tab', tid); p.setAttribute('role', 'tabpanel');
          var f = el('iframe'); f.title = 'Quote prepared on ' + fmt(q.created, true);
          f.setAttribute('data-src', q.url || ('../packages/' + encodeURIComponent(d.folder) + '/' + encodeURIComponent(q.id) + '.html'));
          p.appendChild(f); panelsEl.appendChild(p); panels[tid] = p;
          if (i === 0) { DEFAULT = tid; latestBtn = b; }
        });
        /* In front of the latest quote: Wedding Timeline, and in front of that, Payment. Each appears only once it has been added to data.json
           (the Enquiries app does that, one item at a time, after Navin confirms it). */
        var ref = latestBtn || first;
        [['timeline', 'Wedding Timeline'], ['payment', 'Payment']].forEach(function (k) {
          var x = d[k[0]];
          if (!x || !x.url) return;
          var b = el('button', 'tab', k[1]);
          b.type = 'button'; b.setAttribute('role', 'tab'); b.setAttribute('data-tab', k[0]);
          tabsEl.insertBefore(b, ref); ref = b;
          registerTab(b);
          var p = el('section', 'panel'); p.id = 'panel-' + k[0]; p.setAttribute('data-tab', k[0]); p.setAttribute('role', 'tabpanel');
          var f = el('iframe'); f.title = k[1];
          f.setAttribute('data-src', x.url);
          p.appendChild(f); panelsEl.appendChild(p); panels[k[0]] = p;
        });
        done();
      })
      .catch(function () { done(); });
  }

  loadClient(function () {
    var h = location.hash.slice(1);
    show(panels[h] ? h : DEFAULT, false);
  });
})();
"""


def intro_panel(dynamic):
    client_card = ""
    if dynamic:
        client_card = '''
    <div class="client-card" id="clientCard" hidden>
      <div class="client-inner">
        <p class="client-label">Prepared for you</p>
        <div class="info-grid">
          <div class="info-item"><div class="info-label">Name</div><div class="info-value" id="cName"></div></div>
          <div class="info-item"><div class="info-label">Date</div><div class="info-value" id="cDate"></div></div>
          <div class="info-item"><div class="info-label">Venue</div><div class="info-value" id="cVenue"></div></div>
        </div>
      </div>
    </div>'''
    return f'''  <section class="panel" id="panel-intro" data-tab="intro" role="tabpanel">
    <header class="site-header">
      <img class="logo" src="__PREFIX__logo.png" alt="Ivory Events logo">
      <span class="header-badge">Since 2011</span>
      <h1>Ivory Events</h1>
      <p>Wedding Planning &amp; Event Management since 2011</p>
      <div class="orn" aria-hidden="true">&#10022;</div>
    </header>{client_card}
    <nav class="subnav" aria-label="Jump to a section">
      <button type="button" class="sub-btn active" data-go="sec-intro">Intro</button>
      <button type="button" class="sub-btn" data-go="sec-reviews">Reviews</button>
      <button type="button" class="sub-btn" data-go="sec-gallery">Gallery</button>
    </nav>
    <main>
      <section class="block" id="sec-intro">
        <div class="card">
          <h2>Welcome</h2>
          <p>A wedding is more than an event. It is a moment that brings families together. We take care of the planning and coordination so that you can focus on being present and enjoying your celebration.</p>
        </div>
        <div class="card">
          <h2>Our Experience</h2>
          <p>Since 2011, we have created and coordinated weddings across Kerala, bringing wedding planning, d&eacute;cor and event management together under one team.</p>
        </div>
        <div class="card">
          <h2>NRI Wedding Support</h2>
          <p>Planning a Kerala wedding from abroad? We act as your on-the-ground team, coordinating vendors and overseeing the arrangements so you can plan with confidence.</p>
        </div>
        <div class="card">
          <h2>What We Do</h2>
          <ul class="tick-list">
            <li>Wedding planning</li>
            <li>D&eacute;cor</li>
            <li>Vendor coordination</li>
            <li>Ceremony management</li>
            <li>Reception management</li>
            <li>On-the-day coordination</li>
          </ul>
        </div>
        <div class="card">
          <h2>Our Promise</h2>
          <p>A wedding brings people together. We handle the details so your family can celebrate and make memories.</p>
        </div>
      </section>

      <section class="block" id="sec-reviews">
        <div class="sec-head">
          <span class="feature-badge">Verified Testimonials</span>
          <h2>Client Feedback &amp; Reviews</h2>
          <p>What families say about celebrating with Ivory Events</p>
        </div>
        <div class="feature-card">
          <div class="g-business-thumb">
            {GOOGLE_G}
            <div class="g-thumb-info">
              <div class="g-thumb-name">Ivory Events</div>
              <div class="g-thumb-meta">Google Business Profile &bull; Wedding Planner</div>
            </div>
          </div>
          <div class="rating-highlight-box">
            <div class="rating-number-stars">
              <span class="rating-score">5.0</span>
              <span class="stars" role="img" aria-label="5 out of 5 stars">&#9733;&#9733;&#9733;&#9733;&#9733;</span>
            </div>
            <span class="rating-tag">Top-Rated Service &bull; 100% Client Satisfaction</span>
          </div>
          <p class="feature-desc">Read first-hand experiences, ratings, and reviews from families and couples who trusted us with their special celebrations.</p>
          <a href="https://maps.app.goo.gl/WSkQMiq3MTGtXUp79" target="_blank" rel="noopener noreferrer" class="feature-btn"><span>&#128073; Ivory Events Google Business Page</span></a>
        </div>
        <button type="button" class="to-top" data-go="top">&uarr; Back to top</button>
      </section>

      <section class="block" id="sec-gallery">
        <div class="sec-head">
          <span class="feature-badge">Photo Portfolio</span>
          <h2>Our Gallery</h2>
          <p>Stage designs, ceremonies, entries and floral setups</p>
        </div>
        <div class="feature-card">
          <h3 class="feature-title">View a Sample of Our Past Events</h3>
          <div class="gallery-icon" aria-hidden="true">&#10022; &#10022; &#10022;</div>
          <p class="feature-desc">Explore our curated collection of stage designs, church ceremonies, bridal entries, and floral setups in high resolution.</p>
          <a href="https://photos.app.goo.gl/G5nyMtNpj78S9HgY9" target="_blank" rel="noopener noreferrer" class="feature-btn"><span>&#128073; Ivory Events Google Photos Album</span></a>
          <div class="gallery-note">Opens in Google Photos for full high-resolution viewing</div>
        </div>
        <button type="button" class="to-top" data-go="top">&uarr; Back to top</button>
      </section>
    </main>
    <footer>
      <div class="orn" aria-hidden="true">&#10022;</div>
      <div class="social">
        <a href="https://www.instagram.com/ivoryeventsweddings" target="_blank" rel="noopener noreferrer" aria-label="Ivory Events on Instagram"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 7.2A4.8 4.8 0 1 0 12 16.8 4.8 4.8 0 0 0 12 7.2zm0 7.9a3.1 3.1 0 1 1 0-6.2 3.1 3.1 0 0 1 0 6.2zM17.3 6a1.1 1.1 0 1 0 0 2.2 1.1 1.1 0 0 0 0-2.2zM12 2.2c-3.2 0-3.6 0-4.8.1-1.3.1-2.1.3-2.9.6a5.8 5.8 0 0 0-2.1 1.4A5.8 5.8 0 0 0 .8 6.4c-.3.8-.5 1.6-.6 2.9C.1 10.4.1 10.8.1 12s0 1.6.1 2.8c.1 1.3.3 2.1.6 2.9.3.8.7 1.5 1.4 2.1.6.7 1.3 1.1 2.1 1.4.8.3 1.6.5 2.9.6 1.2.1 1.6.1 4.8.1s3.6 0 4.8-.1c1.3-.1 2.1-.3 2.9-.6a5.8 5.8 0 0 0 2.1-1.4 5.8 5.8 0 0 0 1.4-2.1c.3-.8.5-1.6.6-2.9.1-1.2.1-1.6.1-4.8s0-3.6-.1-4.8c-.1-1.3-.3-2.1-.6-2.9a5.8 5.8 0 0 0-1.4-2.1A5.8 5.8 0 0 0 19.6 .9c-.8-.3-1.6-.5-2.9-.6C15.6.2 15.2.2 12 .2zm0 1.7c3.1 0 3.5 0 4.7.1 1.1.1 1.7.2 2.1.4.5.2.9.4 1.3.9.4.4.7.8.9 1.3.2.4.3 1 .4 2.1.1 1.2.1 1.6.1 4.7s0 3.5-.1 4.7c-.1 1.1-.2 1.7-.4 2.1-.2.5-.4.9-.9 1.3-.4.4-.8.7-1.3.9-.4.2-1 .3-2.1.4-1.2.1-1.6.1-4.7.1s-3.5 0-4.7-.1c-1.1-.1-1.7-.2-2.1-.4-.5-.2-.9-.4-1.3-.9-.4-.4-.7-.8-.9-1.3-.2-.4-.3-1-.4-2.1C1.9 15.5 1.9 15.1 1.9 12s0-3.5.1-4.7c.1-1.1.2-1.7.4-2.1.2-.5.4-.9.9-1.3.4-.4.8-.7 1.3-.9.4-.2 1-.3 2.1-.4C8.5 1.9 8.9 1.9 12 1.9z"/></svg><span>Instagram</span></a>
        <a href="https://www.facebook.com/ivoryevents" target="_blank" rel="noopener noreferrer" aria-label="Ivory Events on Facebook"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M24 12a12 12 0 1 0-13.9 11.9v-8.4H7.1V12h3V9.4c0-3 1.8-4.7 4.5-4.7 1.3 0 2.7.2 2.7.2v3h-1.5c-1.5 0-2 .9-2 1.9V12h3.4l-.5 3.5h-2.9v8.4A12 12 0 0 0 24 12z"/></svg><span>Facebook</span></a>
      </div>
      Ivory Events &middot; Wedding Planning &amp; Event Management
    </footer>
  </section>
'''


def build_page(mode):
    """mode 'root' = generic page; mode 'client' = shell template (tokens in the head, data.json fills the rest).
    A client page always opens on its newest quote tab; with no quotes yet it opens on Intro."""
    client = mode == "client"
    prefix = "../" if client else ""
    tab_btns = ['<button type="button" class="tab" role="tab" data-tab="intro">Intro</button>',
                '<button type="button" class="tab" role="tab" data-tab="packages">Packages</button>',
                '<button type="button" class="tab" role="tab" data-tab="checklist">Service Checklist</button>']
    panels = [intro_panel(client).replace("__PREFIX__", prefix),
              f'  <section class="panel" id="panel-packages" data-tab="packages" role="tabpanel">\n'
              f'    <iframe title="Packages" data-src="{prefix}parts/packages.html"></iframe>\n  </section>\n',
              f'  <section class="panel" id="panel-checklist" data-tab="checklist" role="tabpanel">\n'
              f'    <iframe title="Service Checklist" data-src="{prefix}parts/checklist.html"></iframe>\n  </section>\n']
    if client:
        title = "Ivory Events - __NAME__"
        og_desc = "Ivory Events wedding planning and decor - __WEDDING_DATE__, __VENUE__"
        url = f"{SITE}/__FOLDER__/"
        for_html = '<div class="for" id="brandFor"></div>'
    else:
        title = "Ivory Events | Wedding Planning & Event Management"
        og_desc = "Ivory Events: wedding planning, décor and event management across Kerala since 2011."
        url = f"{SITE}/"
        for_html = ""
    t, d = html.escape(title, quote=False).replace("&amp;", "&amp;"), html.escape(og_desc)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="robots" content="noindex">
<title>{t}</title>
<meta name="description" content="{d}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Ivory Events">
<meta property="og:url" content="{url}">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{d}">
<meta property="og:image" content="{SITE}/logo.png">
<meta property="og:image:type" content="image/png">
<meta property="og:image:width" content="300">
<meta property="og:image:height" content="300">
<meta property="og:image:alt" content="Ivory Events logo">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{html.escape(title)}">
<meta name="twitter:description" content="{d}">
<meta name="twitter:image" content="{SITE}/logo.png">
<link rel="icon" href="{prefix}logo.png" type="image/png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&family=Montserrat:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>{PAGE_CSS}</style>
</head>
<body data-default="intro" data-client="{1 if client else 0}">
<div class="topbar">
  <div class="brand"><img src="{prefix}logo.png" alt=""><b>Ivory Events</b>{for_html}</div>
  <div class="tabs" role="tablist" aria-label="Pages">
    {chr(10).join("    " + b for b in tab_btns).strip()}
  </div>
</div>
<div class="panels">
{"".join(panels)}</div>
<script>{PAGE_JS}</script>
</body>
</html>
"""


def render_shell(template, data):
    """Same token substitution the Quote Builder app does when it creates a client page."""
    return (template.replace("__NAME__", esc(data["name"]))
            .replace("__WEDDING_DATE__", long_date(data["wedding_date"]))
            .replace("__VENUE__", esc(data["venue"]))
            .replace("__FOLDER__", data["folder"]))


# ---------------------------------------------------------------- main
def build_client(folder, template):
    cdir = ROOT / folder
    dpath = cdir / "data.json"
    data = json.loads(dpath.read_text(encoding="utf-8"))
    data["folder"] = folder
    # optional spec-driven quotes (used for the Navin test); app-made quotes are plain html files
    specs = sorted((ROOT / "quotes" / folder).glob("*.json")) if (ROOT / "quotes" / folder).exists() else []
    if specs:
        client = {"name": data["name"], "wedding_date": long_date(data["wedding_date"]), "venue": data["venue"]}
        outdir = ROOT / "packages" / folder
        outdir.mkdir(parents=True, exist_ok=True)
        known = {q["id"] for q in data.get("quotes", [])}
        for p in specs:
            q = json.loads(p.read_text(encoding="utf-8"))
            (outdir / f"{q['id']}.html").write_text(build_quote(client, q), encoding="utf-8")
            if q["id"] not in known:
                data.setdefault("quotes", []).append({"id": q["id"], "created": q["created"]})
    dpath.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (cdir / "index.html").write_text(render_shell(template, data), encoding="utf-8")
    print(f"{folder}: {len(data.get('quotes', []))} quote(s)")


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    if not only:
        for _key, (_label, _src, _sub, _swaps) in TYPES.items():
            for n in ("packages", "checklist"):
                build_part(n, _src, _sub, _swaps)
        (ROOT / "index.html").write_text(build_page("root"), encoding="utf-8")
        for site in EXTRA_SITES:
            build_site(site)
    template = build_page("client")
    (ROOT / "client-shell.html").write_text(template, encoding="utf-8")
    for p in sorted(ROOT.glob("*/data.json")):
        if only and p.parent.name != only:
            continue
        if "moved_to" in json.loads(p.read_text(encoding="utf-8")):
            continue                      # an old link that now redirects: leave its page alone
        build_client(p.parent.name, template)


if __name__ == "__main__":
    main()
