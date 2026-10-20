import os
import sys
import unittest
from unittest.mock import MagicMock, patch

import requests
from streamlit.testing.v1 import AppTest

APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../app"))
sys.path.insert(0, APP_DIR)

from helpers import github, storage

SCRIPT = f"""
import sys
sys.path.insert(0, {APP_DIR!r})
import streamlit as st
st.session_state.setdefault("schema_branch", "test")
st.session_state.setdefault("event_name", "first_event")
import builder
builder.render_builder()
"""


def make_get(schemas_status, branch_status, calls):
    def fake_get(url, **kwargs):
        r = MagicMock()
        r.json.return_value = []
        if url.endswith("/contents/schemas"):
            calls.append(url)
            r.status_code = schemas_status
        elif url.endswith("/branches/test"):
            r.status_code = branch_status
        elif url.endswith("/branches"):
            r.status_code, r.json.return_value = 200, [{"name": "main"}, {"name": "test"}]
        else:  # repo.json and anything else: not found -> Builder falls back to {}
            r.status_code = 404
        if r.status_code >= 400:
            r.raise_for_status.side_effect = requests.exceptions.HTTPError(str(r.status_code))
        return r
    return fake_get


class TestBuilderSchemaList(unittest.TestCase):
    def setUp(self):
        github.invalidate_schema_list_cache()
        for p in (
            patch.object(storage, "GITHUB_CONFIGURED", True),
            patch.object(github, "SCHEMA_REPO_OWNER", "o"),
            patch.object(github, "SCHEMA_REPO_NAME", "r"),
            patch.object(github, "DEFAULT_BRANCH", "main"),
            patch.dict(os.environ, {"ALLOW_SAVE_TO_DEFAULT_BRANCH": ""}),
        ):
            p.start()
            self.addCleanup(p.stop)

    def run_builder(self, schemas_status, branch_status):
        calls = []
        patcher = patch.object(github.requests, "get", make_get(schemas_status, branch_status, calls))
        patcher.start()
        self.addCleanup(patcher.stop)
        return AppTest.from_string(SCRIPT, default_timeout=30).run(), calls

    def test_empty_branch_allows_first_save(self):
        at, _ = self.run_builder(schemas_status=404, branch_status=200)
        self.assertEqual([e.value for e in at.exception], [])
        self.assertEqual([e.value for e in at.error if "Cannot verify" in e.value], [])
        self.assertFalse(at.button(key="send_gcp_btn").disabled)

    def test_inaccessible_branch_still_blocks_save(self):
        at, _ = self.run_builder(schemas_status=404, branch_status=404)
        self.assertTrue(any("Cannot verify" in e.value for e in at.error))
        self.assertTrue(at.button(key="send_gcp_btn").disabled)

    def test_listing_is_fetched_once_across_reruns(self):
        at, calls = self.run_builder(schemas_status=200, branch_status=200)
        at.text_input(key="search_param").set_value("a").run()
        at.text_input(key="search_param").set_value("ab").run()
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
