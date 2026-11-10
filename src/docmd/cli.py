"""Command line: docmd build | serve | new."""

from __future__ import annotations

import argparse
import functools
import http.server
import shutil
import sys
import threading
import time
from pathlib import Path

from docmd.build import BuildError, build

STARTER = Path(__file__).resolve().parent / "starter"


def _snapshot(src: Path) -> dict:
    return {p: p.stat().st_mtime for p in src.rglob("*") if p.is_file()}


def cmd_build(args) -> int:
    build(args.src, args.out)
    return 0


def cmd_serve(args) -> int:
    src, out = Path(args.src), Path(args.out)
    build(src, out)

    def watch():
        seen = _snapshot(src)
        while True:
            time.sleep(0.5)
            now = _snapshot(src)
            if now != seen:
                seen = now
                try:
                    build(src, out, quiet=True)
                    print("rebuilt")
                except BuildError as e:
                    print(f"error: {e}", file=sys.stderr)
                except Exception as e:  # a half-saved file must not stop the watcher
                    print(f"error: {type(e).__name__}: {e}", file=sys.stderr)

    threading.Thread(target=watch, daemon=True).start()
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):  # one line per request buries the "rebuilt" messages
            pass

    handler = functools.partial(Quiet, directory=str(out))
    with http.server.ThreadingHTTPServer(("127.0.0.1", args.port), handler) as server:
        print(f"http://127.0.0.1:{args.port}/  (rebuilds when {src}/ changes, Ctrl+C to stop)")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
    return 0


def cmd_new(args) -> int:
    dest = Path(args.dir)
    if dest.exists() and any(dest.iterdir()):
        print(f"error: {dest} already exists and is not empty", file=sys.stderr)
        return 1
    shutil.copytree(STARTER, dest, dirs_exist_ok=True)
    print(f"Created {dest}/. Next: docmd serve {dest}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="docmd", description="Static docs from Markdown with live, embeddable figures.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="build the site")
    b.add_argument("src", nargs="?", default="docs", help="source folder (default: docs)")
    b.add_argument("--out", default="site", help="output folder (default: site)")
    b.set_defaults(fn=cmd_build)

    s = sub.add_parser("serve", help="build, serve locally and rebuild on change")
    s.add_argument("src", nargs="?", default="docs")
    s.add_argument("--out", default="site")
    s.add_argument("--port", type=int, default=8000)
    s.set_defaults(fn=cmd_serve)

    n = sub.add_parser("new", help="create a starter docs folder")
    n.add_argument("dir", nargs="?", default="docs")
    n.set_defaults(fn=cmd_new)

    args = parser.parse_args(argv)
    try:
        return args.fn(args)
    except BuildError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
