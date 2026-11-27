import os
import unittest

from streamlit.testing.v1 import AppTest

APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../app"))

SCRIPT = f"""
import sys
sys.path.insert(0, {APP_DIR!r})
from helpers import components

components.is_github_mode = lambda: True
components.list_branches = lambda: ["main", "feat/x"]
components.get_current_branch = lambda: "{{branch}}"
components.get_storage_info = lambda: {{"mode": "github", "owner": "o", "repo": "r"}}
components.render_branch_selector(key="t_branch")
"""


def _run(branch):
    return AppTest.from_string(SCRIPT.replace("{branch}", branch), default_timeout=30).run()


class TestBranchBar(unittest.TestCase):
    def test_production_badge_on_default_branch(self):
        at = _run("main")
        self.assertEqual([e.value for e in at.exception], [])
        text = " ".join(m.value for m in at.markdown)
        self.assertIn("GitHub · o/r @ main", text)
        self.assertIn("production", text)
        self.assertEqual({b.key for b in at.button}, {"t_branch_refresh", "t_branch_create_btn"})

    def test_no_production_badge_on_feature_branch(self):
        at = _run("feat/x")
        text = " ".join(m.value for m in at.markdown)
        self.assertIn("@ feat/x", text)
        self.assertNotIn("production", text)


if __name__ == "__main__":
    unittest.main()
