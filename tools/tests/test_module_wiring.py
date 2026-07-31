"""Every scraper module must define or import every global name it reads.

The common/ package means a function can move out of a CLI and into a shared
module, and the CLI keeps importing fine while a name it still calls is gone.
Nothing catches that: --help never reaches the call, and the unit tests
exercise the shared module directly. It only surfaces on the daily run, as a
NameError -- which is how `fetch_normas` and `norma_text` went missing from
elperuano_scraper when the transport moved to common/elperuano_client.

symtable resolves real scopes (params, locals, comprehensions, nested defs),
so a name that survives here is genuinely a module-level free variable.
"""

import builtins
import importlib
import symtable
import unittest
from pathlib import Path

SCRAPERS = Path(__file__).resolve().parent.parent / "scrapers"


def scraper_modules():
    """Every module under tools/scrapers/, dotted, CLIs and shared alike."""
    root = SCRAPERS.parent.parent
    return sorted(
        ".".join(path.relative_to(root).with_suffix("").parts)
        for path in SCRAPERS.rglob("*.py")
        if path.name != "__init__.py"
    )


def undefined_globals(source: str, defined: set, filename: str = "<src>") -> list:
    """Names read as globals in `source` that `defined` does not bind."""
    found = set()

    def walk(table):
        for symbol in table.get_symbols():
            name = symbol.get_name()
            if (symbol.is_global() and not symbol.is_assigned()
                    and name not in defined and not hasattr(builtins, name)):
                found.add(name)
        for child in table.get_children():
            walk(child)

    walk(symtable.symtable(source, filename, "exec"))
    return sorted(found)


class ModuleWiringTest(unittest.TestCase):
    def test_every_scraper_module_is_fully_wired(self):
        modules = scraper_modules()
        self.assertIn("tools.scrapers.elperuano_scraper", modules)  # discovery works
        for dotted in modules:
            with self.subTest(module=dotted):
                module = importlib.import_module(dotted)
                source = Path(module.__file__).read_text(encoding="utf-8")
                self.assertEqual(
                    undefined_globals(source, set(vars(module)), module.__file__), [])

    def test_detects_a_name_the_module_never_imports(self):
        """Guards the guard: the exact shape of the bug it exists to catch."""
        source = "import sys\n\ndef run():\n    return fetch_normas('20260730')\n"
        self.assertEqual(undefined_globals(source, {"sys"}), ["fetch_normas"])

    def test_locals_and_comprehensions_are_not_flagged(self):
        source = "def run(arg):\n    rows = [x for x in arg if x]\n    return rows\n"
        self.assertEqual(undefined_globals(source, set()), [])


if __name__ == "__main__":
    unittest.main()
