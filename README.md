# doc.md

Static documentation from Markdown, with live figures. Each page is one
Markdown file; each figure is one small HTML file with its own script, shown
in the page and also published on its own so it can be embedded elsewhere
(for example in an Obsidian note).

No JavaScript framework and no bundler: the build is one Python module that
writes plain HTML.

```
docs/                       sources (you edit these)
  site.yml                    title, language, categories
  pages/<category>/*.md       page content
  figures/*.html              figures: markup + script, one file each
  lib/                        your own figure libraries, theme overrides
  static/                     copied as is (images, downloads)

site/                       result of `docmd build`
  index.html                  start page with search
  <category>/<page>.html      pages
  widgets/<slug>.html         every figure on its own
  assets/, manifest.json
```

## Start

```bash
pip install git+https://github.com/maaaax1611/doc.md
docmd new docs        # starter folder with one example page and two figures
docmd serve docs      # http://127.0.0.1:8000, rebuilds when a source changes
docmd build docs      # writes site/
```

The starter page, `docs/pages/guide/writing-pages.md`, shows every feature and
is the place to copy from.

## Pages

```markdown
---
title: Autograd
desc: One line for the card on the start page.
tags: [Chain rule, Graph]
order: 1
---

First paragraph: the lede.

## The chain rule {#chain-rule group="Basics"}

Inline $x^2$ and display formulas:

$$ \frac{\partial L}{\partial x} = \sum_i \frac{\partial L}{\partial y_i}\frac{\partial y_i}{\partial x} $$

> [!abstract] Key points
> - Boxes use Obsidian's callout syntax.

::: widget ag-01-graph
```

Front matter: `title` (required), `desc`, `tags`, `order` (position on the
start page, default 100), `group`, `eyebrow`, `footer`, `toc_intro`, `libs`.

Section attributes, in the braces after a `##` heading: `#id`, `group`,
`toc`, `eyebrow`, `n`, `level`, `appendix`.

## Figures

`docs/figures/ag-01-graph.html`:

```html
<!-- title: Computational graph
     lib: fig
     height: 420 -->
<figure class="fig">
  <canvas id="ag1-cv" style="aspect-ratio: 2.4 / 1"></canvas>
  <figcaption><b>Fig.</b> What the reader should see.</figcaption>
</figure>
<script>
(() => {
  const cv = document.getElementById('ag1-cv');
  function draw() {
    const { ctx, w, h } = Fig.fit(cv);
    ctx.strokeStyle = Fig.token('--accent');
    // …
  }
  Fig.onRedraw(cv, draw);
})();
</script>
```

- The header comment gives the `title`, the libraries to load (`lib`) and the
  `height` suggested for embedding.
- `<b>Fig.</b>` is numbered at build time.
- The same script runs in the page and in `widgets/<slug>.html`. Find
  elements by id, prefix the ids per figure, and keep variables inside a
  function.
- `lib: fig` loads the built-in helpers: `Fig.fit`, `Fig.token`,
  `Fig.onRedraw`, `Fig.loop` (animation that pauses off screen and respects
  reduced motion), `Fig.rgba`, `Fig.lerp`, `Fig.ease`, `Fig.clamp`.
- Functions shared by several figures go into `docs/lib/<name>.js`, styles
  into `docs/lib/<name>.css`; load them with `lib: <name>`.
- A file with several `<figure>` elements can be placed piece by piece:
  `::: widget slug part=2`.

Embedded figures accept `?theme=dark`, `?theme=light` and `?frame=0`.

## site.yml

```yaml
title: nabla
lang: en                 # en or de
eyebrow: Autograd · Networks · Training
lede: How the library works, one topic per page.
footer: All figures compute in the browser.
home_label: Docs
categories:
  - { id: core, title: Core, desc: Tensors and the graph. }
planned:
  - { category: core, title: Broadcasting, desc: Coming next., tags: [shapes] }
widgets_section: true    # list of embeddable figures on the start page
labels: { fig: "Figure" } # override single generated texts
```

Categories that exist only as a folder under `pages/` are added
automatically. A `docs/template.html` replaces the page skeleton, and a file
in `docs/lib/` with the name of a theme file (`page.css`, `index.css`,
`ui.js`) replaces that file.

## Publish with GitHub Pages

`.github/workflows/docs.yml` in the project that holds the docs
(*Settings → Pages → Source: GitHub Actions*, once):

```yaml
name: docs
on:
  push: { branches: [main], paths: ["docs/**", ".github/workflows/docs.yml"] }
  workflow_dispatch:
permissions: { contents: read, pages: write, id-token: write }
concurrency: { group: pages, cancel-in-progress: true }
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install git+https://github.com/maaaax1611/doc.md
      - run: docmd build docs --out site
      - uses: actions/upload-pages-artifact@v3
        with: { path: site }
  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment: { name: github-pages, url: "${{ steps.d.outputs.page_url }}" }
    steps:
      - id: d
        uses: actions/deploy-pages@v4
```

To commit the built pages instead (deploy from a branch), build into the
repository root with `docmd build src --out .`; the build never deletes
files it did not write.

## Notes

- Formulas are rendered by MathJax from cdnjs and the fonts come from Google
  Fonts, so both need a network connection; the figures work without one.
- The start page loads `manifest.json` with `fetch`, so open the site through
  a web server (`docmd serve`), not as a file.

## Development

```bash
uv sync
uv run pytest
```
