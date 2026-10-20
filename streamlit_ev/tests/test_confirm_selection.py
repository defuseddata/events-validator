import os
import sys
import unittest

from streamlit.testing.v1 import AppTest

APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../app"))

SCRIPT = f"""
import sys
sys.path.insert(0, {APP_DIR!r})
import streamlit as st
import repo

def fake_apply(updates):
    st.session_state["applied"] = sorted(updates)
    return len(updates), []

repo.apply_updates = fake_apply
repo.write_repo = lambda *a, **k: None
repo.direct_default_branch_save_blocked = lambda: False
repo.render_diff_ui = lambda *a, **k: None
st.session_state.setdefault("repo", {{}})
st.session_state.setdefault("pending_confirmation", {{"draft_param_data": None}})
fmap = {{n: {{"original": {{}}, "new": {{}}}} for n in ("a", "b", "c")}}
repo.confirm_update_dialog(fmap, "p")
"""


class TestConfirmSelection(unittest.TestCase):
    def test_unchecked_schema_hidden_by_filter_stays_unchecked(self):
        at = AppTest.from_string(SCRIPT, default_timeout=30).run()
        at.checkbox(key="chk_b").uncheck().run()
        at.text_input(key="confirm_update_search").set_value("a").run()  # hides b
        at.run()  # extra rerun: widget state of hidden b is dropped here
        at.text_input(key="confirm_update_search").set_value("").run()
        self.assertFalse(at.checkbox(key="chk_b").value)
        next(b for b in at.button if b.label == "Confirm & Update").click().run()
        self.assertEqual(at.session_state["applied"], ["a", "c"])


if __name__ == "__main__":
    unittest.main()
