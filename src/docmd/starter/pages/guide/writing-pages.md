---
title: Writing pages
desc: Sections, formulas, boxes, tables, code and figures — everything a page can contain.
tags: [Markdown, Figures, Formulas]
order: 1
eyebrow: Guide · Basics
footer: This page is its own example. Its source is <code>pages/guide/writing-pages.md</code>.
---

A page is one Markdown file. The first paragraph, before any heading, becomes the lede you are reading now. Each `##` heading starts a numbered section that appears in the table of contents.

## Sections {#sections group="Text"}

Write a section as `## Title {#id}`. The id becomes the anchor, so links to a section stay stable when you reword its title. Attributes in the braces control how it appears:

| Attribute | Effect |
| --- | --- |
| `group="Text"` | sub-heading in the table of contents from this section on |
| `toc="Short"` | shorter title for the table of contents |
| `eyebrow="…"` | small line above the title (default: the current group) |
| `n="→"` | own marker instead of the automatic number |
| `level="3"` | depth indicator with five dots instead of a number |
| `appendix="A"` | appendix: not numbered, listed under "Appendix" |

## Formulas and boxes {#formulas toc="Formulas, boxes"}

Inline formulas go between single dollar signs, $e^{i\pi} + 1 = 0$, and display formulas between double ones:

$$
y(x, t) = A \sin\bigl(2\pi f\,(x - t)\bigr)
$$

Boxes use the callout syntax of Obsidian. A callout with a title becomes a highlighted box:

> [!abstract] Key points
> - One Markdown file per page, one `##` per section.
> - Formulas in `$…$` and `$$…$$`.

A `[!note]` without a title becomes a quieter side note:

> [!note]
> Callouts may contain lists, formulas and code.

Code blocks are fenced as usual:

```python
def wave(x, t, f=1.0, a=1.0):
    return a * math.sin(2 * math.pi * f * (x - t))
```

## Figures {#figures group="Figures"}

A figure is one HTML file in `figures/`. A page places it with a line of its own:

```
::: widget demo-01-wave
```

The file starts with a comment that names its title and the libraries it needs, followed by the markup of a `<figure class="fig">` and, optionally, one `<script>`. Write the caption as `<b>Fig.</b>`; the number is filled in at build time.

::: widget demo-01-wave

The script of a figure runs on the page and in the stand-alone file under `widgets/`, so it must find its elements by id and keep its variables inside a function. `lib: fig` loads a small helper library; the calls used above are:

| Call | Purpose |
| --- | --- |
| `Fig.fit(canvas)` | sizes the canvas for sharp lines, clears it, returns `{ ctx, w, h }` |
| `Fig.token('--accent')` | a colour of the current theme; read it inside the draw function |
| `Fig.onRedraw(canvas, draw)` | redraws on resize and when the theme changes |
| `Fig.loop(canvas, step)` | animation that pauses off screen and respects reduced motion |

## Sketches {#sketches}

A figure without controls is listed as a sketch. Inline SVG picks up the theme through helper classes such as `d-fg`, `d-mut` and `d-acc` (fill) or `d-st`, `d-stm` and `d-sta` (stroke).

::: widget demo-02-pipeline

## Your own libraries {#libraries appendix="A"}

Functions shared by several figures belong in `lib/<name>.js`, extra styles in `lib/<name>.css`. A figure loads them with `lib: <name>` in its header comment. A file in `lib/` with the name of a theme file, for example `page.css`, replaces it.
