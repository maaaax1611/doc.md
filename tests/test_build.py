import json
import shutil
from pathlib import Path

import pytest

from docmd import build
from docmd.build import BuildError, preprocess
from docmd.cli import main

STARTER = Path(__file__).resolve().parents[1] / "src" / "docmd" / "starter"


@pytest.fixture
def docs(tmp_path):
    shutil.copytree(STARTER, tmp_path / "docs")
    return tmp_path / "docs"


def page(docs, name="p", body="Intro.\n\n## One {#one}\n\nText.\n", front="title: P\n"):
    path = docs / "pages" / "guide" / f"{name}.md"
    path.write_text(f"---\n{front}---\n\n{body}")
    return path


def test_starter_builds_pages_widgets_assets_and_manifest(docs, tmp_path):
    out = tmp_path / "site"
    manifest = build(docs, out, quiet=True)

    assert (out / "index.html").exists()
    html = (out / "guide" / "writing-pages.html").read_text()
    assert '<section id="sections">' in html and '<p class="lede">' in html
    assert {p.name for p in (out / "assets").iterdir()} >= {"page.css", "ui.js", "index.js", "index.css", "fig.js"}
    assert manifest == json.loads((out / "manifest.json").read_text())
    assert [w["slug"] for w in manifest["widgets"]] == ["demo-01-wave", "demo-02-pipeline"]
    assert [w["interactive"] for w in manifest["widgets"]] == [True, False]
    assert manifest["widgets"][0]["height"] == 470
    assert [p.get("status") for p in manifest["pages"]] == [None, "planned"]


def test_figures_are_numbered_in_page_and_keep_their_number_stand_alone(docs, tmp_path):
    out = tmp_path / "site"
    build(docs, out, quiet=True)
    html = (out / "guide" / "writing-pages.html").read_text()
    assert "<b>Fig. 1</b>" in html and "<b>Fig. 2</b>" in html and "<b>Fig.</b>" not in html.split("<figure")[1]
    assert "<b>Fig. 2</b>" in (out / "widgets" / "demo-02-pipeline.html").read_text()


def test_only_libraries_a_page_needs_are_loaded(docs, tmp_path):
    out = tmp_path / "site"
    build(docs, out, quiet=True)
    assert "assets/fig.js" in (out / "widgets" / "demo-01-wave.html").read_text()
    assert "assets/fig.js" not in (out / "widgets" / "demo-02-pipeline.html").read_text()


def test_syntax_inside_code_fences_is_not_expanded():
    md = "::: widget a-b\n\n```\n::: widget c-d\n> [!note]\n> x\n```\n\n> [!abstract] T\n> body\n"
    out = preprocess(md)
    assert out.count("xw-widget-slot") == 1 and 'data-slug="a-b"' in out
    assert "::: widget c-d\n> [!note]\n> x" in out
    assert out.count('class="merke"') == 1


def test_german_labels_and_appendix(docs, tmp_path):
    (docs / "site.yml").write_text("title: Wiki\nlang: de\n")
    page(docs, body="Intro.\n\n## Eins {#eins}\n\nText.\n\n::: widget demo-02-pipeline\n\n## Mehr {#mehr appendix=\"A\"}\n\nText.\n")
    (docs / "pages" / "guide" / "writing-pages.md").unlink()
    out = tmp_path / "site"
    build(docs, out, quiet=True)
    html = (out / "guide" / "p.html").read_text()
    assert '<html lang="de">' in html and "<b>Abb. 1</b>" in html
    assert '<div class="eyebrow">Anhang A</div>' in html and "← Wiki" in html


def test_project_lib_overrides_theme_and_static_is_copied(docs, tmp_path):
    (docs / "lib" / "page.css").write_text("/* mine */")
    (docs / "static" / "img").mkdir(parents=True)
    (docs / "static" / "img" / "a.txt").write_text("x")
    out = tmp_path / "site"
    build(docs, out, quiet=True)
    assert (out / "assets" / "page.css").read_text() == "/* mine */"
    assert (out / "img" / "a.txt").read_text() == "x"


def test_pages_without_category_folder_and_undeclared_categories(docs, tmp_path):
    (docs / "site.yml").write_text("title: T\n")
    (docs / "pages" / "top.md").write_text("---\ntitle: Top\n---\n\nIntro.\n")
    out = tmp_path / "site"
    manifest = build(docs, out, quiet=True)
    assert (out / "top.html").exists()
    assert 'href="assets/page.css"' in (out / "top.html").read_text()
    assert {c["id"] for c in manifest["categories"]} == {"", "guide"}


def test_order_controls_position_on_start_page(docs, tmp_path):
    page(docs, "zz", front="title: First\norder: 0\n")
    manifest = build(docs, tmp_path / "site", quiet=True)
    assert [p["title"] for p in manifest["pages"]][:2] == ["First", "Writing pages"]


def test_height_from_previous_manifest_is_kept(docs, tmp_path):
    fig = docs / "figures" / "demo-02-pipeline.html"
    fig.write_text(fig.read_text().replace("     height: 250 -->", "-->").replace("<!-- title: From sources to site\n-->", "<!-- title: From sources to site -->"))
    out = tmp_path / "site"
    assert build(docs, out, quiet=True)["widgets"][1]["height"] == 640
    m = json.loads((out / "manifest.json").read_text())
    m["widgets"][1]["height"] = 333
    (out / "manifest.json").write_text(json.dumps(m))
    assert build(docs, out, quiet=True)["widgets"][1]["height"] == 333


@pytest.mark.parametrize(
    "body, front, message",
    [
        ("::: widget nope\n", "title: P\n", "Figure not found"),
        ("Text.\n", "desc: x\n", "needs a title"),
        ("::: widget demo-02-pipeline part=3\n", "title: P\n", "has no part 3"),
    ],
)
def test_source_problems_are_reported(docs, tmp_path, body, front, message):
    page(docs, body=body, front=front)
    with pytest.raises(BuildError, match=message):
        build(docs, tmp_path / "site", quiet=True)


def test_unknown_library_is_reported(docs, tmp_path):
    (docs / "figures" / "x-01.html").write_text('<!-- title: X\n     lib: nolib -->\n<figure class="fig"></figure>\n')
    page(docs, body="::: widget x-01\n")
    with pytest.raises(BuildError, match='library "nolib"'):
        build(docs, tmp_path / "site", quiet=True)


def test_cli_new_then_build(tmp_path, capsys):
    assert main(["new", str(tmp_path / "docs")]) == 0
    assert main(["new", str(tmp_path / "docs")]) == 1  # refuses to overwrite
    assert main(["build", str(tmp_path / "docs"), "--out", str(tmp_path / "site")]) == 0
    assert (tmp_path / "site" / "guide" / "writing-pages.html").exists()
    (tmp_path / "docs" / "pages" / "guide" / "bad.md").write_text("no front matter\n")
    assert main(["build", str(tmp_path / "docs"), "--out", str(tmp_path / "site")]) == 1
    assert "needs a title" in capsys.readouterr().err
