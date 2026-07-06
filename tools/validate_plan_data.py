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

    meta = data["meta"]
    if "actualizado_texto" not in meta or not isinstance(meta["actualizado_texto"], str):
        fail("meta.actualizado_texto must be a string")
    if "fuentes" not in meta or not isinstance(meta["fuentes"], list) or not meta["fuentes"]:
        fail("meta.fuentes must be a non-empty list")
    for i, fuente in enumerate(meta["fuentes"]):
        if not isinstance(fuente, str) or not fuente.strip():
            fail(f"meta.fuentes[{i}] must be a non-empty string")

    resumen = data["resumen"]
    for key in ("avance_general", "total", "estados"):
        if key not in resumen:
            fail(f"missing resumen.{key}")
    if not isinstance(resumen["estados"], dict):
        fail("resumen.estados must be a dict")

    estados = resumen["estados"]
    if set(estados) != VALID_ESTADOS:
        fail(f"resumen.estados keys must be exactly {sorted(VALID_ESTADOS)}")
    if sum(estados.values()) != resumen["total"]:
        fail(f"estado counts {sum(estados.values())} != total {resumen['total']}")
    if not 0 <= resumen["avance_general"] <= 100:
        fail("resumen.avance_general must be 0..100")

    for i, item in enumerate(data["destacados"] + data["actualizaciones"]):
        if "estado" not in item:
            fail(f"missing estado at destacados/actualizaciones[{i}]")
        if item["estado"] not in VALID_ESTADOS:
            fail(f"invalid estado '{item['estado']}' at destacados/actualizaciones[{i}]")
        if "texto" not in item or not isinstance(item["texto"], str) or not item["texto"].strip():
            fail(f"empty texto at destacados/actualizaciones[{i}]")

    seen_ids = set()
    for i, eje in enumerate(data["ejes"]):
        for key in ("id", "nombre", "compromisos", "avance"):
            if key not in eje:
                fail(f"missing eje.{key} at ejes[{i}]")
        if eje["id"] in seen_ids:
            fail(f"duplicate eje id: {eje['id']}")
        seen_ids.add(eje["id"])
        if not 0 <= eje["avance"] <= 100:
            fail(f"eje '{eje['id']}' avance must be 0..100")

    print(f"OK: {DATA_PATH.name} valid — {resumen['total']} compromisos, {len(data['ejes'])} ejes")


if __name__ == "__main__":
    main()
