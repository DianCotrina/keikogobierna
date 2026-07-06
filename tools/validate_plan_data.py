#!/usr/bin/env python3
"""Validate src/data/plan.json: schema, estado ids, and count consistency."""
import json
import sys
from pathlib import Path

VALID_ESTADOS = {"cumplida", "en_progreso", "sin_avance", "incumplida"}
DATA_PATH = Path(__file__).resolve().parent.parent / "src" / "data" / "plan.json"


def fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    sys.exit(1)


def main() -> None:
    try:
        data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        fail(f"cannot read/parse {DATA_PATH}: {e}")

    for key in ("meta", "resumen", "destacados", "ejes", "actualizaciones"):
        if key not in data:
            fail(f"missing top-level key: {key}")

    estados = data["resumen"]["estados"]
    if set(estados) != VALID_ESTADOS:
        fail(f"resumen.estados keys must be exactly {sorted(VALID_ESTADOS)}")
    if sum(estados.values()) != data["resumen"]["total"]:
        fail(f"estado counts {sum(estados.values())} != total {data['resumen']['total']}")
    if not 0 <= data["resumen"]["avance_general"] <= 100:
        fail("resumen.avance_general must be 0..100")

    for i, item in enumerate(data["destacados"] + data["actualizaciones"]):
        if item["estado"] not in VALID_ESTADOS:
            fail(f"invalid estado '{item['estado']}' at destacados/actualizaciones[{i}]")
        if not item["texto"].strip():
            fail(f"empty texto at destacados/actualizaciones[{i}]")

    seen_ids = set()
    for eje in data["ejes"]:
        if eje["id"] in seen_ids:
            fail(f"duplicate eje id: {eje['id']}")
        seen_ids.add(eje["id"])
        if not 0 <= eje["avance"] <= 100:
            fail(f"eje '{eje['id']}' avance must be 0..100")

    print(f"OK: {DATA_PATH.name} valid — {data['resumen']['total']} compromisos, {len(data['ejes'])} ejes")


if __name__ == "__main__":
    main()
