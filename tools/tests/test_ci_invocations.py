"""Every scraper a workflow runs must be invoked the way the package needs.

tools/scrapers is a package now, so `python3 tools/scrapers/x.py` dies at
import with ModuleNotFoundError: no 'tools' on sys.path. Only `python3 -m
tools.scrapers.x` works. Nothing else notices: the YAML is not executed by
CI, and the scrapers run on their own schedules -- elperuano-scraper.yml
kept the path form through the restructure and would have failed on its
next nightly run, silently as far as the test suite was concerned.

So: every python3 invocation in a workflow must use -m, and the module it
names must exist.
"""

import importlib.util
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
WORKFLOWS = ROOT / ".github" / "workflows"

# `python3 -m pkg.mod` or the broken `python3 path/to/mod.py`
INVOCATION = re.compile(r"python3\s+(?:(-m)\s+([\w.]+)|([\w./]+\.py))")


def invocations():
    """(workflow name, line no, dash_m, target) for every python3 call in CI."""
    for path in sorted(WORKFLOWS.glob("*.yml")):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for dash_m, module, script in INVOCATION.findall(line):
                yield path.name, lineno, bool(dash_m), module or script


class WorkflowInvocationTest(unittest.TestCase):
    def setUp(self):
        self.calls = list(invocations())

    def test_workflows_invoke_python_at_all(self):
        """Guards the guard: a regex that matches nothing would pass everything."""
        self.assertGreater(len(self.calls), 2)

    def test_no_workflow_runs_a_package_module_by_path(self):
        by_path = [
            f"{name}:{lineno} runs {target}"
            for name, lineno, dash_m, target in self.calls
            if not dash_m and (target.startswith("tools/scrapers/") or target.startswith("tools/cabinet/"))
        ]
        self.assertEqual(by_path, [], "package modules must be run with python3 -m")

    def test_every_module_named_with_dash_m_exists(self):
        for name, lineno, dash_m, target in self.calls:
            if not dash_m or not target.startswith("tools."):
                continue
            with self.subTest(workflow=name, line=lineno, module=target):
                self.assertIsNotNone(importlib.util.find_spec(target))


if __name__ == "__main__":
    unittest.main()
