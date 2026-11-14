import os
import sys
import unittest

from streamlit.testing.v1 import AppTest

APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../app"))

SCRIPT = f"""
import sys
sys.path.insert(0, {APP_DIR!r})
import streamlit as st
from helpers import helpers

helpers.write_repo = lambda *a, **k: (False, "boom")
st.session_state.repo = {{"currency": {{"usedInSchemas": []}}}}
helpers.update_repo_with_schema_usage("purchase", {{"event_name": "purchase", "currency": {{}}}})
"""


class TestUsageTrackingWrite(unittest.TestCase):
    def test_failed_repo_write_shows_warning(self):
        at = AppTest.from_string(SCRIPT, default_timeout=30).run()
        self.assertEqual([e.value for e in at.exception], [])
        self.assertEqual([w.value for w in at.warning], ["boom"])


if __name__ == "__main__":
    unittest.main()
