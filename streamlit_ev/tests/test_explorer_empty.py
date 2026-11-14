import os
import sys
import unittest

from streamlit.testing.v1 import AppTest

APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../app"))

SCRIPT = f"""
import sys
sys.path.insert(0, {APP_DIR!r})
import streamlit as st
import explorer

explorer.is_github_mode = lambda: True
explorer.get_current_branch = lambda: "main"
explorer.render_branch_selector = lambda **k: None
explorer.render_storage_status = lambda: None
explorer.render_commit_history = lambda **k: st.write("history")
explorer.list_schemas = lambda: []
explorer.read_schemas_parallel = lambda files: {{}}
st.session_state.setdefault("repo", {{}})
explorer.render_explorer()
"""


class TestExplorerEmpty(unittest.TestCase):
    def test_recent_changes_rendered_with_no_schemas(self):
        at = AppTest.from_string(SCRIPT, default_timeout=30).run()
        self.assertEqual([e.value for e in at.exception], [])
        self.assertTrue(any("No schemas found" in i.value for i in at.info))
        self.assertIn("Recent Changes", [e.label for e in at.expander])


if __name__ == "__main__":
    unittest.main()
