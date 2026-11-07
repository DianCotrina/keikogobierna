"""Fetch one El Peruano norma as raw material for an editorial review.

Saves, under --out/<op>/:
  page.txt   the single-norma HTML rendition (#visor-html), tags stripped
  norma.pdf  the official PDF, annexes included when the gazette publishes them
  pdf.txt    `pdftotext -layout` of the PDF, so annexes can be searched and diffed
  meta.json  op, numero, sumilla, sector, fecha and the source URLs

Usage:
  python3 -m tools.review.fetch_norma 2571425-12 [2572385-1 ...] --out /tmp/normas

Deterministic: no AI, no scoring. It only gathers what the reviewer must read.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

BASE = "https://busquedas.elperuano.pe"
UA = {"User-Agent": "Mozilla/5.0 (keikogobierna review)"}


def get(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as resp:
        return resp.read()


def page_field(raw: str, name: str) -> str | None:
    """The page embeds its data as a flat, escaped key/value array: \\"key\\",\\"value\\"."""
    match = re.search(r'\\"' + re.escape(name) + r'\\",\\"((?:[^"\\]|\\\\.)*?)\\"', raw)
    return json.loads(f'"{match.group(1)}"') if match else None


def strip(raw: str) -> str:
    raw = re.sub(r"<(script|style)[\s\S]*?</\1>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw))).strip()


def fetch(op: str, out: Path) -> dict:
    target = out / op
    target.mkdir(parents=True, exist_ok=True)
    raw = get(f"{BASE}/dispositivo/NL/{op}").decode("utf-8", "ignore")
    visor = re.search(r'id="visor-html"[^>]*>([\s\S]*?)</div>\s*</div>', raw)
    (target / "page.txt").write_text(strip(visor.group(1) if visor else raw))

    pdf_path = page_field(raw, "urlPDF")
    meta = {
        "op": op,
        "url": f"{BASE}/dispositivo/NL/{op}",
        "pdf_url": f"{BASE}{pdf_path}" if pdf_path else None,
        "sumilla": page_field(raw, "sumilla"),
        "sector": page_field(raw, "sector"),
        "tipo": page_field(raw, "tipoDispositivo"),
    }
    if pdf_path:
        (target / "norma.pdf").write_bytes(get(meta["pdf_url"]))
        text = subprocess.run(
            ["pdftotext", "-layout", str(target / "norma.pdf"), "-"],
            capture_output=True, text=True, check=True,
        ).stdout
        (target / "pdf.txt").write_text(text)
        meta["pdf_pages"] = text.count("\f") or 1
    (target / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    return meta


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("ops", nargs="+", help="El Peruano op ids, e.g. 2571425-12")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    for op in args.ops:
        meta = fetch(op, args.out)
        print(f"{op}\tpdf_pages={meta.get('pdf_pages', 0)}\t{meta['sumilla'] or ''}"[:200])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
