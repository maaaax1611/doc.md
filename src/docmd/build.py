"""Builds a docs site from Markdown pages and figure files.

Source directory (default: docs/):
  site.yml                      title, language, categories, texts of the start page
  pages/<category>/<page>.md    page content (Markdown with formulas); pages/<page>.md works too
  figures/<slug>.html           a figure: markup plus optional <script>, placed with "::: widget <slug>"
  lib/                          your own figure libraries (<name>.js / <name>.css) and theme overrides
  static/                       copied to the output as is (images, downloads)

Output directory (default: site/):
  index.html                    start page, reads manifest.json
  <category>/<page>.html        pages
  widgets/<slug>.html           every figure on its own, for embedding
  assets/                       theme files and everything from lib/
  manifest.json                 categories, pages, figures

Markdown:
  Front matter    title, desc, tags, order, group, eyebrow, footer (HTML allowed),
                  toc_intro (entry "0" in the table of contents), libs
  ## Title {#id}  a section. More attributes, all optional:
                    group="…"     sub-heading in the table of contents from here on
                    eyebrow="…"   small heading above the title (default: current group)
                    toc="…"       shorter title for the table of contents
                    n="…"         own number instead of the automatic one (e.g. "→" or "01")
                    level="3"     depth indicator with 5 dots instead of a number
                    appendix="A"  appendix: no number, eyebrow "Appendix A"
  > [!abstract] Key points        box with a heading (Obsidian callout syntax)
  > [!note]                       side note
  ::: widget <slug>               figure at this position
  ::: widget <slug> part=2        only the 2nd <figure> of a figure file with several parts
  $…$, $$…$$                      formulas (MathJax)
"""

from __future__ import annotations

import html
import json
import re
import shutil
from pathlib import Path

import markdown
import yaml
from bs4 import BeautifulSoup

from docmd.labels import labels_for

THEME = Path(__file__).resolve().parent / "theme"
CALLOUT = re.compile(r"^> \[!(\w+)\][ \t]*(.*)\n((?:>.*(?:\n|$))*)", re.M)
WIDGET = re.compile(r"^::: *widget +([\w-]+)(?: +part=(\d+))? *$", re.M)
CAPTION = re.compile(r"<b>(?:Abb|Fig)\.([^<]*)</b>")
DEFAULT_HEIGHT = 640


class BuildError(Exception):
    """A problem in the sources that the author has to fix."""


def esc(s) -> str:
    return html.escape(str(s), quote=True)


# ---------- site ----------
class Site:
    def __init__(self, src: Path, out: Path):
        self.src, self.out = src, out
        cfg_path = src / "site.yml"
        self.cfg = (yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}) if cfg_path.exists() else {}
        self.lang = self.cfg.get("lang", "en")
        self.labels = labels_for(self.lang, self.cfg.get("labels"))
        self.title = self.cfg.get("title", src.resolve().parent.name)
        self.categories = list(self.cfg.get("categories") or [])
        template = src / "template.html"
        self.template = (template if template.exists() else THEME / "template.html").read_text(encoding="utf-8")

    def lib_file(self, name: str) -> Path | None:
        """A library file: the project's lib/ wins over the theme."""
        for base in (self.src / "lib", THEME):
            if (base / name).exists():
                return base / name
        return None

    def category_title(self, cat: str) -> str:
        return {c["id"]: c.get("title", c["id"]) for c in self.categories}.get(cat, cat)

    def source_label(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(Path.cwd()).as_posix()
        except ValueError:
            return path.as_posix()


# ---------- figures ----------
def load_figure(site: Site, slug: str) -> dict:
    path = site.src / "figures" / f"{slug}.html"
    if not path.exists():
        raise BuildError(f"Figure not found: {site.source_label(path)}")
    text = path.read_text(encoding="utf-8")
    meta = {}
    m = re.match(r"<!--(.*?)-->\s*", text, re.S)
    if m:
        for line in m.group(1).strip().splitlines():
            k, _, v = line.strip().partition(":")
            meta[k.strip()] = v.strip()
        text = text[m.end():]
    m = re.search(r"<script>(.*)</script>\s*$", text, re.S)
    markup, code = (text[: m.start()].strip(), m.group(1).strip()) if m else (text.strip(), "")
    libs = [lib.strip() for lib in meta.get("lib", "").split(",") if lib.strip()]
    for lib in libs:
        if not (site.lib_file(f"{lib}.js") or site.lib_file(f"{lib}.css")):
            raise BuildError(f'{site.source_label(path)}: library "{lib}" not found in lib/')
    height = int(meta["height"]) if meta.get("height", "").isdigit() else None
    return {
        "slug": slug, "path": path, "title": meta.get("title", slug), "markup": markup, "code": code, "libs": libs,
        "height": height, "interactive": bool(re.search(r"<input|<select|<button|tabindex", markup)),
    }


def number_captions(markup: str, start: int, label: str) -> tuple[str, int]:
    """Numbers every <figure> consecutively: "<b>Fig.</b>" without a number gets one, fixed numbers stay."""
    n = start

    def cap(m):
        nonlocal n
        n += 1
        return f"<b>{label} {n}</b>" if m.group(1).strip() == "" else m.group(0)

    out = CAPTION.sub(cap, markup)
    return out, start + max(1, markup.count("<figure"))


def head_assets(site: Site, root: str, libs: list[str]) -> str:
    return "\n".join(f'<link rel="stylesheet" href="{root}assets/{lib}.css">' for lib in libs if site.lib_file(f"{lib}.css"))


def script_tags(site: Site, root: str, libs: list[str], codes: list[str]) -> str:
    tags = [f'<script src="{root}assets/ui.js"></script>']
    tags += [f'<script src="{root}assets/{lib}.js"></script>' for lib in libs if site.lib_file(f"{lib}.js")]
    tags += [f"<script>\n{c}\n</script>" for c in codes if c]
    return "\n".join(tags)


def fill(site: Site, title: str, root: str, source: str, libs: list[str], body: str, codes: list[str]) -> str:
    out = site.template.replace("{{title}}", esc(title)).replace("{{root}}", root).replace("{{lang}}", esc(site.lang))
    out = out.replace("{{generated}}", site.labels["generated"].format(source=source)).replace("{{source}}", source)
    out = out.replace("{{head}}", head_assets(site, root, libs))
    return out.replace("{{body}}", body).replace("{{scripts}}", script_tags(site, root, libs, codes))


# ---------- Markdown ----------
FENCE = re.compile(r"(^(`{3,}|~{3,}).*?^\2[ \t]*$)", re.M | re.S)


def preprocess(md: str) -> str:
    def callout(m):
        kind, title = m.group(1).lower(), m.group(2).strip()
        inner = re.sub(r"^> ?", "", m.group(3), flags=re.M)
        if kind == "note" and not title:
            return f'<div class="note" markdown="1">\n\n{inner}\n</div>\n'
        return f'<div class="merke" markdown="1">\n<div class="eyebrow">{esc(title or kind.capitalize())}</div>\n\n{inner}\n</div>\n'

    def transform(text):
        text = CALLOUT.sub(callout, text)
        return WIDGET.sub(lambda m: f'\n<div class="xw-widget-slot" data-slug="{m.group(1)}" data-part="{m.group(2) or ""}"></div>\n', text)

    # fenced code blocks are left alone, so a page can show the syntax it documents
    parts = FENCE.split(md)  # [text, fence, marker, text, fence, marker, ...]
    return "".join(part if i % 3 == 1 else transform(part) for i, part in enumerate(parts) if i % 3 != 2)


def render(md: str) -> str:
    return markdown.markdown(
        md,
        extensions=["tables", "attr_list", "md_in_html", "fenced_code", "pymdownx.arithmatex"],
        extension_configs={"pymdownx.arithmatex": {"generic": True}},
    )


def level_badge(level: int, eyebrow: str) -> str:
    dots = "".join('<i class="f"></i>' if i < level else "<i></i>" for i in range(5))
    return f'<div class="level"><span class="depth">{dots}</span><span class="eyebrow">{esc(eyebrow)}</span></div>'


def theme_buttons(labels: dict) -> str:
    return (
        f'<div class="theme" role="group" aria-label="{esc(labels["theme"])}">'
        f'<button type="button" data-t="light">{esc(labels["light"])}</button>'
        f'<button type="button" data-t="dark">{esc(labels["dark"])}</button>'
        f'<button type="button" data-t="system">{esc(labels["system"])}</button></div>'
    )


def read_page(path: Path) -> tuple[dict, str]:
    raw = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", raw, re.S)
    if not m:
        return {}, raw
    return yaml.safe_load(m.group(1)) or {}, raw[m.end():]


def build_page(site: Site, path: Path) -> dict:
    L = site.labels
    fm, md = read_page(path)
    if not fm.get("title"):
        raise BuildError(f"{site.source_label(path)}: front matter needs a title")
    rel = path.relative_to(site.src / "pages").with_suffix(".html")
    root = "../" * (len(rel.parts) - 1)
    soup = BeautifulSoup(render(preprocess(md)), "html.parser")

    for d in soup.select("div.arithmatex"):
        d["class"] = ["eq"]
    for c in soup.find_all(["td", "th"], style=True):
        if "text-align: right" in c["style"]:
            del c["style"]
            c["class"] = ["num"]
    for t in soup.find_all("table"):
        if not (t.parent and "tbl" in (t.parent.get("class") or [])):
            t.wrap(soup.new_tag("div", attrs={"class": "tbl"}))
    for ul in soup.find_all("ul"):
        if not ul.find_parent(class_=["merke", "note"]) and not ul.get("class"):
            ul["class"] = ["tight"]
    for ol in soup.find_all("ol"):
        if not ol.get("class"):
            ol["class"] = ["steps"]

    figs, seen, counter = [], {}, 0
    for slot in soup.select("div.xw-widget-slot"):
        slug, part = slot["data-slug"], slot.get("data-part")
        if slug not in seen:
            f = load_figure(site, slug)
            f["start"] = counter
            seen[slug] = f
            figs.append(f)
        f = seen[slug]
        markup = f["markup"]
        if part:  # only the n-th <figure> of the figure file
            parts = [str(x) for x in BeautifulSoup(markup, "html.parser").find_all("figure", recursive=False)]
            if int(part) > len(parts):
                raise BuildError(f'{site.source_label(path)}: "{slug}" has no part {part}')
            markup = parts[int(part) - 1]
        markup, counter = number_captions(markup, counter, L["fig"])
        slot.replace_with(BeautifulSoup(markup, "html.parser"))

    intro, sections, cur = [], [], None
    for node in list(soup.children):
        if getattr(node, "name", None) == "h2":
            cur = {"h2": node, "nodes": []}
            sections.append(cur)
        elif cur is None:
            intro.append(node)
        else:
            cur["nodes"].append(node)

    toc, toc_m, secs, num, group = [], [], [], 0, None
    if fm.get("toc_intro"):
        toc.append(f'<li><a href="#ueberblick"><span class="n">0</span><span>{esc(fm["toc_intro"])}</span></a></li>')
        toc_m.append(f'<li><a href="#ueberblick">{esc(fm["toc_intro"])}</a></li>')
    for s in sections:
        h = s["h2"]
        a = {k: h.attrs.pop(k) for k in ["id", "group", "eyebrow", "toc", "n", "level", "appendix"] if k in h.attrs}
        sid = a.get("id") or re.sub(r"\W+", "-", h.get_text().lower()).strip("-")
        if a.get("appendix"):
            if group != L["appendix"] and "group" not in a:
                a["group"] = L["appendix"]
            mark = a.get("n", a["appendix"])
            badge = f'<div class="eyebrow">{esc(a.get("eyebrow", L["appendix"] + " " + a["appendix"]))}</div>'
        else:
            num += 1
            mark = a.get("n", str(num))
        if a.get("group") and a["group"] != group:
            group = a["group"]
            toc.append(f'<li class="lv">{esc(group)}</li>')
        if not a.get("appendix"):
            eb = a.get("eyebrow", group or "")
            badge = level_badge(int(a["level"]), eb) if a.get("level") else f'<div class="step"><b>{esc(mark)}</b><span class="eyebrow">{esc(eb)}</span></div>'
        short = a.get("toc") or h.get_text().strip()
        toc.append(f'<li><a href="#{sid}"><span class="n">{esc(mark)}</span><span>{esc(short)}</span></a></li>')
        toc_m.append(f'<li><a href="#{sid}"><span class="n">{esc(mark)}</span><span>{esc(short)}</span></a></li>')
        secs.append(f'<section id="{sid}">\n{badge}\n{h}\n{"".join(str(x) for x in s["nodes"]).strip()}\n</section>')

    intro_html = "".join(str(x) for x in intro).strip()
    intro_html = re.sub(r"^<p>", '<p class="lede">', intro_html, count=1)
    cat = fm.get("category", rel.parts[0] if len(rel.parts) > 1 else "")
    cat_title = site.category_title(cat)
    home = site.cfg.get("home_label", L["home"])
    back = f'<p class="backlink"><a href="{root}index.html">← {esc(home)}</a>' + (f' · <a href="{root}index.html#{cat}">{esc(cat_title)}</a>' if cat else "") + "</p>"
    nl = chr(10)
    body = f'''<div class="wrap">
  <nav class="toc" aria-label="{esc(L["toc"])}">
    <div class="eyebrow">{esc(L["toc"])}</div>
    <ol>
      {(nl + '      ').join(toc)}
    </ol>
  </nav>
  <main>
    <header id="ueberblick">
      {back}
      <div class="topbar"><div class="eyebrow">{esc(fm.get('eyebrow', cat_title or site.title))}</div>
        {theme_buttons(L)}</div>
      <h1>{esc(fm['title'])}</h1>
      {intro_html}
    </header>
    <details class="toc-mobile"><summary><span class="lab">{esc(L["toc"])}</span><span class="cur"></span></summary><ol>{''.join(toc_m)}</ol></details>
{nl.join(secs)}
    {f'<footer>{fm["footer"]}</footer>' if fm.get('footer') else ''}
  </main>
</div>'''
    libs = list(dict.fromkeys(lib for f in figs for lib in f["libs"]))
    libs = list(dict.fromkeys(list(fm.get("libs") or []) + libs))
    dest = site.out / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(fill(site, fm["title"], root, site.source_label(path), libs, body, [f["code"] for f in figs]), encoding="utf-8")
    entry = {"id": fm.get("id", path.stem), "category": cat, "path": rel.as_posix(), "title": fm["title"],
             "desc": fm.get("desc", ""), "tags": list(fm.get("tags") or [])}
    if fm.get("group"):
        entry["group"] = fm["group"]
    return {"entry": entry, "order": fm.get("order", 100), "figs": figs}


def build_widget(site: Site, f: dict) -> None:
    markup, _ = number_captions(f["markup"], f["start"], site.labels["fig"])
    body = f'<main class="widget">\n{markup}\n</main>'
    (site.out / "widgets").mkdir(parents=True, exist_ok=True)
    (site.out / "widgets" / f'{f["slug"]}.html').write_text(
        fill(site, f["title"], "../", site.source_label(f["path"]), f["libs"], body, [f["code"]]), encoding="utf-8")


def build_index(site: Site, has_widgets: bool) -> None:
    L, cfg = site.labels, site.cfg
    widgets = ""
    if has_widgets and cfg.get("widgets_section", True):
        widgets = f'''<section id="widgets" style="padding-top:64px">
  <h2>{L["widgets_title"]}</h2>
  <p>{L["widgets_intro"]}</p>
  <pre class="ex" id="ex"></pre>
  <ul class="tight">
    <li>{L["widgets_theme"]}</li>
    <li>{L["widgets_frame"]}</li>
  </ul>
  <div id="wlist"></div>
</section>'''
    page = (THEME / "index.html").read_text(encoding="utf-8")
    for key, value in {
        "lang": esc(site.lang), "title": esc(site.title),
        "generated": L["generated"].format(source=site.source_label(site.src / "site.yml")),
        "eyebrow": f'<div class="eyebrow">{esc(cfg["eyebrow"])}</div>' if cfg.get("eyebrow") else "",
        "lede": f'<p class="lede">{cfg["lede"]}</p>' if cfg.get("lede") else "",
        "search": esc(L["search"]), "search_aria": esc(L["search_aria"]),
        "widgets": widgets, "footer": f'<footer>{cfg["footer"]}</footer>' if cfg.get("footer") else "",
    }.items():
        page = page.replace("{{" + key + "}}", value)
    (site.out / "index.html").write_text(page, encoding="utf-8")


def copy_assets(site: Site) -> None:
    assets = site.out / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    for base in (THEME, site.src / "lib"):  # project files override the theme
        if base.is_dir():
            for p in sorted(base.iterdir()):
                if p.suffix in (".css", ".js"):
                    shutil.copyfile(p, assets / p.name)
    static = site.src / "static"
    if static.is_dir():
        shutil.copytree(static, site.out, dirs_exist_ok=True)


def build(src: str | Path = "docs", out: str | Path = "site", quiet: bool = False) -> dict:
    """Build the site and return the manifest. Raises BuildError for problems in the sources."""
    site = Site(Path(src), Path(out))
    pages_dir = site.src / "pages"
    if not pages_dir.is_dir():
        raise BuildError(f"No pages/ folder in {site.src}")
    site.out.mkdir(parents=True, exist_ok=True)
    old_path = site.out / "manifest.json"
    old = json.loads(old_path.read_text(encoding="utf-8")) if old_path.exists() else {}
    old_heights = {w["slug"]: w.get("height") for w in old.get("widgets", [])}

    copy_assets(site)
    built, widgets, used = [], [], {}
    for p in sorted(pages_dir.rglob("*.md")):
        info = build_page(site, p)
        built.append(info)
        for f in info["figs"]:
            if f["slug"] in used:  # reused on a second page: the stand-alone file keeps its first number
                continue
            used[f["slug"]] = info["entry"]["id"]
            build_widget(site, f)
            widgets.append({"slug": f["slug"], "page": info["entry"]["id"], "title": f["title"], "interactive": f["interactive"],
                            "height": f["height"] or old_heights.get(f["slug"]) or DEFAULT_HEIGHT})
        if not quiet:
            print(f'{info["entry"]["path"]}: {len(info["figs"])} figure(s)')

    planned = [{"order": 1000, **p, "status": "planned", "tags": list(p.get("tags") or []), "desc": p.get("desc", "")}
               for p in (site.cfg.get("planned") or [])]
    entries = [(i["order"], n, i["entry"]) for n, i in enumerate(built)]
    entries += [(p.pop("order"), len(built) + n, p) for n, p in enumerate(planned)]
    pages = [e for _, _, e in sorted(entries, key=lambda t: (t[0], t[1]))]

    categories = [dict(c) for c in site.categories]
    known = {c["id"] for c in categories}
    for cat in dict.fromkeys(p["category"] for p in pages):  # categories that only exist as folders
        if cat not in known:
            categories.append({"id": cat, "title": cat.replace("-", " ").capitalize() if cat else "", "desc": ""})

    manifest = {"title": site.title, "lang": site.lang, "labels": site.labels,
                "categories": categories, "pages": pages, "widgets": widgets}
    old_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    build_index(site, bool(widgets))
    return manifest
